"""Reusable UI widgets and styling helpers for the CAN recorder GUI."""

from __future__ import annotations

import time

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen, QRegion
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QComboBox,
    QFrame,
    QListWidget,
    QTableWidget,
    QStyledItemDelegate,
    QStyle,
    QStyleOptionViewItem,
)


class DropdownComboBox(QComboBox):
    """Combo box with a consistently visible dropdown chevron."""

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor("#718096" if self.isEnabled() else "#aab5c4")
        painter.setPen(QPen(color, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        center_x = self.width() - 16
        center_y = self.height() // 2
        painter.drawLine(center_x - 4, center_y - 2, center_x, center_y + 2)
        painter.drawLine(center_x, center_y + 2, center_x + 4, center_y - 2)
        painter.end()


class RoundedCard(QFrame):
    """Card with a clipped rounded background and border."""

    def __init__(self, parent=None) -> None:
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

    def __init__(self, rows: int, columns: int, parent=None) -> None:
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


class DataFadeDelegate(QStyledItemDelegate):
    """Render each data byte darker when it changes and lighter when stable."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._half_life_seconds = 2.5
        self._minimum_alpha = 72

    def paint(self, painter, option, index) -> None:  # noqa: N802
        item_option = QStyleOptionViewItem(option)
        self.initStyleOption(item_option, index)
        item_option.text = ""
        style = item_option.widget.style() if item_option.widget else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem,
                          item_option, painter, item_option.widget)

        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        metadata = index.data(Qt.ItemDataRole.UserRole) or {}
        change_times = metadata.get("change_times", [])
        byte_values = text.split()
        if not byte_values:
            return

        painter.save()
        painter.setFont(item_option.font)
        metrics = painter.fontMetrics()
        x = item_option.rect.left() + 10
        baseline = item_option.rect.top() + (item_option.rect.height() + metrics.ascent() - metrics.descent()) // 2
        now = time.monotonic()
        for byte_index, byte_text in enumerate(byte_values):
            changed_at = change_times[byte_index] if byte_index < len(change_times) else now
            age = max(0.0, now - changed_at)
            alpha = max(self._minimum_alpha, int(255 * (0.5 ** (age / self._half_life_seconds))))
            color = QColor("#344157")
            color.setAlpha(alpha)
            painter.setPen(color)
            painter.drawText(x, baseline, byte_text)
            x += metrics.horizontalAdvance(byte_text + "  ")
        painter.restore()


class ChannelListWidget(QListWidget):
    """Scrollable channel picker with full-row checkbox toggling."""

    def __init__(self, parent=None) -> None:
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



APP_STYLE = """
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
    QScrollArea#leftPanelScroll > QWidget > QWidget { background: transparent; }
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
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
    QLabel#helperText { color: #68758a; }
    QLabel#sectionTitle {
        color: #172033;
        font-size: 16px;
        font-weight: 650;
    }
    QFrame#card { background: transparent; border: none; }
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
    QComboBox:focus, QLineEdit:focus { border: 1px solid #3474df; }
    QComboBox:disabled, QLineEdit:disabled {
        border-color: #d3dbe6;
        background: #e7ecf3;
        color: #8a96a8;
    }
    QComboBox::drop-down { width: 28px; border: none; }
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
        color: #1d2940;
        border-radius: 5px;
    }
    QListWidget#channelList:enabled { background: #f8fafd; color: #1d2940; }
    QListWidget#channelList:enabled::item,
    QListWidget#channelList:enabled::item:hover {
        background: transparent;
        color: #1d2940;
    }
    QListWidget#channelList::item:hover { background: #eaf1fc; }
    QListWidget#channelList:disabled {
        border-color: #d3dbe6;
        background: #e7ecf3;
        color: #8a96a8;
    }
    QListWidget#channelList:disabled::item,
    QListWidget#channelList:disabled::item:hover {
        background: transparent;
        color: #8a96a8;
    }
    QListWidget#channelList::indicator { width: 15px; height: 15px; }
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
    QListWidget#channelList QScrollBar::sub-line:vertical { height: 0; }
    QCheckBox { color: #344157; spacing: 8px; }
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
    QPushButton:disabled {
        border-color: #d3dbe6;
        background: #e7ecf3;
        color: #8a96a8;
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
    QPushButton#primaryButton:hover { background: #205bc1; }
    QPushButton#primaryButton:pressed { background: #194b9f; }
    QPushButton#primaryButton:disabled {
        background: #b9c5d6;
        color: #eef2f7;
    }
    QPushButton#primaryButton:disabled:hover {
        background: #b9c5d6;
        color: #eef2f7;
        border: none;
    }
    QLabel#statusLabel { color: #2868d7; font-weight: 700; }
    QLabel#metricLabel { color: #68758a; font-size: 12px; }
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
        padding: 8px 6px;
        border: none;
        border-bottom: 1px solid #d7e0eb;
        background: #eef3f9;
        color: #68758a;
        font-family: "Segoe UI";
        font-size: 11px;
        font-weight: 700;
    }
    QTableWidget#traceTable QHeaderView::up-arrow,
    QTableWidget#traceTable QHeaderView::down-arrow { image: none; }
    QSplitter::handle { background: #f3f6fa; }
"""


DISABLED_CHANNEL_STYLE = """
    QListWidget#channelList {
        border: 1px solid #d3dbe6;
        border-radius: 8px;
        background: #e1e6ee;
        color: #8a96a8;
    }
    QListWidget#channelList::item,
    QListWidget#channelList::item:hover {
        background: transparent;
        color: #8a96a8;
    }
"""


DISABLED_INTERFACE_STYLE = """
    QComboBox {
        min-height: 38px;
        padding: 0 11px;
        border: 1px solid #d3dbe6;
        border-radius: 8px;
        background: #e1e6ee;
        color: #8a96a8;
    }
    QComboBox::drop-down { width: 28px; border: none; }
"""

