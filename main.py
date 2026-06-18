"""
main.py - Application Tracker entry point and main window
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout,
    QVBoxLayout, QStackedWidget, QLabel, QFrame,
    QGraphicsOpacityEffect,
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QColor

import database as db
from ui.styles import APP_STYLESHEET, COLORS
from ui.sidebar import Sidebar
from ui.dashboard import Dashboard
from ui.applications_view import ApplicationsView
from ui.application_dialog import ApplicationDialog
from ui.analytics import Analytics


# ──────────────────────────────────────────────────────────────────────────────
# Toast notification
# ──────────────────────────────────────────────────────────────────────────────

class Toast(QLabel):
    """Transient notification that fades in then out."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(38)
        self.setMinimumWidth(260)
        self.setStyleSheet(f"""
            QLabel {{
                background: {COLORS['bg_card']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                font-size: 13px;
                font-weight: 500;
                padding: 0 18px;
            }}
        """)
        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(0)
        self.setGraphicsEffect(self._effect)
        self.hide()

    def show_message(self, text: str, color: str = None):
        color = color or COLORS["accent_green"]
        self.setText("  {}  {}".format(
            "✓" if color == COLORS["accent_green"] else "✕", text
        ))
        self.setStyleSheet(f"""
            QLabel {{
                background:{COLORS['bg_card']};
                color:{color};
                border:1px solid {color}44;
                border-radius:8px;
                font-size:13px; font-weight:600;
                padding:0 18px;
            }}
        """)
        self.adjustSize()
        self._reposition()
        self.show()
        self.raise_()

        # Fade in
        self._anim_in = QPropertyAnimation(self._effect, b"opacity")
        self._anim_in.setDuration(200)
        self._anim_in.setStartValue(0.0)
        self._anim_in.setEndValue(1.0)
        self._anim_in.start()

        # Schedule fade out
        QTimer.singleShot(2200, self._fade_out)

    def _fade_out(self):
        self._anim_out = QPropertyAnimation(self._effect, b"opacity")
        self._anim_out.setDuration(400)
        self._anim_out.setStartValue(1.0)
        self._anim_out.setEndValue(0.0)
        self._anim_out.finished.connect(self.hide)
        self._anim_out.start()

    def _reposition(self):
        if self.parent():
            pw = self.parent().width()
            ph = self.parent().height()
            self.move((pw - self.width()) // 2, ph - 70)

    def resizeEvent(self, event):
        self._reposition()
        super().resizeEvent(event)


# ──────────────────────────────────────────────────────────────────────────────
# Title bar
# ──────────────────────────────────────────────────────────────────────────────

class TitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(48)
        self.setObjectName("titleBar")
        self.setStyleSheet(f"""
            QWidget#titleBar {{
                background:{COLORS['bg_secondary']};
                border-bottom:1px solid {COLORS['border']};
            }}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(22, 0, 22, 0)
        layout.setSpacing(0)

        self._page_lbl = QLabel("Dashboard")
        self._page_lbl.setStyleSheet(f"""
            font-size:14px; font-weight:600;
            color:{COLORS['text_primary']}; background:transparent;
        """)
        layout.addWidget(self._page_lbl)
        layout.addStretch()

        self._clock = QLabel()
        self._clock.setStyleSheet(
            f"color:{COLORS['text_muted']}; font-size:12px; background:transparent;"
        )
        layout.addWidget(self._clock)
        self._update_clock()
        t = QTimer(self)
        t.timeout.connect(self._update_clock)
        t.start(60_000)

    def _update_clock(self):
        from datetime import datetime
        self._clock.setText(datetime.now().strftime("%a, %b %d  %H:%M"))

    def set_page(self, name: str):
        self._page_lbl.setText(name)


# ──────────────────────────────────────────────────────────────────────────────
# Main window
# ──────────────────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Application Tracker")
        self.setMinimumSize(1100, 680)
        self.resize(1300, 800)
        self.setStyleSheet(APP_STYLESHEET)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sidebar ───────────────────────────────────────────────────
        self._sidebar = Sidebar()
        self._sidebar.page_changed.connect(self._navigate)
        root.addWidget(self._sidebar)

        # ── Right pane ────────────────────────────────────────────────
        right = QWidget()
        right.setObjectName("rightPane")
        right.setStyleSheet(f"QWidget#rightPane {{ background:{COLORS['bg_primary']}; }}")
        right_v = QVBoxLayout(right)
        right_v.setContentsMargins(0, 0, 0, 0)
        right_v.setSpacing(0)
        root.addWidget(right, 1)

        self._title_bar = TitleBar()
        right_v.addWidget(self._title_bar)

        self._stack = QStackedWidget()
        right_v.addWidget(self._stack, 1)

        # ── Pages ─────────────────────────────────────────────────────
        self._dashboard = Dashboard()
        self._dashboard.navigate_to.connect(self._sidebar.navigate_to)
        self._dashboard.open_application.connect(self._open_edit_dialog)

        self._app_view = ApplicationsView()
        self._app_view.open_dialog.connect(self._open_dialog_for)
        self._app_view.data_changed.connect(self._on_data_changed)

        self._analytics = Analytics()

        self._stack.addWidget(self._dashboard)   # 0
        self._stack.addWidget(self._app_view)    # 1
        self._stack.addWidget(self._analytics)   # 2

        self._page_map = {
            "dashboard":    (0, "Dashboard"),
            "applications": (1, "Applications"),
            "analytics":    (2, "Analytics"),
        }

        # ── Status bar ────────────────────────────────────────────────
        sb = self.statusBar()
        sb.setStyleSheet(f"""
            QStatusBar {{
                background:{COLORS['bg_secondary']};
                border-top:1px solid {COLORS['border']};
                color:{COLORS['text_muted']};
                font-size:11px;
                padding:2px 12px;
            }}
        """)
        sb.showMessage("  Ready")

        # ── Toast overlay (lives on the central widget) ───────────────
        self._toast = Toast(central)
        self._toast.hide()

        # ── Initial load ──────────────────────────────────────────────
        self._navigate("dashboard")

    # ── Navigation ────────────────────────────────────────────────────

    def _navigate(self, page_id: str):
        if page_id == "add":
            self._open_dialog_for(None)
            return

        idx, title = self._page_map.get(page_id, (0, "Dashboard"))
        self._stack.setCurrentIndex(idx)
        self._title_bar.set_page(title)

        if page_id == "dashboard":
            self._dashboard.refresh()
        elif page_id == "applications":
            self._app_view.refresh()
        elif page_id == "analytics":
            self._analytics.refresh()

    # ── Dialog dispatch ───────────────────────────────────────────────

    def _open_dialog_for(self, app_id):
        dlg = ApplicationDialog(app_id, self)
        result = dlg.exec()

        if result == QDialog_Accepted():
            self._on_data_changed()
            if app_id is None:
                self._toast.show_message("Application saved successfully")
                self._sidebar.navigate_to("applications")
            else:
                self._toast.show_message("Application updated")
        elif result == 2:   # deleted from within dialog
            self._on_data_changed()
            self._toast.show_message("Application deleted", COLORS["accent_red"])
            self._sidebar.navigate_to("applications")

    def _open_edit_dialog(self, app_id: int):
        self._open_dialog_for(app_id)

    def _on_data_changed(self):
        """Refresh the visible page, sidebar counts, and status bar."""
        idx = self._stack.currentIndex()
        if idx == 0:
            self._dashboard.refresh()
        elif idx == 1:
            self._app_view.refresh()
        elif idx == 2:
            self._analytics.refresh()

        self._sidebar.refresh_counts()

        total = db.get_dashboard_stats()["total"]
        self.statusBar().showMessage(
            "  {} application{} tracked".format(total, "s" if total != 1 else "")
        )

    # ── Window resize — reposition toast ──────────────────────────────
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._toast._reposition()


def QDialog_Accepted():
    from PySide6.QtWidgets import QDialog
    return QDialog.Accepted


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("Application Tracker")
    app.setOrganizationName("AppTracker")
    app.setApplicationVersion("1.1.0")
    app.setFont(QFont("Segoe UI", 10))

    db.init_db()

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
