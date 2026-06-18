"""
ui/analytics.py - Analytics / insights page
"""
from typing import List, Tuple

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QScrollArea, QProgressBar, QGridLayout,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QFont, QLinearGradient, QPen, QBrush

import database as db
from ui.styles import COLORS, STATUS_COLORS, PRIORITY_COLORS


class BarChart(QWidget):
    """Vertical bar chart drawn with QPainter."""

    def __init__(self, data: List[Tuple[str, int, str]], parent=None):
        super().__init__(parent)
        self._data = data  # [(label, value, color)]
        self._max = max((v for _, v, _ in data), default=1) or 1
        self.setMinimumHeight(160)

    def paintEvent(self, event):
        from PySide6.QtCore import QRectF
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height() - 30  # leave room for labels
        n = len(self._data)
        if n == 0:
            p.end()
            return

        bar_w = max(10, (w - 20) // n - 8)
        spacing = (w - 20 - bar_w * n) // (n + 1)

        for i, (label, value, color) in enumerate(self._data):
            x = 10 + spacing * (i + 1) + bar_w * i
            bar_h = int((value / self._max) * (h - 20))
            y = h - bar_h

            # Bar
            grad = QLinearGradient(x, y, x, y + bar_h)
            grad.setColorAt(0, QColor(color))
            grad.setColorAt(1, QColor(color + "88"))
            p.setBrush(QBrush(grad))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(x, y, bar_w, bar_h, 4, 4)

            # Value on top
            p.setPen(QColor(COLORS["text_primary"]))
            p.setFont(QFont("Segoe UI", 8, QFont.Bold))
            p.drawText(x, y - 4, bar_w, 16, Qt.AlignCenter, str(value))

            # Label below
            p.setPen(QColor(COLORS["text_muted"]))
            p.setFont(QFont("Segoe UI", 8))
            label_text = label[:8] if len(label) > 8 else label
            p.drawText(x - 4, h + 4, bar_w + 8, 20, Qt.AlignCenter, label_text)

        p.end()


class Analytics(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        root.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(22)

        # Header
        pg_title = QLabel("Analytics")
        pg_title.setStyleSheet(f"font-size:22px; font-weight:700; color:{COLORS['text_primary']};")
        pg_sub = QLabel("Deep insights into your job search")
        pg_sub.setStyleSheet(f"font-size:13px; color:{COLORS['text_secondary']};")
        layout.addWidget(pg_title)
        layout.addWidget(pg_sub)

        # ── Status chart ──────────────────────────────────────────────
        self._status_card = self._make_card("Applications by Status")
        self._status_chart_holder = QVBoxLayout()
        self._status_card.layout().addLayout(self._status_chart_holder)
        layout.addWidget(self._status_card)

        # ── Priority card ─────────────────────────────────────────────
        self._priority_card = self._make_card("Applications by Priority")
        self._priority_chart_holder = QVBoxLayout()
        self._priority_card.layout().addLayout(self._priority_chart_holder)
        layout.addWidget(self._priority_card)

        # ── Success rates ─────────────────────────────────────────────
        self._rates_card = self._make_card("Success Rate Funnel")
        self._rates_holder = QVBoxLayout()
        self._rates_card.layout().addLayout(self._rates_holder)
        layout.addWidget(self._rates_card)

        layout.addStretch()

    def _make_card(self, title: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
            }}
        """)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(18, 16, 18, 16)
        cl.setSpacing(12)
        lbl = QLabel(title)
        lbl.setStyleSheet(f"font-size:15px; font-weight:700; color:{COLORS['text_primary']};")
        cl.addWidget(lbl)
        return card

    def refresh(self):
        stats = db.get_dashboard_stats()
        total = stats["total"] or 1
        by_status = stats["by_status"]

        # ── Status chart ──────────────────────────────────────────────
        _clear_layout(self._status_chart_holder)
        status_data = [
            (s, by_status.get(s, 0), STATUS_COLORS.get(s, (COLORS["accent_blue"], ""))[0])
            for s in ["Applied", "Screening", "Interview", "Technical",
                      "Offer", "Accepted", "Rejected", "Withdrawn"]
        ]
        chart = BarChart(status_data)
        chart.setMinimumHeight(180)
        self._status_chart_holder.addWidget(chart)

        # Progress bars for status
        for s, cnt, color in status_data:
            row = QHBoxLayout()
            lbl = QLabel(s)
            lbl.setFixedWidth(90)
            lbl.setStyleSheet(f"color:{COLORS['text_secondary']}; font-size:12px;")
            pb = QProgressBar()
            pb.setRange(0, total)
            pb.setValue(cnt)
            pb.setStyleSheet(f"""
                QProgressBar {{
                    background: {COLORS['bg_card']}; border: 1px solid {COLORS['border']};
                    border-radius: 4px; height: 8px;
                }}
                QProgressBar::chunk {{
                    background: {color}; border-radius: 4px;
                }}
            """)
            cnt_lbl = QLabel(str(cnt))
            cnt_lbl.setFixedWidth(30)
            cnt_lbl.setAlignment(Qt.AlignRight)
            cnt_lbl.setStyleSheet(f"color:{COLORS['text_primary']}; font-weight:600; font-size:12px;")
            row.addWidget(lbl)
            row.addWidget(pb, 1)
            row.addWidget(cnt_lbl)
            self._status_chart_holder.addLayout(row)

        # ── Priority chart ────────────────────────────────────────────
        _clear_layout(self._priority_chart_holder)
        conn_rows = db.get_all_applications()
        by_priority = {}
        for row in conn_rows:
            p = row["priority"]
            by_priority[p] = by_priority.get(p, 0) + 1

        for pri, (color, _) in PRIORITY_COLORS.items():
            cnt = by_priority.get(pri, 0)
            row_w = QHBoxLayout()
            lbl = QLabel(pri)
            lbl.setFixedWidth(70)
            lbl.setStyleSheet(f"color:{color}; font-size:12px; font-weight:600;")
            pb = QProgressBar()
            pb.setRange(0, max(by_priority.values(), default=1))
            pb.setValue(cnt)
            pb.setStyleSheet(f"""
                QProgressBar {{
                    background: {COLORS['bg_card']}; border: 1px solid {COLORS['border']};
                    border-radius: 4px; height: 8px;
                }}
                QProgressBar::chunk {{ background: {color}; border-radius: 4px; }}
            """)
            cnt_lbl = QLabel(str(cnt))
            cnt_lbl.setFixedWidth(30)
            cnt_lbl.setAlignment(Qt.AlignRight)
            cnt_lbl.setStyleSheet(f"color:{COLORS['text_primary']}; font-weight:600; font-size:12px;")
            row_w.addWidget(lbl)
            row_w.addWidget(pb, 1)
            row_w.addWidget(cnt_lbl)
            self._priority_chart_holder.addLayout(row_w)

        # ── Funnel ────────────────────────────────────────────────────
        _clear_layout(self._rates_holder)
        funnel = [
            ("Applied",    by_status.get("Applied", 0),   COLORS["accent_blue"]),
            ("Screening",  by_status.get("Screening", 0), COLORS["accent_purple"]),
            ("Interview",  by_status.get("Interview", 0), COLORS["accent_orange"]),
            ("Offer",      by_status.get("Offer", 0),     COLORS["accent_green"]),
            ("Accepted",   by_status.get("Accepted", 0),  COLORS["accent_teal"]),
        ]
        base = max((v for _, v, _ in funnel), default=1) or 1
        for stage, cnt, color in funnel:
            pct = int(cnt / base * 100) if base else 0
            row_w = QHBoxLayout()
            lbl = QLabel(stage)
            lbl.setFixedWidth(90)
            lbl.setStyleSheet(f"color:{COLORS['text_secondary']}; font-size:12px;")
            pb = QProgressBar()
            pb.setRange(0, 100)
            pb.setValue(pct)
            pb.setFormat(f"{cnt}  ({pct}%)")
            pb.setTextVisible(True)
            pb.setStyleSheet(f"""
                QProgressBar {{
                    background: {COLORS['bg_card']}; border: 1px solid {COLORS['border']};
                    border-radius: 6px; height: 22px; color: {COLORS['text_primary']}; font-size:11px;
                }}
                QProgressBar::chunk {{ background: {color}; border-radius: 6px; }}
            """)
            row_w.addWidget(lbl)
            row_w.addWidget(pb, 1)
            self._rates_holder.addLayout(row_w)


def _clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            _clear_layout(item.layout())
