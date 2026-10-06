"""PySide6 GUI for recording a CAN bus to an ASC trace."""

from __future__ import annotations

import sys
import queue
from datetime import datetime
from pathlib import Path

import can
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QRegion
from PySide6.QtWidgets import (QApplication, QCheckBox, QFileDialog,
    QFormLayout, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QSplitter, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget, QAbstractItemView, QHeaderView,
    QListWidget, QListWidgetItem, QScrollArea)

try:
    from .design import DropdownComboBox
except ImportError:
    from design import DropdownComboBox

try:
    # Package execution: python -m asc_generator.can_recorder_gui
    from .can_recorder import CanRecorder
except ImportError:
    # Direct execution from inside asc_generator: python can_recorder_gui.py
    from can_recorder import CanRecorder


class RoundedCard(QFrame):
    """Card with a genuinely clipped rounded background and border."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._update_round_mask()

    def resizeEvent(self, event) -> None:  # noqa: N802
        self._update_round_mask()
        super().resizeEvent(event)

    def _update_round_mask(self) -> None:
        width, height, radius = self.width(), self.height(), 14
        if width <= 0 or height <= 0:
            return
        mask = QRegion(radius, 0, max(1, width - 2 * radius), height)
        mask += QRegion(0, radius, width, max(1, height - 2 * radius))
        mask += QRegion(0, 0, 2 * radius, 2 * radius, QRegion.RegionType.Ellipse)
        mask += QRegion(width - 2 * radius, 0, 2 * radius, 2 * radius, QRegion.RegionType.Ellipse)
        mask += QRegion(0, height - 2 * radius, 2 * radius, 2 * radius, QRegion.RegionType.Ellipse)
        mask += QRegion(width - 2 * radius, height - 2 * radius,
                        2 * radius, 2 * radius, QRegion.RegionType.Ellipse)
        self.setMask(mask)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(0, 0, -1, -1)
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(QPen(QColor("#dce4ef"), 1))
        painter.drawRoundedRect(rect, 14, 14)
        painter.end()
        super().paintEvent(event)


class RoundedTraceTable(QTableWidget):
    """Trace table whose viewport is clipped to its rounded border."""

    def __init__(self, rows: int, columns: int, parent: QWidget | None = None) -> None:
        super().__init__(rows, columns, parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._update_round_mask()

    def resizeEvent(self, event) -> None:  # noqa: N802
        self._update_round_mask()
        super().resizeEvent(event)

    def _update_round_mask(self) -> None:
        width, height, radius = self.width(), self.height(), 9
        if width <= 0 or height <= 0:
            return
        mask = QRegion(radius, 0, max(1, width - 2 * radius), height)
        mask += QRegion(0, radius, width, max(1, height - 2 * radius))
        mask += QRegion(0, 0, 2 * radius, 2 * radius, QRegion.RegionType.Ellipse)
        mask += QRegion(width - 2 * radius, 0, 2 * radius, 2 * radius, QRegion.RegionType.Ellipse)
        mask += QRegion(0, height - 2 * radius, 2 * radius, 2 * radius, QRegion.RegionType.Ellipse)
        mask += QRegion(width - 2 * radius, height - 2 * radius,
                        2 * radius, 2 * radius, QRegion.RegionType.Ellipse)
        self.setMask(mask)


class ChannelListWidget(QListWidget):
    """Always-visible, scrollable channel picker with full-row toggling."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("channelList")
        self.setFixedHeight(112)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        item = self.itemAt(event.position().toPoint())
        if item is not None and item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
            item.setCheckState(
                Qt.CheckState.Unchecked
                if item.checkState() == Qt.CheckState.Checked
                else Qt.CheckState.Checked
            )
            event.accept()
            return
        super().mousePressEvent(event)

    def checked_data(self) -> list[object]:
        return [
            self.item(index).data(Qt.ItemDataRole.UserRole)
            for index in range(self.count())
            if self.item(index).checkState() == Qt.CheckState.Checked
        ]


class CanRecorderWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("CAN ASC Recorder")
        self.resize(1160, 720)
        self.setMinimumSize(980, 560)
        self.recorder: CanRecorder | None = None
        self.started_at: datetime | None = None
        self._message_queue: queue.Queue[tuple[datetime, can.Message]] = queue.Queue()
        self._trace_rows: dict[tuple[object, int], int] = {}
        self._active_channel_label: str | None = None

        self.interface = DropdownComboBox()
        self.interface.setEditable(False)
        self.interface.addItems(["slcan", "vector"])
        self.channel = ChannelListWidget()
        self.channel.itemChanged.connect(self._channel_item_changed)
        self.refresh_ports = QPushButton("Refresh")
        self.refresh_ports.clicked.connect(self._load_channels)
        self.interface.currentTextChanged.connect(self._interface_changed)
        self._load_channels()
        self.bitrate = QLineEdit("500")
        self.bitrate.setPlaceholderText("e.g. 500")
        self.output = QLineEdit(str(Path.cwd() / "can_recording.asc"))
        browse = QPushButton("Browse...")
        browse.clicked.connect(self._browse_output)
        output_row = QHBoxLayout()
        output_row.addWidget(self.output)
        output_row.addWidget(browse)
        channel_panel = QVBoxLayout()
        channel_panel.setContentsMargins(0, 0, 0, 0)
        channel_panel.setSpacing(8)
        channel_panel.addWidget(self.channel)
        refresh_row = QHBoxLayout()
        refresh_row.setContentsMargins(0, 0, 0, 0)
        refresh_row.addWidget(self.refresh_ports, 1)
        channel_panel.addLayout(refresh_row)
        self.receive_own = QCheckBox("Receive own transmitted messages")
        self.receive_own.setChecked(True)

        form = QFormLayout()
        form.addRow("CAN interface", self.interface)
        form.addRow("Channel / port", channel_panel)
        form.addRow("Bitrate (kbits/s)", self.bitrate)
        form.addRow("ASC output file", output_row)
        form.addRow("", self.receive_own)
        settings = RoundedCard()
        settings_layout = QVBoxLayout(settings)
        settings_layout.setContentsMargins(22, 20, 22, 22)
        settings_layout.setSpacing(14)
        settings_title = QLabel("Recording settings")
        settings_title.setObjectName("sectionTitle")
        settings_help = QLabel("Configure the CAN interface and choose where the ASC trace is saved.")
        settings_help.setObjectName("helperText")
        settings_help.setWordWrap(True)
        settings_layout.addWidget(settings_title)
        settings_layout.addWidget(settings_help)
        settings_layout.addLayout(form)

        self.record_button = QPushButton("Start recording")
        self.record_button.setObjectName("primaryButton")
        self.record_button.clicked.connect(self._toggle_recording)
        self.status = QLabel("Ready")
        self.status.setObjectName("statusLabel")
        self.count = QLabel("Messages: 0")
        self.count.setObjectName("metricLabel")
        self.elapsed = QLabel("Duration: 00:00:00")
        self.elapsed.setObjectName("metricLabel")
        info = QGridLayout()
        info.addWidget(self.status, 0, 0, 1, 2)
        info.addWidget(self.count, 1, 0)
        info.addWidget(self.elapsed, 1, 1)

        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)
        root.addWidget(settings)
        root.addWidget(self.record_button)
        root.addLayout(info)
        root.addStretch()

        left_panel = QWidget()
        left_panel.setLayout(root)
        left_panel.setMinimumWidth(340)

        left_scroll = QScrollArea()
        left_scroll.setObjectName("leftPanelScroll")
        left_scroll.setMinimumWidth(360)
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        left_scroll.setWidget(left_panel)

        self.trace = RoundedTraceTable(0, 5)
        self.trace.setObjectName("traceTable")
        self.trace.setHorizontalHeaderLabels(["Time", "Channel", "ID", "DLC", "Data"])
        self._update_trace_channel_header()
        self.trace.setAlternatingRowColors(True)
        self.trace.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.trace.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.trace.setSelectionMode(QAbstractItemView.SingleSelection)
        self.trace.verticalHeader().setVisible(False)
        header = self.trace.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        trace_box = RoundedCard()
        trace_layout = QVBoxLayout(trace_box)
        trace_layout.setContentsMargins(22, 20, 22, 22)
        trace_layout.setSpacing(12)
        trace_title = QLabel("Live CAN trace")
        trace_title.setObjectName("sectionTitle")
        trace_help = QLabel("The latest message is shown for each unique CAN ID.")
        trace_help.setObjectName("helperText")
        trace_layout.addWidget(trace_title)
        trace_layout.addWidget(trace_help)
        trace_frame = QFrame()
        trace_frame.setObjectName("traceFrame")
        trace_frame_layout = QVBoxLayout(trace_frame)
        trace_frame_layout.setContentsMargins(0, 0, 0, 0)
        trace_frame_layout.addWidget(self.trace)
        trace_layout.addWidget(trace_frame)

        splitter = QSplitter()
        splitter.addWidget(left_scroll)
        splitter.addWidget(trace_box)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setHandleWidth(24)
        splitter.setSizes([360, 700])
        content = QWidget()
        content.setObjectName("appBackground")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(32, 28, 32, 28)
        content_layout.addWidget(splitter, 1)
        self.setCentralWidget(content)

        self.setStyleSheet("""
            QWidget#appBackground {
                background: #f3f6fa;
                color: #172033;
                font-family: "Segoe UI";
                font-size: 13px;
            }
            QScrollArea#leftPanelScroll {
                border: none;
                background: transparent;
            }
            QScrollArea#leftPanelScroll > QWidget > QWidget {
                background: transparent;
            }
            QScrollBar:vertical {
                width: 10px;
                border: none;
                border-radius: 5px;
                background: #e7ecf3;
            }
            QScrollBar::handle:vertical {
                min-height: 28px;
                border-radius: 4px;
                background: #aebaca;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            QLabel#helperText {
                color: #68758a;
            }
            QLabel#sectionTitle {
                color: #172033;
                font-size: 16px;
                font-weight: 650;
            }
            QFrame#card {
                background: transparent;
                border: none;
            }
            QComboBox, QLineEdit {
                min-height: 38px;
                padding: 0 11px;
                border: 1px solid #ccd6e4;
                border-radius: 8px;
                background: white;
                color: #1d2940;
                selection-background-color: #dce9ff;
            }
            QComboBox:hover, QLineEdit:hover {
                border-color: #9fb3d2;
            }
            QComboBox:focus, QLineEdit:focus {
                border: 1px solid #3474df;
            }
            QComboBox::drop-down {
                width: 28px;
                border: none;
            }
            QListWidget#channelList {
                border: 1px solid #ccd6e4;
                border-radius: 8px;
                background: #f8fafd;
                color: #1d2940;
                padding: 2px;
            }
            QListWidget#channelList::item {
                min-height: 30px;
                padding: 4px 8px;
                border-radius: 5px;
            }
            QListWidget#channelList::item:hover {
                background: #eaf1fc;
            }
            QListWidget#channelList::indicator {
                width: 15px;
                height: 15px;
            }
            QListWidget#channelList QScrollBar:vertical {
                width: 10px;
                border: none;
                border-radius: 5px;
                background: #e7ecf3;
            }
            QListWidget#channelList QScrollBar::handle:vertical {
                min-height: 24px;
                border-radius: 4px;
                background: #aebaca;
            }
            QListWidget#channelList QScrollBar::add-line:vertical,
            QListWidget#channelList QScrollBar::sub-line:vertical {
                height: 0;
            }
            QCheckBox {
                color: #344157;
                spacing: 8px;
            }
            QPushButton {
                min-height: 38px;
                padding: 0 16px;
                border: 1px solid #c9d5e5;
                border-radius: 8px;
                background: #ffffff;
                color: #25324a;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #f5f8fc;
                border-color: #a8b9d0;
            }
            QPushButton#primaryButton {
                min-height: 52px;
                border: none;
                border-radius: 10px;
                background: #2868d7;
                color: white;
                font-size: 15px;
                font-weight: 700;
            }
            QPushButton#primaryButton:hover {
                background: #205bc1;
            }
            QPushButton#primaryButton:pressed {
                background: #194b9f;
            }
            QPushButton#primaryButton:disabled {
                background: #b9c5d6;
                color: #eef2f7;
            }
            QLabel#statusLabel {
                color: #2868d7;
                font-weight: 700;
            }
            QLabel#metricLabel {
                color: #68758a;
                font-size: 12px;
            }
            QTableWidget#traceTable {
                border: none;
                background: #f8fafd;
                color: #344157;
                gridline-color: #e6ebf2;
                selection-background-color: #dce9ff;
                selection-color: #172033;
                font-family: "Consolas";
                font-size: 12px;
            }
            QFrame#traceFrame {
                background: transparent;
                border: 1px solid #d7e0eb;
                border-radius: 9px;
            }
            QTableWidget#traceTable QHeaderView::section {
                padding: 8px 10px;
                border: none;
                border-bottom: 1px solid #d7e0eb;
                background: #eef3f9;
                color: #68758a;
                font-family: "Segoe UI";
                font-size: 11px;
                font-weight: 700;
            }
            QSplitter::handle {
                background: #f3f6fa;
            }
        """)

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
                    serial = config.get("serial")
                    channels.append(f"{name} (SN {serial})")
                    channel_data.append({
                        "channel": config.get("channel"),
                        "serial": serial,
                    })
            except Exception:
                pass
        else:
            try:
                from serial.tools import list_ports
                channels = sorted({p.device for p in list_ports.comports()})
            except Exception:
                pass
        self.channel.clear()
        self.channel.blockSignals(True)
        if channels:
            for index, value in enumerate(channels):
                item = QListWidgetItem(value)
                item.setData(
                    Qt.ItemDataRole.UserRole,
                    channel_data[index] if channel_data else value,
                )
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(
                    Qt.CheckState.Checked if index == 0 else Qt.CheckState.Unchecked
                )
                self.channel.addItem(item)
        else:
            item = QListWidgetItem("No channels detected")
            item.setData(Qt.ItemDataRole.UserRole, None)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.channel.addItem(item)
        self.channel.blockSignals(False)

    def _channel_item_changed(self, changed_item: QListWidgetItem) -> None:
        if self.interface.currentText() == "vector":
            return
        if changed_item.checkState() != Qt.CheckState.Checked:
            return
        self.channel.blockSignals(True)
        for index in range(self.channel.count()):
            item = self.channel.item(index)
            if item is not changed_item:
                item.setCheckState(Qt.CheckState.Unchecked)
        self.channel.blockSignals(False)

    def _interface_changed(self, _interface: str) -> None:
        if hasattr(self, "trace"):
            self._update_trace_channel_header()
        self._load_channels()

    def _update_trace_channel_header(self) -> None:
        title = "COM port" if self.interface.currentText() == "slcan" else "Channel"
        self.trace.setHorizontalHeaderItem(1, QTableWidgetItem(title))

    def _browse_output(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(self, "Save ASC recording", self.output.text(), "ASC trace (*.asc)")
        if filename:
            self.output.setText(filename if filename.lower().endswith(".asc") else filename + ".asc")

    def _toggle_recording(self) -> None:
        if self.recorder and self.recorder.is_recording:
            self._stop_recording()
            return
        try:
            selected_channels = self.channel.checked_data()
            if self.interface.currentText() == "vector":
                channel = selected_channels
            else:
                channel = selected_channels[0] if selected_channels else None
            self._active_channel_label = str(channel) if channel is not None else None
            self.recorder = CanRecorder(self.interface.currentText(), channel,
                                        int(self.bitrate.text()) * 1000, self.output.text(),
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
        self._active_channel_label = None
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
            message_channel = getattr(message, "channel", None)
            if message_channel is None and self.interface.currentText() == "slcan":
                message_channel = self._active_channel_label
            row_key = (message_channel, message_id)
            row = self._trace_rows.get(row_key)
            if row is None:
                row = self.trace.rowCount()
                self.trace.insertRow(row)
                self._trace_rows[row_key] = row

            elapsed = ((received_at - self.started_at).total_seconds()
                       if self.started_at else 0.0)
            values = (
                f"{elapsed:9.3f}",
                str(message_channel) if message_channel is not None else "—",
                f"0x{message_id:08X}" if message.is_extended_id else f"0x{message_id:03X}",
                str(message.dlc),
                " ".join(f"{byte:02X}" for byte in message.data),
            )
            for column, value in enumerate(values):
                item = self.trace.item(row, column)
                if item is None:
                    item = QTableWidgetItem()
                    self.trace.setItem(row, column, item)
                item.setText(value)
                if column == 2:
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
