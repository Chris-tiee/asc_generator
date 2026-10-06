"""Small helpers for discovering and presenting CAN channels."""

from __future__ import annotations

from typing import Any

import can


def discover_channels(interface: str) -> tuple[list[str], list[Any]]:
    """Return display names and backend values for the selected interface."""
    if interface == "vector":
        return _discover_vector_channels()
    return _discover_slcan_ports()


def _discover_vector_channels() -> tuple[list[str], list[dict[str, Any]]]:
    names: list[str] = []
    data: list[dict[str, Any]] = []
    try:
        configs = can.detect_available_configs(interfaces=["vector"])
    except Exception:
        return names, data

    for config in configs:
        channel_config = config.get("vector_channel_config")
        if channel_config is None:
            continue
        name = channel_config.name
        if name.lower().startswith("virtual"):
            continue
        serial = config.get("serial")
        names.append(f"{name} (SN {serial})")
        data.append({"channel": config.get("channel"), "serial": serial})
    return names, data


def _discover_slcan_ports() -> tuple[list[str], list[str]]:
    try:
        from serial.tools import list_ports
        ports = sorted({port.device for port in list_ports.comports()})
    except Exception:
        ports = []
    return ports, ports.copy()


def channel_column_title(interface: str) -> str:
    """Return the trace column title for an interface."""
    return "COM port" if interface == "slcan" else "Channel"


def display_channel_label(message_channel: object) -> str:
    """Return a safe display value for a message channel."""
    return str(message_channel) if message_channel is not None else "-"
