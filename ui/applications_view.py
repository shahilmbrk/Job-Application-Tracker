"""
ui/applications_view.py - Applications table: search, filter, sort, CRUD, quick-status
"""

import os
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QAbstractItemView, QHeaderView, QFrame, QMenu, QMessageBox,
    QToolButton, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor, QFont, QAction

import database as db
from ui.styles import COLORS, STATUS_COLORS, PRIORITY_COLORS
from ui.widgets import EmptyState

STATUSES_FILTER  = ["All", "Applied", "Screening", "Interview", "Technical",
                    "Offer", "Accepted", "Rejected", "Withdrawn", "Ghosted"]
PRIORITIES_FILTER = ["All", "High", "Medium", "Low"]

ALL_STATUSES = ["Applied", "Screening", "Interview", "Technical",
                "Offer", "Accepted", "Rejected", "Withdrawn", "Ghosted"]

COLUMNS = [
    ("Company",  "company",      170),
    ("Position", "position",     210),
    ("Location", "location",     120),
    ("Status",   "status",       115),
    ("Priority", "priority",     90),
    ("Applied",  "applied_date", 95),
    ("Source",   "source",       95),
    ("Updated",  "updated_at",   130),
]


class ChipFilter(QWidget):
    """Horizontal row of clickable status filter chips."""

    filter_changed = Signal(str)   # emits selected status or "All"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active = "All"
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self._btns = {}

        chips = [("All", COLORS["text_secondary"], COLORS["bg_card"])] + [
            (s, STATUS_COLORS[s][0], STATUS_COLORS[s][1])
            for s in ALL_STATUSES
        ]
        for status, fg, bg in chips:
            btn = QPushButton(status)
            btn.setCheckable(True)
            btn.setFixedHeight(26)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background:{bg}; color:{fg};
                    border:1px solid {fg}44; border-radius:13px;
                    padding:0 10px; font-size:11px; font-weight:600;
                }}
                QPushButton:checked {{
                    background:{fg}; color:#ffffff;
                    border:1px solid {fg};
                }}
                QPushButton:hover:!checked {{
                    background:{fg}22;
                }}
            """)
            btn.clicked.connect(
                lambda checked=False, s=status: self._on_click(s)
            )
            self._btns[status] = btn
            layout.addWidget(btn)

        layout.addStretch()
        self._btns["All"].setChecked(True)

    def _on_click(self, status: str):
        self._active = status
        for s, btn in self._btns.items():
            btn.setChecked(s == status)
        self.filter_changed.emit(status)

    def reset(self):
        self._on_click("All")

    @property
    def current(self) -> str:
        return self._active


class ApplicationsView(QWidget):
    """Applications list / table page with full search, filter, sort, CRUD."""

    open_dialog  = Signal(object)   # None = add, int = edit id
    row_selected = Signal(int)
    data_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sort_col = "updated_at"
        self._sort_dir = "DESC"
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._apply_filters)
        self._build_ui()

    # ── Build ─────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 16)
        root.setSpacing(14)

        # ── Page header ───────────────────────────────────────────────
        hdr = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(2)

        pg_title = QLabel("Applications")
        pg_title.setStyleSheet(
            f"font-size:22px; font-weight:700; color:{COLORS['text_primary']};"
        )
        self._count_lbl = QLabel("Loading…")
        self._count_lbl.setStyleSheet(
            f"font-size:12px; color:{COLORS['text_secondary']};"
        )
        title_col.addWidget(pg_title)
        title_col.addWidget(self._count_lbl)
        hdr.addLayout(title_col)
        hdr.addStretch()

        add_btn = QPushButton("  ➕  Add Application")
        add_btn.setObjectName("primaryBtn")
        add_btn.setFixedHeight(38)
        add_btn.setMinimumWidth(160)
        add_btn.clicked.connect(lambda: self.open_dialog.emit(None))
        hdr.addWidget(add_btn)
        root.addLayout(hdr)

        # ── Search toolbar ────────────────────────────────────────────
        toolbar = QFrame()
        toolbar.setStyleSheet(f"""
            QFrame {{
                background:{COLORS['bg_secondary']};
                border:1px solid {COLORS['border']};
                border-radius:10px;
            }}
        """)
        tb = QHBoxLayout(toolbar)
        tb.setContentsMargins(14, 10, 14, 10)
        tb.setSpacing(10)

        # Search box
        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍  Search company, position, location, tags…")
        self._search.setFixedHeight(36)
        self._search.textChanged.connect(lambda: self._search_timer.start(280))
        tb.addWidget(self._search, 3)

        # Priority filter
        self._priority_filter = QComboBox()
        self._priority_filter.addItems(PRIORITIES_FILTER)
        self._priority_filter.setFixedHeight(36)
        self._priority_filter.setFixedWidth(110)
        self._priority_filter.currentTextChanged.connect(self._apply_filters)
        tb.addWidget(self._priority_filter)

        # Clear
        clear_btn = QPushButton("✕  Clear")
        clear_btn.setObjectName("iconBtn")
        clear_btn.setFixedHeight(36)
        clear_btn.clicked.connect(self._clear_filters)
        tb.addWidget(clear_btn)

        root.addWidget(toolbar)

        # ── Status chip filters ───────────────────────────────────────
        chip_scroll_inner = QWidget()
        chip_layout = QHBoxLayout(chip_scroll_inner)
        chip_layout.setContentsMargins(0, 0, 0, 0)
        self._chip_filter = ChipFilter()
        self._chip_filter.filter_changed.connect(self._apply_filters)
        chip_layout.addWidget(self._chip_filter)
        root.addWidget(chip_scroll_inner)

        # ── Table ─────────────────────────────────────────────────────
        self._table = QTableWidget()
        self._table.setObjectName("appTable")
        self._table.setColumnCount(len(COLUMNS))
        self._table.setHorizontalHeaderLabels([c[0] for c in COLUMNS])
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        self._table.setFocusPolicy(Qt.ClickFocus)
        self._table.setSortingEnabled(False)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._context_menu)
        self._table.cellDoubleClicked.connect(self._on_double_click)
        self._table.itemSelectionChanged.connect(self._on_selection)

        hdr_view = self._table.horizontalHeader()
        for i, (_, _, w) in enumerate(COLUMNS):
            self._table.setColumnWidth(i, w)
        hdr_view.setSectionResizeMode(1, QHeaderView.Stretch)
        hdr_view.sectionClicked.connect(self._on_header_click)
        hdr_view.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        hdr_view.setHighlightSections(False)
        self._table.verticalHeader().setDefaultSectionSize(52)

        root.addWidget(self._table, 1)

        # ── Bottom action bar ─────────────────────────────────────────
        action_bar = QHBoxLayout()
        action_bar.setSpacing(8)

        self._edit_btn = QPushButton("  ✏️  Edit")
        self._edit_btn.setFixedHeight(34)
        self._edit_btn.setEnabled(False)
        self._edit_btn.clicked.connect(self._edit_selected)

        self._del_btn = QPushButton("  🗑  Delete")
        self._del_btn.setObjectName("dangerBtn")
        self._del_btn.setFixedHeight(34)
        self._del_btn.setEnabled(False)
        self._del_btn.clicked.connect(self._delete_selected)

        # Quick status change
        self._status_quick = QComboBox()
        self._status_quick.addItem("⚡ Change Status…")
        self._status_quick.addItems(ALL_STATUSES)
        self._status_quick.setFixedHeight(34)
        self._status_quick.setFixedWidth(175)
        self._status_quick.setEnabled(False)
        self._status_quick.currentIndexChanged.connect(self._quick_status_change)

        action_bar.addWidget(self._edit_btn)
        action_bar.addWidget(self._del_btn)
        action_bar.addSpacing(10)
        action_bar.addWidget(self._status_quick)
        action_bar.addStretch()

        # Row count hint
        self._sel_hint = QLabel("")
        self._sel_hint.setStyleSheet(
            f"color:{COLORS['text_muted']}; font-size:11px;"
        )
        action_bar.addWidget(self._sel_hint)
        root.addLayout(action_bar)

    # ── Data ──────────────────────────────────────────────────────────

    def refresh(self):
        self._apply_filters()

    def _apply_filters(self, *_):
        search   = self._search.text().strip()
        status   = self._chip_filter.current
        priority = self._priority_filter.currentText()
        rows = db.get_all_applications(search, status, priority,
                                       self._sort_col, self._sort_dir)
        self._populate(rows)

    def _clear_filters(self):
        self._search.clear()
        self._priority_filter.setCurrentIndex(0)
        self._chip_filter.reset()

    def _populate(self, rows: list):
        self._table.setRowCount(0)
        n = len(rows)
        self._count_lbl.setText(
            "{} application{}".format(n, "s" if n != 1 else "")
        )

        for row in rows:
            r = self._table.rowCount()
            self._table.insertRow(r)
            self._table.setRowHeight(r, 52)

            vals = [
                row["company"] or "",
                row["position"] or "",
                row["location"] or "—",
                row["status"] or "",
                row["priority"] or "",
                (row["applied_date"] or "")[:10],
                row["source"] or "—",
                (row["updated_at"] or "")[:16],
            ]
            for col_idx, val in enumerate(vals):
                item = QTableWidgetItem(val)
                item.setData(Qt.UserRole, row["id"])
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)

                if col_idx == 3:   # Status — coloured + bold
                    fg, _ = STATUS_COLORS.get(val, (COLORS["text_secondary"], ""))
                    item.setForeground(QColor(fg))
                    f = item.font(); f.setBold(True); item.setFont(f)
                elif col_idx == 4: # Priority — coloured
                    fg, _ = PRIORITY_COLORS.get(val, (COLORS["text_secondary"], ""))
                    item.setForeground(QColor(fg))
                elif col_idx == 0: # Company — slightly bolder
                    f = item.font(); f.setWeight(QFont.DemiBold); item.setFont(f)

                self._table.setItem(r, col_idx, item)

        self._edit_btn.setEnabled(False)
        self._del_btn.setEnabled(False)
        self._status_quick.setEnabled(False)
        self._status_quick.setCurrentIndex(0)
        self._sel_hint.setText("")

    # ── Interaction ───────────────────────────────────────────────────

    def _selected_id(self) -> Optional[int]:
        row = self._table.currentRow()
        if row < 0:
            return None
        item = self._table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _on_selection(self):
        app_id = self._selected_id()
        has = app_id is not None
        self._edit_btn.setEnabled(has)
        self._del_btn.setEnabled(has)
        self._status_quick.setEnabled(has)
        self._status_quick.setCurrentIndex(0)
        if has:
            self.row_selected.emit(app_id)
            # Show current status as hint
            row = db.get_application(app_id)
            if row:
                self._sel_hint.setText(
                    "Selected: {}  @ {}".format(row["position"], row["company"])
                )

    def _on_double_click(self, row: int, col: int):
        item = self._table.item(row, 0)
        if item:
            self.open_dialog.emit(item.data(Qt.UserRole))

    def _edit_selected(self):
        app_id = self._selected_id()
        if app_id:
            self.open_dialog.emit(app_id)

    def _delete_selected(self):
        app_id = self._selected_id()
        if not app_id:
            return
        app = db.get_application(app_id)
        if not app:
            return
        confirm = QMessageBox.question(
            self, "Delete Application",
            "Permanently delete the application at "
            "<b>{}</b> for <b>{}</b>?<br>"
            "All attachments and history will be removed.".format(
                app["company"], app["position"]
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            db.delete_application(app_id)
            self.data_changed.emit()
            self.refresh()

    def _quick_status_change(self, idx: int):
        if idx <= 0:
            return
        app_id = self._selected_id()
        if not app_id:
            self._status_quick.setCurrentIndex(0)
            return
        new_status = self._status_quick.itemText(idx)
        db.update_application(app_id, {"status": new_status})
        self.data_changed.emit()
        self.refresh()
        self._status_quick.setCurrentIndex(0)

    def _context_menu(self, pos):
        app_id = self._selected_id()
        if not app_id:
            return

        menu = QMenu(self)
        edit_act = menu.addAction("✏️  Edit")
        menu.addSeparator()

        status_menu = menu.addMenu("🔄  Change Status")
        for s in ALL_STATUSES:
            fg, _ = STATUS_COLORS.get(s, (COLORS["text_primary"], ""))
            act = status_menu.addAction(s)
            act.triggered.connect(
                lambda checked=False, st=s: self._change_status(app_id, st)
            )

        menu.addSeparator()
        del_act = menu.addAction("🗑  Delete")

        action = menu.exec(self._table.viewport().mapToGlobal(pos))
        if action == edit_act:
            self.open_dialog.emit(app_id)
        elif action == del_act:
            self._delete_selected()

    def _change_status(self, app_id: int, status: str):
        db.update_application(app_id, {"status": status})
        self.data_changed.emit()
        self.refresh()

    def _on_header_click(self, logical_idx: int):
        col_key = COLUMNS[logical_idx][1]
        if self._sort_col == col_key:
            self._sort_dir = "ASC" if self._sort_dir == "DESC" else "DESC"
        else:
            self._sort_col = col_key
            self._sort_dir = "DESC"
        self._apply_filters()
