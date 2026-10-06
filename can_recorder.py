"""Standalone CAN bus recording to Vector ASC format."""

from __future__ import annotations

import copy
import threading
from pathlib import Path
from typing import Any, Callable

import can


class _MessageCounter(can.Listener):
    def __init__(self, callback: Callable[[int], None] | None = None,
                 message_callback: Callable[[can.Message], None] | None = None,
                 source_label: str | None = None,
                 vector_source: bool = False):
        self.count = 0
        self.callback = callback
        self.message_callback = message_callback
        self.source_label = source_label
        self.vector_source = vector_source

    def on_message_received(self, msg: can.Message) -> None:
        self.count += 1
        if self.callback:
            self.callback(self.count)
        if self.message_callback:
            if self.source_label:
                msg = copy.copy(msg)
                if self.vector_source:
                    raw_channel = getattr(msg, "channel", "?")
                    try:
                        channel_label = f"CH{int(raw_channel) + 1}"
                    except (TypeError, ValueError):
                        channel_label = f"CH{raw_channel}"
                    msg.channel = f"{channel_label} ({self.source_label.replace(' ', '')})"
                else:
                    msg.channel = self.source_label
            self.message_callback(msg)


class _ThreadSafeAscLogger(can.Listener):
    """Share one ASC logger and periodically flush it to disk."""

    _FLUSH_INTERVAL_SECONDS = 5 * 60

    def __init__(self, output_file: Path) -> None:
        self._logger = can.Logger(str(output_file))
        self._lock = threading.RLock()
        self._closed = False
        self._flush_stop = threading.Event()
        self._flush_thread = threading.Thread(
            target=self._flush_periodically,
            name="can-asc-flush",
            daemon=True,
        )
        self._flush_thread.start()

    def on_message_received(self, msg: can.Message) -> None:
        with self._lock:
            if not self._closed:
                self._logger.on_message_received(msg)

    def stop(self) -> None:
        # Notifier.stop() calls listener.stop(). The recorder closes the logger
        # only after all notifiers have stopped.
        return

    def _flush_periodically(self) -> None:
        while not self._flush_stop.wait(self._FLUSH_INTERVAL_SECONDS):
            with self._lock:
                if self._closed:
                    return
                file = getattr(self._logger, "file", None)
                if file is not None and not file.closed:
                    file.flush()

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._closed = True
                self._flush_stop.set()
                self._flush_thread.join(timeout=1.0)
                self._logger.stop()


class CanRecorder:
    """Open a CAN bus and continuously write received messages to an ASC file."""

    def __init__(self, interface: str, channel: str | int | list[dict[str, Any]], bitrate: int,
                 output_file: str | Path, receive_own_messages: bool = True,
                 on_message_count: Callable[[int], None] | None = None,
                 on_message: Callable[[can.Message], None] | None = None) -> None:
        self.interface = interface.strip()
        self.channel = channel.strip() if isinstance(channel, str) else channel
        self.bitrate = int(bitrate)
        self.output_file = Path(output_file)
        self.receive_own_messages = receive_own_messages
        self.on_message_count = on_message_count
        self.on_message = on_message
        self._buses: list[can.Bus] = []
        self._notifiers: list[can.Notifier] = []
        self._logger: _ThreadSafeAscLogger | None = None
        self._counters: list[_MessageCounter] = []
        self._last_count = 0
        self._lock = threading.RLock()

    @property
    def is_recording(self) -> bool:
        return bool(self._notifiers)

    @property
    def message_count(self) -> int:
        return (sum(counter.count for counter in self._counters)
                if self._counters else self._last_count)

    def start(self) -> None:
        with self._lock:
            if self.is_recording:
                raise RuntimeError("Recording is already running")
            if not self.interface or self.channel is None or self.channel == "":
                raise ValueError("CAN interface and channel are required")
            self.output_file.parent.mkdir(parents=True, exist_ok=True)
            self._last_count = 0
            try:
                self._logger = _ThreadSafeAscLogger(self.output_file)
                bus_configs = self._bus_configs()
                for bus_config in bus_configs:
                    bus = can.Bus(**bus_config)
                    source_label = None
                    vector_source = self.interface == "vector"
                    if vector_source and bus_config.get("serial") is not None:
                        source_label = f"SN {bus_config['serial']}"
                    elif not vector_source:
                        source_label = str(bus_config["channel"])
                    counter = _MessageCounter(
                        self.on_message_count,
                        self.on_message,
                        source_label,
                        vector_source,
                    )
                    notifier = can.Notifier(bus, [self._logger, counter])
                    self._buses.append(bus)
                    self._counters.append(counter)
                    self._notifiers.append(notifier)
            except Exception:
                self._cleanup()
                raise

    def _bus_configs(self) -> list[dict[str, Any]]:
        common = {
            "interface": self.interface,
            "bitrate": self.bitrate,
            "receive_own_messages": self.receive_own_messages,
            "rx_queue_size": 1024,
        }
        if self.interface != "vector":
            channels = self.channel if isinstance(self.channel, list) else [self.channel]
            if not channels or any(channel in (None, "") for channel in channels):
                raise ValueError("Select at least one COM port")
            return [{**common, "channel": channel} for channel in channels]

        if not isinstance(self.channel, list) or not self.channel:
            raise ValueError("Select at least one Vector channel")

        grouped: dict[int | None, list[int]] = {}
        for selected in self.channel:
            if not isinstance(selected, dict):
                raise ValueError("Vector channel selections are invalid")
            serial = selected.get("serial")
            channel = selected.get("channel")
            if channel is None:
                raise ValueError("A selected Vector channel has no channel index")
            grouped.setdefault(serial, []).append(int(channel))

        configs = []
        for serial, channels in grouped.items():
            config = {**common, "channel": channels}
            if serial is not None:
                config["serial"] = serial
            configs.append(config)
        return configs

    def stop(self) -> None:
        with self._lock:
            self._cleanup()

    def _cleanup(self) -> None:
        self._last_count = sum(counter.count for counter in self._counters)
        notifiers, buses, logger = self._notifiers, self._buses, self._logger
        self._notifiers = []
        self._buses = []
        self._counters = []
        self._logger = None
        for notifier in notifiers:
            notifier.stop()
        if logger is not None:
            logger.close()
        for bus in buses:
            bus.shutdown()

    def __enter__(self) -> "CanRecorder":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()
