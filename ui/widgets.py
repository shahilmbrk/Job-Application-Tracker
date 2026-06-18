"""
ui/widgets.py - Reusable custom widgets for Application Tracker
"""

from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame,
    QPushButton, QGraphicsDropShadowEffect, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QPoint, QSize
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QPainterPath, QLinearGradient
from ui.styles import STATUS_COLORS, PRIORITY_COLORS, COLORS


# ──────────────────────────────────────────────────────────────────────────────
# Badge / pill label
# ──────────────────────────────────────────────────────────────────────────────

class Badge(QLabel):
    """Coloured pill badge (e.g. for status or priority)."""

    def __init__(self, text: str = "", color_pair: tuple = None, parent=None):
        super().__init__(text, parent)
        fg, bg = color_pair or (COLORS["accent_blue"], "#1f4280")
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {fg}44;
                border-radius: 10px;
                padding: 2px 10px;
                font-size: 11px;
                font-weight: 600;
            }}
        """)
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)

    @staticmethod
    def for_status(status: str) -> "Badge":
        pair = STATUS_COLORS.get(status, (COLORS["text_secondary"], COLORS["bg_card"]))
        return Badge(status, pair)

    @staticmethod
    def for_priority(priority: str) -> "Badge":
        pair = PRIORITY_COLORS.get(priority, (COLORS["text_secondary"], COLORS["bg_card"]))
        return Badge(priority, pair)


# ──────────────────────────────────────────────────────────────────────────────
# Stat Card
# ──────────────────────────────────────────────────────────────────────────────

class StatCard(QFrame):
    """A dashboard metric card with icon, value, label, and optional trend."""

    clicked = Signal()

    def __init__(self, title: str, value: str, icon: str, color: str,
                 subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(110)
        self._color = color

        self.setStyleSheet(f"""
            QFrame#statCard {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
            }}
            QFrame#statCard:hover {{
                border-color: {color};
                background-color: {COLORS['bg_hover']};
            }}
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.setGraphicsEffect(shadow)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(14)

        # Icon circle
        icon_lbl = QLabel(icon)
        icon_lbl.setFixedSize(48, 48)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(f"""
            QLabel {{
                background-color: {color}22;
                border: 1px solid {color}44;
                border-radius: 24px;
                font-size: 22px;
                color: {color};
            }}
        """)
        layout.addWidget(icon_lbl)

        # Text block
        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        self.value_lbl = QLabel(value)
        self.value_lbl.setStyleSheet(f"""
            font-size: 28px; font-weight: 700;
            color: {COLORS['text_primary']};
        """)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")

        text_col.addWidget(self.value_lbl)
        text_col.addWidget(title_lbl)

        if subtitle:
            sub_lbl = QLabel(subtitle)
            sub_lbl.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: 500;")
            text_col.addWidget(sub_lbl)

        layout.addLayout(text_col)
        layout.addStretch()

        # Accent bar on the left edge (drawn via border trick)
        self._left_bar = QFrame(self)
        self._left_bar.setFixedWidth(4)
        self._left_bar.setStyleSheet(f"background:{color}; border-radius:2px;")
        self._left_bar.setGeometry(0, 12, 4, 86)

    def set_value(self, v: str):
        self.value_lbl.setText(v)

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


# ──────────────────────────────────────────────────────────────────────────────
# Empty State widget
# ──────────────────────────────────────────────────────────────────────────────

class EmptyState(QWidget):
    action_clicked = Signal()

    def __init__(self, emoji: str, title: str, subtitle: str,
                 btn_text: str = "", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(10)

        emoji_lbl = QLabel(emoji)
        emoji_lbl.setAlignment(Qt.AlignCenter)
        emoji_lbl.setStyleSheet("font-size: 52px; background: transparent;")

        title_lbl = QLabel(title)
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setStyleSheet(f"""
            font-size: 18px; font-weight: 600;
            color: {COLORS['text_primary']}; background: transparent;
        """)

        sub_lbl = QLabel(subtitle)
        sub_lbl.setAlignment(Qt.AlignCenter)
        sub_lbl.setWordWrap(True)
        sub_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")

        layout.addStretch()
        layout.addWidget(emoji_lbl)
        layout.addWidget(title_lbl)
        layout.addWidget(sub_lbl)

        if btn_text:
            btn = QPushButton(f"  {btn_text}")
            btn.setObjectName("primaryBtn")
            btn.setFixedSize(180, 40)
            btn.clicked.connect(self.action_clicked)
            btn_row = QHBoxLayout()
            btn_row.addStretch()
            btn_row.addWidget(btn)
            btn_row.addStretch()
            layout.addSpacing(8)
            layout.addLayout(btn_row)

        layout.addStretch()


# ──────────────────────────────────────────────────────────────────────────────
# Divider
# ──────────────────────────────────────────────────────────────────────────────

class HDivider(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.HLine)
        self.setStyleSheet(f"color: {COLORS['border']};")
        self.setFixedHeight(1)


# ──────────────────────────────────────────────────────────────────────────────
# Section Header
# ──────────────────────────────────────────────────────────────────────────────

class SectionHeader(QWidget):
    def __init__(self, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 4)
        layout.setSpacing(2)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"""
            font-size: 16px; font-weight: 700;
            color: {COLORS['text_primary']}; background: transparent;
        """)
        layout.addWidget(title_lbl)

        if subtitle:
            sub = QLabel(subtitle)
            sub.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; background: transparent;")
            layout.addWidget(sub)


# ──────────────────────────────────────────────────────────────────────────────
# Activity Item
# ──────────────────────────────────────────────────────────────────────────────

class ActivityItem(QFrame):
    def __init__(self, action: str, description: str, company: str,
                 timestamp: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        # Dot indicator
        dot_map = {
            "Created": COLORS["accent_blue"],
            "Updated": COLORS["accent_orange"],
            "Attachment": COLORS["accent_purple"],
        }
        dot_color = dot_map.get(action, COLORS["text_muted"])
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {dot_color}; font-size: 10px; background: transparent;")
        dot.setFixedWidth(14)
        layout.addWidget(dot)

        col = QVBoxLayout()
        col.setSpacing(2)

        desc_lbl = QLabel(description or "–")
        desc_lbl.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 12px; background: transparent;")

        meta = f"{company}  ·  {timestamp[:16] if timestamp else ''}"
        meta_lbl = QLabel(meta)
        meta_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px; background: transparent;")

        col.addWidget(desc_lbl)
        col.addWidget(meta_lbl)
        layout.addLayout(col)
        layout.addStretch()

        badge = Badge(action)
        layout.addWidget(badge)
