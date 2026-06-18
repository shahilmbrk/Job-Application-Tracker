"""
ui/dashboard.py - Dashboard page for Application Tracker
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QFrame, QSizePolicy, QPushButton,
    QGridLayout,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

import database as db
from ui.styles import COLORS, STATUS_COLORS
from ui.widgets import StatCard, ActivityItem, EmptyState, SectionHeader, HDivider, Badge


class RecentAppRow(QFrame):
    """A single row in the Recent Applications mini-table."""

    clicked = Signal(int)

    def __init__(self, row, parent=None):
        super().__init__(parent)
        self._app_id = row["id"]
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("recentRow")
        self.setStyleSheet(f"""
            QFrame#recentRow {{
                background: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
            QFrame#recentRow:hover {{
                background: {COLORS['bg_hover']};
                border-color: {COLORS['accent_blue']}66;
            }}
        """)
        self.setFixedHeight(56)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(12)

        # Company avatar circle
        initial = (row["company"] or "?")[0].upper()
        avatar = QLabel(initial)
        avatar.setFixedSize(36, 36)
        avatar.setAlignment(Qt.AlignCenter)
        color = STATUS_COLORS.get(row["status"], (COLORS["accent_blue"], "#1f4280"))[0]
        avatar.setStyleSheet(f"""
            background: {color}22; border: 1px solid {color}55;
            border-radius: 18px; font-weight: 700; font-size: 14px; color: {color};
        """)
        layout.addWidget(avatar)

        # Company + Position
        info_col = QVBoxLayout()
        info_col.setSpacing(1)
        co = QLabel(row["company"] or "")
        co.setStyleSheet(f"font-weight: 600; font-size: 13px; color: {COLORS['text_primary']}; background:transparent;")
        pos = QLabel(row["position"] or "")
        pos.setStyleSheet(f"font-size: 11px; color: {COLORS['text_secondary']}; background:transparent;")
        info_col.addWidget(co)
        info_col.addWidget(pos)
        layout.addLayout(info_col)
        layout.addStretch()

        # Location
        if row["location"]:
            loc = QLabel(f"📍 {row['location']}")
            loc.setStyleSheet(f"font-size: 11px; color: {COLORS['text_muted']}; background:transparent;")
            layout.addWidget(loc)

        # Status badge
        badge = Badge.for_status(row["status"])
        layout.addWidget(badge)

        # Applied date
        if row["applied_date"]:
            date_lbl = QLabel(row["applied_date"][:10])
            date_lbl.setStyleSheet(f"font-size: 11px; color: {COLORS['text_muted']}; background:transparent; min-width:70px;")
            date_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            layout.addWidget(date_lbl)

    def mousePressEvent(self, event):
        self.clicked.emit(self._app_id)
        super().mousePressEvent(event)


class MiniDonutChart(QWidget):
    """Simple SVG-style donut chart drawn with QPainter."""

    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self.setFixedSize(160, 160)
        self._data = data  # {label: (count, color)}
        self._total = sum(v[0] for v in data.values()) or 1

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QPen, QBrush, QColor
        from PySide6.QtCore import QRectF
        import math

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(20, 20, 120, 120)
        start = -90 * 16   # start from top, Qt uses 1/16 degrees

        for label, (count, color) in self._data.items():
            span = int(count / self._total * 360 * 16)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(color))
            p.drawPie(rect, start, span)
            start += span

        # Hollow centre
        p.setBrush(QColor(COLORS["bg_secondary"]))
        p.setPen(Qt.NoPen)
        inner_rect = QRectF(48, 48, 64, 64)
        p.drawEllipse(inner_rect)

        # Total text
        p.setPen(QColor(COLORS["text_primary"]))
        font = QFont("Segoe UI", 14, QFont.Bold)
        p.setFont(font)
        p.drawText(rect, Qt.AlignCenter, str(self._total))

        p.end()


class Dashboard(QWidget):
    """Main dashboard page."""

    open_application = Signal(int)
    navigate_to = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        root.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(22)

        # ── Page Header ───────────────────────────────────────────────
        header_row = QHBoxLayout()
        header_col = QVBoxLayout()
        header_col.setSpacing(2)
        pg_title = QLabel("Dashboard")
        pg_title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {COLORS['text_primary']};")
        pg_sub = QLabel("Track your job search progress at a glance")
        pg_sub.setStyleSheet(f"font-size: 13px; color: {COLORS['text_secondary']};")
        header_col.addWidget(pg_title)
        header_col.addWidget(pg_sub)
        header_row.addLayout(header_col)
        header_row.addStretch()

        add_btn = QPushButton("  ➕  Add Application")
        add_btn.setObjectName("primaryBtn")
        add_btn.setFixedHeight(38)
        add_btn.setMinimumWidth(160)
        add_btn.clicked.connect(lambda: self.navigate_to.emit("add"))
        header_row.addWidget(add_btn)
        layout.addLayout(header_row)

        # ── Stat Cards ────────────────────────────────────────────────
        self._stat_cards_layout = QGridLayout()
        self._stat_cards_layout.setSpacing(14)

        self._cards: dict[str, StatCard] = {}
        card_defs = [
            ("total",      "Total",       "0", "📁", COLORS["accent_blue"]),
            ("applied",    "Applied",     "0", "📨", "#58a6ff"),
            ("interview",  "Interviews",  "0", "🎤", COLORS["accent_orange"]),
            ("offer",      "Offers",      "0", "🎉", COLORS["accent_green"]),
            ("rejected",   "Rejected",    "0", "❌", COLORS["accent_red"]),
            ("pending",    "In Progress", "0", "⏳", COLORS["accent_purple"]),
        ]
        for i, (key, title, val, icon, color) in enumerate(card_defs):
            card = StatCard(title, val, icon, color)
            self._cards[key] = card
            self._stat_cards_layout.addWidget(card, i // 3, i % 3)

        layout.addLayout(self._stat_cards_layout)

        # ── Middle row: Recent + Chart ─────────────────────────────────
        mid_row = QHBoxLayout()
        mid_row.setSpacing(18)

        # Recent Applications
        recent_card = QFrame()
        recent_card.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
            }}
        """)
        recent_layout = QVBoxLayout(recent_card)
        recent_layout.setContentsMargins(18, 16, 18, 16)
        recent_layout.setSpacing(10)

        rec_header = QHBoxLayout()
        rec_title = QLabel("Recent Applications")
        rec_title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {COLORS['text_primary']};")
        view_all = QPushButton("View all →")
        view_all.setObjectName("iconBtn")
        view_all.clicked.connect(lambda: self.navigate_to.emit("applications"))
        rec_header.addWidget(rec_title)
        rec_header.addStretch()
        rec_header.addWidget(view_all)
        recent_layout.addLayout(rec_header)

        self._recent_list = QVBoxLayout()
        self._recent_list.setSpacing(6)
        recent_layout.addLayout(self._recent_list)

        mid_row.addWidget(recent_card, 2)

        # Status breakdown card
        status_card = QFrame()
        status_card.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
            }}
        """)
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(18, 16, 18, 16)
        status_layout.setSpacing(10)

        sc_title = QLabel("Status Breakdown")
        sc_title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {COLORS['text_primary']};")
        status_layout.addWidget(sc_title)

        self._chart_container = QVBoxLayout()
        self._chart_container.setAlignment(Qt.AlignHCenter)
        status_layout.addLayout(self._chart_container)

        self._legend_layout = QVBoxLayout()
        self._legend_layout.setSpacing(4)
        status_layout.addLayout(self._legend_layout)
        status_layout.addStretch()

        mid_row.addWidget(status_card, 1)
        layout.addLayout(mid_row)

        # ── Activity Feed ─────────────────────────────────────────────
        activity_card = QFrame()
        activity_card.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
            }}
        """)
        act_layout = QVBoxLayout(activity_card)
        act_layout.setContentsMargins(18, 16, 18, 16)
        act_layout.setSpacing(10)

        act_title = QLabel("Recent Activity")
        act_title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {COLORS['text_primary']};")
        act_layout.addWidget(act_title)

        self._activity_layout = QVBoxLayout()
        self._activity_layout.setSpacing(6)
        act_layout.addLayout(self._activity_layout)

        layout.addWidget(activity_card)
        layout.addStretch()

    def refresh(self):
        """Reload all dashboard data from DB."""
        stats = db.get_dashboard_stats()
        total = stats["total"]
        by_status = stats["by_status"]

        # ── Stat cards ────────────────────────────────────────────────
        in_progress = sum(
            by_status.get(s, 0)
            for s in ["Screening", "Interview", "Technical"]
        )
        self._cards["total"].set_value(str(total))
        self._cards["applied"].set_value(str(by_status.get("Applied", 0)))
        self._cards["interview"].set_value(str(by_status.get("Interview", 0) + by_status.get("Technical", 0)))
        self._cards["offer"].set_value(str(by_status.get("Offer", 0) + by_status.get("Accepted", 0)))
        self._cards["rejected"].set_value(str(by_status.get("Rejected", 0)))
        self._cards["pending"].set_value(str(in_progress))

        # ── Recent list ───────────────────────────────────────────────
        _clear_layout(self._recent_list)
        recent = stats["recent"]
        if recent:
            for row in recent:
                item = RecentAppRow(row)
                item.clicked.connect(self.open_application.emit)
                self._recent_list.addWidget(item)
        else:
            empty = EmptyState("🔍", "No applications yet", "Add your first job application!")
            self._recent_list.addWidget(empty)

        # ── Chart & legend ────────────────────────────────────────────
        _clear_layout(self._chart_container)
        _clear_layout(self._legend_layout)

        from ui.styles import STATUS_COLORS
        chart_data = {}
        for status, count in by_status.items():
            color = STATUS_COLORS.get(status, (COLORS["text_muted"], ""))[0]
            chart_data[status] = (count, color)

        if chart_data:
            chart = MiniDonutChart(chart_data)
            self._chart_container.addWidget(chart)
            for status, (count, color) in chart_data.items():
                row_w = QHBoxLayout()
                dot = QLabel("●")
                dot.setStyleSheet(f"color:{color}; font-size:11px; background:transparent;")
                lbl = QLabel(status)
                lbl.setStyleSheet(f"color:{COLORS['text_secondary']}; font-size:12px; background:transparent;")
                cnt = QLabel(str(count))
                cnt.setStyleSheet(f"color:{COLORS['text_primary']}; font-size:12px; font-weight:600; background:transparent;")
                row_w.addWidget(dot)
                row_w.addWidget(lbl)
                row_w.addStretch()
                row_w.addWidget(cnt)
                self._legend_layout.addLayout(row_w)

        # ── Activity ──────────────────────────────────────────────────
        _clear_layout(self._activity_layout)
        activities = db.get_recent_activity(8)
        if activities:
            for a in activities:
                item = ActivityItem(
                    a["action"],
                    a["description"],
                    a["company"] or "—",
                    a["timestamp"],
                )
                self._activity_layout.addWidget(item)
        else:
            lbl = QLabel("No recent activity")
            lbl.setStyleSheet(f"color:{COLORS['text_muted']}; font-size:13px; text-align:center;")
            lbl.setAlignment(Qt.AlignCenter)
            self._activity_layout.addWidget(lbl)


def _clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            _clear_layout(item.layout())
