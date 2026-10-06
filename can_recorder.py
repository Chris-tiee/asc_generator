"""Standalone CAN bus recording to Vector ASC format."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable

import can


class _MessageCounter(can.Listener):
    def __init__(self, callback: Callable[[int], None] | None = None):
        self.count = 0
        self.callback = callback

    def on_message_received(self, msg: can.Message) -> None:
        self.count += 1
        if self.callback:
            self.callback(self.count)


class CanRecorder:
    """Open a CAN bus and continuously write received messages to an ASC file."""

    def __init__(self, interface: str, channel: str | int, bitrate: int,
                 output_file: str | Path, receive_own_messages: bool = True,
                 on_message_count: Callable[[int], None] | None = None) -> None:
        self.interface = interface.strip()
        self.channel = channel.strip() if isinstance(channel, str) else channel
        self.bitrate = int(bitrate)
        self.output_file = Path(output_file)
        self.receive_own_messages = receive_own_messages
        self.on_message_count = on_message_count
        self._bus: can.Bus | None = None
        self._notifier: can.Notifier | None = None
        self._logger: can.Logger | None = None
        self._counter: _MessageCounter | None = None
        self._last_count = 0
        self._lock = threading.RLock()

    @property
    def is_recording(self) -> bool:
        return self._notifier is not None

    @property
    def message_count(self) -> int:
        return self._counter.count if self._counter else self._last_count

    def start(self) -> None:
        with self._lock:
            if self.is_recording:
                raise RuntimeError("Recording is already running")
            if not self.interface or self.channel is None or self.channel == "":
                raise ValueError("CAN interface and channel are required")
            self.output_file.parent.mkdir(parents=True, exist_ok=True)
            self._last_count = 0
            try:
                self._bus = can.Bus(interface=self.interface, channel=self.channel,
                                    bitrate=self.bitrate,
                                    receive_own_messages=self.receive_own_messages,
                                    rx_queue_size=1024)
                self._logger = can.Logger(str(self.output_file))
                self._counter = _MessageCounter(self.on_message_count)
                self._notifier = can.Notifier(self._bus, [self._logger, self._counter])
            except Exception:
                self._cleanup()
                raise

    def stop(self) -> None:
        with self._lock:
            self._cleanup()

    def _cleanup(self) -> None:
        notifier, bus, logger = self._notifier, self._bus, self._logger
        if self._counter is not None:
            self._last_count = self._counter.count
        self._notifier = self._bus = self._logger = self._counter = None
        if notifier is not None:
            notifier.stop()
        if logger is not None:
            logger.stop()
        if bus is not None:
            bus.shutdown()

    def __enter__(self) -> "CanRecorder":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()
