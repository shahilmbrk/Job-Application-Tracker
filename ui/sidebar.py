"""
ui/sidebar.py - Professional sidebar navigation with live status counts
"""

from typing import Dict
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont
import database as db
from ui.styles import COLORS, STATUS_COLORS

NAV_ITEMS = [
    ("dashboard",    "dashboard",    "📊", "Dashboard"),
    ("applications", "applications", "📋", "Applications"),
    ("add",          "add",          "➕", "Add New"),
    ("analytics",    "analytics",    "📈", "Analytics"),
]


class CountBadge(QLabel):
    """Small numeric pill shown beside nav items."""
    def __init__(self, parent=None):
        super().__init__("", parent)
        self.setFixedSize(22, 18)
        self.setAlignment(Qt.AlignCenter)
        self._apply_style(COLORS["accent_blue"], "#1f4280")

    def _apply_style(self, fg: str, bg: str):
        self.setStyleSheet(f"""
            QLabel {{
                background: {bg};
                color: {fg};
                border-radius: 9px;
                font-size: 10px;
                font-weight: 700;
            }}
        """)

    def set_count(self, n: int, fg: str = None, bg: str = None):
        self.setText(str(n) if n > 0 else "")
        self.setVisible(n > 0)
        if fg and bg:
            self._apply_style(fg, bg)


class NavButton(QPushButton):
    def __init__(self, icon: str, label: str, page_id: str, parent=None):
        super().__init__(parent)
        self.page_id = page_id
        self._icon_str = icon
        self._label_str = label
        self.setCheckable(True)
        self.setFixedHeight(46)
        self.setCursor(Qt.PointingHandCursor)
        self.setFlat(True)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(14, 0, 10, 0)
        self._layout.setSpacing(10)

        self._icon_lbl = QLabel(icon)
        self._icon_lbl.setFixedWidth(22)
        self._icon_lbl.setAlignment(Qt.AlignCenter)
        self._icon_lbl.setStyleSheet("background:transparent; font-size:15px;")

        self._text_lbl = QLabel(label)
        self._text_lbl.setStyleSheet("background:transparent; font-size:13px; font-weight:500;")

        self.badge = CountBadge()
        self.badge.setVisible(False)

        self._layout.addWidget(self._icon_lbl)
        self._layout.addWidget(self._text_lbl)
        self._layout.addStretch()
        self._layout.addWidget(self.badge)

        self._refresh_style()

    def setChecked(self, checked: bool):
        super().setChecked(checked)
        self._refresh_style()

    def _refresh_style(self):
        if self.isChecked():
            self.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                        stop:0 #1f6feb28, stop:1 #1f6feb10);
                    border: none;
                    border-left: 3px solid {COLORS['accent_blue']};
                    border-radius: 0px 8px 8px 0px;
                    color: {COLORS['accent_blue']};
                    text-align: left;
                    padding-left: 11px;
                }}
            """)
            self._text_lbl.setStyleSheet(
                f"background:transparent; font-size:13px; font-weight:700;"
                f" color:{COLORS['accent_blue']};"
            )
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    border-left: 3px solid transparent;
                    border-radius: 0px 8px 8px 0px;
                    color: {COLORS['text_secondary']};
                    text-align: left;
                    padding-left: 11px;
                }}
                QPushButton:hover {{
                    background: {COLORS['bg_hover']};
                    color: {COLORS['text_primary']};
                    border-left: 3px solid {COLORS['border']};
                }}
            """)
            self._text_lbl.setStyleSheet(
                f"background:transparent; font-size:13px; font-weight:500;"
            )


class MiniStatRow(QWidget):
    """A single status-count row in the sidebar summary."""
    def __init__(self, label: str, count: int, color: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 2, 14, 2)
        layout.setSpacing(8)

        dot = QLabel("●")
        dot.setStyleSheet(f"color:{color}; font-size:9px; background:transparent;")
        dot.setFixedWidth(12)

        lbl = QLabel(label)
        lbl.setStyleSheet(f"color:{COLORS['text_muted']}; font-size:11px; background:transparent;")

        cnt = QLabel(str(count))
        cnt.setStyleSheet(f"color:{color}; font-size:11px; font-weight:700; background:transparent;")
        cnt.setAlignment(Qt.AlignRight)

        layout.addWidget(dot)
        layout.addWidget(lbl)
        layout.addStretch()
        layout.addWidget(cnt)


class Sidebar(QWidget):
    """Left navigation sidebar with live statistics."""

    page_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(226)
        self.setObjectName("sidebar")
        self.setStyleSheet(f"""
            QWidget#sidebar {{
                background-color: {COLORS['bg_secondary']};
                border-right: 1px solid {COLORS['border']};
            }}
        """)
        self._buttons: Dict[str, NavButton] = {}
        self._setup_ui()

        # Refresh counts every 30 s
        self._count_timer = QTimer(self)
        self._count_timer.timeout.connect(self.refresh_counts)
        self._count_timer.start(30_000)

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 16)
        root.setSpacing(0)

        # ── Brand ─────────────────────────────────────────────────────
        brand = QWidget()
        brand.setFixedHeight(70)
        brand.setStyleSheet(f"""
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                stop:0 {COLORS['bg_tertiary']}, stop:1 {COLORS['bg_secondary']});
            border-bottom: 1px solid {COLORS['border']};
        """)
        bl = QHBoxLayout(brand)
        bl.setContentsMargins(16, 0, 16, 0)
        bl.setSpacing(10)

        logo = QLabel("🎯")
        logo.setStyleSheet("font-size:26px; background:transparent;")

        brand_text = QVBoxLayout()
        brand_text.setSpacing(1)
        name_lbl = QLabel("AppTracker")
        name_lbl.setStyleSheet(f"""
            font-size:15px; font-weight:800;
            color:{COLORS['text_primary']}; background:transparent;
            letter-spacing: -0.3px;
        """)
        tag_lbl = QLabel("Job Hunt Manager")
        tag_lbl.setStyleSheet(f"font-size:10px; color:{COLORS['text_muted']}; background:transparent;")
        brand_text.addWidget(name_lbl)
        brand_text.addWidget(tag_lbl)

        bl.addWidget(logo)
        bl.addLayout(brand_text)
        bl.addStretch()
        root.addWidget(brand)
        root.addSpacing(10)

        # ── Nav section label ─────────────────────────────────────────
        nav_lbl = QLabel("MENU")
        nav_lbl.setStyleSheet(f"""
            font-size:10px; font-weight:700; color:{COLORS['text_muted']};
            letter-spacing:1.5px; background:transparent; padding-left:16px;
        """)
        root.addWidget(nav_lbl)
        root.addSpacing(4)

        # ── Nav buttons ───────────────────────────────────────────────
        for page_id, _, icon, label in NAV_ITEMS:
            btn = NavButton(icon, label, page_id)
            btn.clicked.connect(lambda checked=False, pid=page_id: self._on_nav(pid))
            self._buttons[page_id] = btn
            root.addWidget(btn)
            root.addSpacing(2)

        root.addSpacing(16)

        # ── Divider ───────────────────────────────────────────────────
        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet(f"color:{COLORS['border']};")
        div.setFixedHeight(1)
        root.addWidget(div)
        root.addSpacing(10)

        # ── Live status summary ───────────────────────────────────────
        summary_lbl = QLabel("STATUS OVERVIEW")
        summary_lbl.setStyleSheet(f"""
            font-size:10px; font-weight:700; color:{COLORS['text_muted']};
            letter-spacing:1.5px; background:transparent; padding-left:16px;
        """)
        root.addWidget(summary_lbl)
        root.addSpacing(4)

        self._status_container = QVBoxLayout()
        self._status_container.setSpacing(0)
        root.addLayout(self._status_container)

        root.addStretch()

        # ── Bottom divider ────────────────────────────────────────────
        div2 = QFrame()
        div2.setFrameShape(QFrame.HLine)
        div2.setStyleSheet(f"color:{COLORS['border']};")
        div2.setFixedHeight(1)
        root.addWidget(div2)
        root.addSpacing(10)

        # ── Status indicator ──────────────────────────────────────────
        self.status_lbl = QLabel("● Ready")
        self.status_lbl.setStyleSheet(f"""
            color:{COLORS['accent_green']}; font-size:11px;
            padding-left:16px; background:transparent;
        """)
        root.addWidget(self.status_lbl)

        self._on_nav("dashboard")
        self.refresh_counts()

    # ── Navigation ────────────────────────────────────────────────────

    def _on_nav(self, page_id: str):
        for pid, btn in self._buttons.items():
            btn.setChecked(pid == page_id)
        self.page_changed.emit(page_id)

    def navigate_to(self, page_id: str):
        self._on_nav(page_id)

    # ── Counts ────────────────────────────────────────────────────────

    def refresh_counts(self):
        """Pull live counts from DB and update sidebar badges + summary."""
        try:
            stats = db.get_dashboard_stats()
            by_status = stats["by_status"]
            total = stats["total"]

            # Badge on Applications nav item
            self._buttons["applications"].badge.set_count(
                total, COLORS["accent_blue"], "#1f4280"
            )

            # Status summary rows
            _clear_layout(self._status_container)
            show = [
                ("Applied",   COLORS["accent_blue"]),
                ("Interview", COLORS["accent_orange"]),
                ("Offer",     COLORS["accent_green"]),
                ("Rejected",  COLORS["accent_red"]),
            ]
            for status, color in show:
                cnt = by_status.get(status, 0)
                row = MiniStatRow(status, cnt, color)
                self._status_container.addWidget(row)

        except Exception:
            pass

    # ── Status bar ────────────────────────────────────────────────────

    def set_status(self, text: str, color: str = None):
        color = color or COLORS["accent_green"]
        self.status_lbl.setText("● {}".format(text))
        self.status_lbl.setStyleSheet(f"""
            color:{color}; font-size:11px;
            padding-left:16px; background:transparent;
        """)


def _clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
