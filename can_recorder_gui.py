"""PySide6 GUI for recording a CAN bus to an ASC trace."""

from __future__ import annotations

import sys
import queue
from datetime import datetime
from pathlib import Path

import can
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFileDialog,
    QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QSplitter, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget, QAbstractItemView, QHeaderView)

try:
    # Package execution: python -m asc_generator.can_recorder_gui
    from .can_recorder import CanRecorder
except ImportError:
    # Direct execution from inside asc_generator: python can_recorder_gui.py
    from can_recorder import CanRecorder


class CanRecorderWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("CAN ASC Recorder")
        self.setMinimumSize(980, 560)
        self.recorder: CanRecorder | None = None
        self.started_at: datetime | None = None
        self._message_queue: queue.Queue[tuple[datetime, can.Message]] = queue.Queue()
        self._trace_rows: dict[int, int] = {}

        self.interface = QComboBox()
        self.interface.setEditable(True)
        self.interface.addItems(["slcan", "vector"])
        self.channel = QComboBox()
        self.channel.setEditable(True)
        self.refresh_ports = QPushButton("Refresh")
        self.refresh_ports.clicked.connect(self._load_channels)
        self.interface.currentTextChanged.connect(self._interface_changed)
        self._load_channels()
        self.bitrate = QComboBox()
        self.bitrate.setEditable(True)
        self.bitrate.addItems(["125000", "250000", "500000", "1000000"])
        self.bitrate.setCurrentText("500000")
        self.output = QLineEdit(str(Path.cwd() / "can_recording.asc"))
        browse = QPushButton("Browse...")
        browse.clicked.connect(self._browse_output)
        output_row = QHBoxLayout()
        output_row.addWidget(self.output)
        output_row.addWidget(browse)
        channel_row = QHBoxLayout()
        channel_row.addWidget(self.channel)
        channel_row.addWidget(self.refresh_ports)
        self.receive_own = QCheckBox("Receive own transmitted messages")
        self.receive_own.setChecked(True)

        form = QFormLayout()
        form.addRow("CAN interface", self.interface)
        form.addRow("Channel / port", channel_row)
        form.addRow("Bitrate (bit/s)", self.bitrate)
        form.addRow("ASC output file", output_row)
        form.addRow("", self.receive_own)
        settings = QGroupBox("Recording settings")
        settings.setLayout(form)

        self.record_button = QPushButton("Start recording")
        self.record_button.setMinimumHeight(42)
        self.record_button.clicked.connect(self._toggle_recording)
        self.status = QLabel("Ready")
        self.status.setStyleSheet("font-weight: bold; color: #486581;")
        self.count = QLabel("Messages: 0")
        self.elapsed = QLabel("Duration: 00:00:00")
        info = QGridLayout()
        info.addWidget(self.status, 0, 0, 1, 2)
        info.addWidget(self.count, 1, 0)
        info.addWidget(self.elapsed, 1, 1)

        root = QVBoxLayout()
        root.addWidget(settings)
        root.addWidget(self.record_button)
        root.addLayout(info)
        root.addStretch()

        left_panel = QWidget()
        left_panel.setLayout(root)

        self.trace = QTableWidget(0, 5)
        self.trace.setHorizontalHeaderLabels(["Time", "ID", "DLC", "Data", "Type"])
        self.trace.setAlternatingRowColors(True)
        self.trace.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.trace.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.trace.setSelectionMode(QAbstractItemView.SingleSelection)
        self.trace.verticalHeader().setVisible(False)
        header = self.trace.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        trace_box = QGroupBox("Live CAN trace (latest message per ID)")
        trace_layout = QVBoxLayout(trace_box)
        trace_layout.addWidget(self.trace)

        splitter = QSplitter()
        splitter.addWidget(left_panel)
        splitter.addWidget(trace_box)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([360, 700])
        self.setCentralWidget(splitter)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_elapsed)
        self.trace_timer = QTimer(self)
        self.trace_timer.timeout.connect(self._drain_message_queue)
        self.trace_timer.start(100)

    def _load_channels(self) -> None:
        interface = self.interface.currentText()
        channels = []
        channel_data = []
        if interface == "vector":
            try:
                configs = can.detect_available_configs(interfaces=["vector"])
                for config in configs:
                    # Do not show Vector's software-only virtual channels.
                    name = config.get("vector_channel_config").name
                    if name.lower().startswith("virtual"):
                        continue
                    channels.append(f"{name} (SN {config.get('serial')})")
                    channel_data.append(config.get("channel"))
            except Exception:
                pass
        else:
            try:
                from serial.tools import list_ports
                channels = sorted({p.device for p in list_ports.comports()})
            except Exception:
                pass
        current = self.channel.currentText()
        self.channel.clear()
        if channels:
            for index, value in enumerate(channels):
                self.channel.addItem(value, channel_data[index] if channel_data else value)
            self.channel.setCurrentText(current if current in channels else channels[0])
        else:
            self.channel.addItem("No channels detected")
            self.channel.setCurrentText("")
        self.channel.setEditable(interface != "vector")

    def _interface_changed(self, _interface: str) -> None:
        self._load_channels()

    def _browse_output(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(self, "Save ASC recording", self.output.text(), "ASC trace (*.asc)")
        if filename:
            self.output.setText(filename if filename.lower().endswith(".asc") else filename + ".asc")

    def _toggle_recording(self) -> None:
        if self.recorder and self.recorder.is_recording:
            self._stop_recording()
            return
        try:
            channel = self.channel.currentData()
            if channel is None:
                channel = self.channel.currentText()
            self.recorder = CanRecorder(self.interface.currentText(), channel,
                                        int(self.bitrate.currentText()), self.output.text(),
                                        self.receive_own.isChecked(),
                                        on_message=self._message_received)
            self._clear_trace()
            self.recorder.start()
        except Exception as exc:
            self.recorder = None
            QMessageBox.critical(self, "Could not start recording", str(exc))
            return
        self.started_at = datetime.now()
        self.timer.start(500)
        self.status.setText(f"Recording -> {self.output.text()}")
        self.status.setStyleSheet("font-weight: bold; color: #c0392b;")
        self.record_button.setText("Stop recording")
        self.record_button.setStyleSheet("background: #c0392b; color: white;")
        for widget in (self.interface, self.channel, self.refresh_ports, self.bitrate, self.output):
            widget.setEnabled(False)

    def _stop_recording(self) -> None:
        if self.recorder:
            self.recorder.stop()
        self.timer.stop()
        self.status.setText(f"Saved {self.output.text()}")
        self.status.setStyleSheet("font-weight: bold; color: #287d3c;")
        self.record_button.setText("Start recording")
        self.record_button.setStyleSheet("")
        for widget in (self.interface, self.channel, self.refresh_ports, self.bitrate, self.output):
            widget.setEnabled(True)

    def _update_elapsed(self) -> None:
        if self.recorder:
            self.count.setText(f"Messages: {self.recorder.message_count:,}")
        if self.started_at:
            seconds = int((datetime.now() - self.started_at).total_seconds())
            self.elapsed.setText(f"Duration: {seconds // 3600:02}:{seconds % 3600 // 60:02}:{seconds % 60:02}")

    def _message_received(self, message: can.Message) -> None:
        """Called by python-can's worker thread; do not touch Qt widgets here."""
        self._message_queue.put((datetime.now(), message))

    def _clear_trace(self) -> None:
        self.trace.setRowCount(0)
        self._trace_rows.clear()
        while not self._message_queue.empty():
            try:
                self._message_queue.get_nowait()
            except queue.Empty:
                break

    def _drain_message_queue(self) -> None:
        while True:
            try:
                received_at, message = self._message_queue.get_nowait()
            except queue.Empty:
                return

            message_id = int(message.arbitration_id)
            row = self._trace_rows.get(message_id)
            if row is None:
                row = self.trace.rowCount()
                self.trace.insertRow(row)
                self._trace_rows[message_id] = row

            elapsed = ((received_at - self.started_at).total_seconds()
                       if self.started_at else 0.0)
            frame_type = "Error" if message.is_error_frame else (
                "Remote" if message.is_remote_frame else (
                    "Extended" if message.is_extended_id else "Data"))
            values = (
                f"{elapsed:9.3f}",
                f"0x{message_id:08X}" if message.is_extended_id else f"0x{message_id:03X}",
                str(message.dlc),
                " ".join(f"{byte:02X}" for byte in message.data),
                frame_type,
            )
            for column, value in enumerate(values):
                item = self.trace.item(row, column)
                if item is None:
                    item = QTableWidgetItem()
                    self.trace.setItem(row, column, item)
                item.setText(value)
                if column == 1:
                    item.setData(32, message_id)

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.recorder and self.recorder.is_recording:
            self._stop_recording()
        event.accept()


def main() -> int:
    app = QApplication(sys.argv)
    window = CanRecorderWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
