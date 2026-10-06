"""Reusable widgets and application-wide visual styling."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QApplication, QComboBox


class DropdownComboBox(QComboBox):
    """Combo box with a consistently visible dropdown chevron."""

    def paintEvent(self, event) -> None:
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


def apply_style(app: QApplication) -> None:
    """Apply the shared Goodnight LIPY041 application stylesheet."""
    app.setStyleSheet(
        """
        QWidget#appBackground { background: #f3f6fa; color: #172033; font-family: "Segoe UI"; font-size: 13px; }
        QScrollArea#contentScroll, QScrollArea#contentScroll > QWidget > QWidget { background: #f3f6fa; border: none; }
        QScrollBar:vertical { width: 12px; margin: 4px 2px; border: none; border-radius: 5px; background: #e7ecf3; }
        QScrollBar::handle:vertical { min-height: 36px; border-radius: 4px; background: #aebaca; }
        QScrollBar::handle:vertical:hover { background: #8f9db1; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        QLabel#appMark { min-width: 46px; max-width: 46px; min-height: 46px; max-height: 46px; border-radius: 12px; background: #245fc7; color: white; font-size: 16px; font-weight: 700; }
        QFrame#lastEventCard { background: white; border: 1px solid #dce4ef; border-radius: 9px; }
        QLabel#lastEventLabel { color: #68758a; font-size: 12px; }
        QLabel#pageTitle { color: #15213a; font-size: 23px; font-weight: 700; }
        QLabel#pageSubtitle, QLabel#helperText { color: #68758a; }
        QLabel#sectionTitle { color: #172033; font-size: 16px; font-weight: 650; }
        QLabel#columnLabel { color: #7a879a; font-size: 11px; font-weight: 700; }
        QFrame#card { background: white; border: 1px solid #dce4ef; border-radius: 14px; }
        QComboBox { min-height: 38px; padding: 0 11px; border: 1px solid #ccd6e4; border-radius: 8px; background: white; color: #1d2940; selection-background-color: #dce9ff; }
        QComboBox:hover { border-color: #9fb3d2; }
        QComboBox:focus { border: 1px solid #3474df; }
        QComboBox::drop-down { width: 28px; border: none; }
        QComboBox::down-arrow { image: none; }
        QPushButton { min-height: 38px; padding: 0 16px; border: 1px solid #c9d5e5; border-radius: 8px; background: #ffffff; color: #25324a; font-weight: 600; }
        QPushButton:hover { background: #f5f8fc; border-color: #a8b9d0; }
        QPushButton#primaryButton { min-height: 40px; border: none; border-radius: 8px; background: #2868d7; color: white; font-weight: 700; }
        QPushButton#primaryButton:hover { background: #205bc1; }
        QPushButton#primaryButton:disabled { background: #aebfdf; color: #eef3fb; }
        QLabel#statusMarkBad { background: #fdecec; color: #d64545; border-radius: 24px; font-size: 24px; font-weight: 700; }
        QLabel#statusMarkWarning { background: #fff5d9; color: #b7791f; border-radius: 24px; font-size: 24px; font-weight: 700; }
        QLabel#statusMarkGood { background: #e8f7ee; color: #1f9d55; border-radius: 24px; font-size: 12px; font-weight: 700; }
        QLabel#statusDot { background: #a0aec0; border-radius: 5px; }
        QLabel#statusTitle { font-size: 15px; font-weight: 600; }
        QLabel#statusHint, QLabel#metricLabel { color: #68758a; }
        QFrame#metric { background: #f8fafd; border: 1px solid #e2e8f0; border-radius: 9px; }
        QLabel#metricValue { font-size: 24px; font-weight: 600; }
        QLabel#metricUnit { color: #68758a; font-size: 13px; }
        QPushButton#dangerButton { min-height: 52px; border: none; border-radius: 9px; background: #d64545; color: white; font-size: 14px; font-weight: 700; }
        QPushButton#dangerButton:hover { background: #bd3838; }
        QPushButton#dangerButtonDisabled { min-height: 52px; border: none; border-radius: 9px; background: #edaaaa; color: #fff8f8; font-size: 14px; font-weight: 700; }
        QPushButton#dangerButtonInProgress { min-height: 52px; border: none; border-radius: 9px; background: #e7a3a3; color: white; font-size: 14px; font-weight: 700; }
        QPushButton#dangerButtonInProgress:disabled { background: #e7a3a3; color: #fff7f7; border-color: #e7a3a3; }
        QPushButton#sleepButton { min-height: 52px; border: none; border-radius: 9px; background: #b7791f; color: white; font-size: 14px; font-weight: 700; }
        QPushButton#sleepButton:hover { background: #9c681b; }
        QPushButton#sleepButtonDisabled { min-height: 52px; border: none; border-radius: 9px; background: #d9b77f; color: #fffaf0; font-size: 14px; font-weight: 700; }
        QPushButton#sleepButtonInProgress { min-height: 52px; border: none; border-radius: 9px; background: #d9b77f; color: white; font-size: 14px; font-weight: 700; }
        QPushButton:disabled { background: #b9c5d6; color: #eef2f7; border-color: #b9c5d6; }
        QComboBox:disabled { background: #edf1f6; color: #9aa7b8; border-color: #d9e0ea; }
        QPlainTextEdit#systemLog { padding: 8px 10px; border: 1px solid #d7e0eb; border-radius: 9px; background: #f8fafd; color: #344157; font-family: "Consolas"; font-size: 12px; }
        QLabel#notice { color: #68758a; font-size: 12px; padding: 4px; }
        """
    )
