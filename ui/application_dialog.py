"""
ui/application_dialog.py - Add / Edit application modal with file open support
"""

import os
import subprocess
import sys
from typing import List

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QLineEdit, QTextEdit, QComboBox, QPushButton,
    QDateEdit, QDoubleSpinBox, QScrollArea, QFrame,
    QFileDialog, QListWidget, QListWidgetItem, QWidget,
    QTabWidget, QMessageBox, QSizePolicy,
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QColor

import database as db
from ui.styles import COLORS, STATUS_COLORS, PRIORITY_COLORS

STATUSES   = ["Applied", "Screening", "Interview", "Technical",
               "Offer", "Accepted", "Rejected", "Withdrawn", "Ghosted"]
PRIORITIES = ["High", "Medium", "Low"]
SOURCES    = ["LinkedIn", "Indeed", "Company Website", "Referral",
               "Glassdoor", "AngelList", "Handshake", "Other"]


def _open_file(path: str):
    """Open a file with the system default application (cross-platform)."""
    if not os.path.exists(path):
        QMessageBox.warning(None, "File Not Found",
                            "The file could not be found:\n{}".format(path))
        return
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def _section(title: str) -> QLabel:
    lbl = QLabel(title)
    lbl.setStyleSheet("""
        font-size: 10px; font-weight: 700;
        color: {muted};
        letter-spacing: 1.2px;
        border-bottom: 1px solid {border};
        padding-bottom: 4px;
        background: transparent;
    """.format(muted=COLORS["text_muted"], border=COLORS["border"]))
    return lbl


def _label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color:{COLORS['text_secondary']}; font-size:12px; background:transparent;")
    return lbl


# ──────────────────────────────────────────────────────────────────────────────
# Attachment row widget (with Open + Remove buttons)
# ──────────────────────────────────────────────────────────────────────────────

class AttachmentRow(QWidget):
    """One attachment entry with icon, name/size, Open and Remove buttons."""

    def __init__(self, label: str, filepath: str,
                 kind: str, ref, parent=None):
        """
        kind : "existing" | "new"
        ref  : att_id (int) if existing, filepath (str) if new
        """
        super().__init__(parent)
        self._filepath = filepath
        self._kind = kind
        self._ref  = ref
        self._removed = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        # File type icon
        ext = os.path.splitext(filepath)[1].lower()
        icon_map = {".pdf": "📄", ".doc": "📝", ".docx": "📝",
                    ".txt": "📃", ".png": "🖼", ".jpg": "🖼", ".jpeg": "🖼"}
        icon = QLabel(icon_map.get(ext, "📎"))
        icon.setStyleSheet("font-size:16px; background:transparent;")
        icon.setFixedWidth(22)
        layout.addWidget(icon)

        # Name + size
        info_col = QVBoxLayout()
        info_col.setSpacing(1)
        name_lbl = QLabel(os.path.basename(filepath))
        name_lbl.setStyleSheet(
            f"color:{COLORS['text_primary']}; font-size:12px;"
            f" font-weight:600; background:transparent;"
        )
        name_lbl.setMaximumWidth(300)
        size_lbl = QLabel(label)
        size_lbl.setStyleSheet(
            f"color:{COLORS['text_muted']}; font-size:10px; background:transparent;"
        )
        info_col.addWidget(name_lbl)
        info_col.addWidget(size_lbl)
        layout.addLayout(info_col)
        layout.addStretch()

        # Status indicator (missing file warning)
        if not os.path.exists(filepath):
            warn = QLabel("⚠ Not found")
            warn.setStyleSheet(f"color:{COLORS['accent_red']}; font-size:10px;")
            layout.addWidget(warn)

        # Open button
        open_btn = QPushButton("📂 Open")
        open_btn.setObjectName("iconBtn")
        open_btn.setFixedHeight(28)
        open_btn.setFixedWidth(72)
        open_btn.setToolTip("Open with default application")
        open_btn.clicked.connect(lambda: _open_file(filepath))
        layout.addWidget(open_btn)

        # Remove button
        rm_btn = QPushButton("✕")
        rm_btn.setObjectName("iconBtn")
        rm_btn.setFixedSize(28, 28)
        rm_btn.setToolTip("Remove attachment")
        rm_btn.setStyleSheet(f"""
            QPushButton {{ color:{COLORS['accent_red']}; background:transparent;
                          border:none; font-weight:700; }}
            QPushButton:hover {{ color:white; background:{COLORS['accent_red']};
                                 border-radius:4px; }}
        """)
        rm_btn.clicked.connect(self._on_remove)
        layout.addWidget(rm_btn)

        self.setStyleSheet(f"""
            AttachmentRow {{
                background:{COLORS['bg_card']};
                border:1px solid {COLORS['border']};
                border-radius:6px;
            }}
            AttachmentRow:hover {{
                border-color:{COLORS['accent_blue']}55;
                background:{COLORS['bg_hover']};
            }}
        """)

    def _on_remove(self):
        if self._kind == "existing":
            db.delete_attachment(self._ref)
        self._removed = True
        self.setVisible(False)
        self.deleteLater()

    def get_pending_path(self):
        """Return filepath if this is a new (not yet saved) attachment."""
        if not self._removed and self._kind == "new":
            return self._filepath
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Status selector with colour preview
# ──────────────────────────────────────────────────────────────────────────────

class StatusCombo(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.addItems(STATUSES)
        self.currentTextChanged.connect(self._update_color)
        self._update_color(self.currentText())

    def _update_color(self, text: str):
        fg, bg = STATUS_COLORS.get(text, (COLORS["text_primary"], COLORS["bg_secondary"]))
        self.setStyleSheet(f"""
            QComboBox {{
                background:{bg}; color:{fg};
                border:1px solid {fg}44; border-radius:6px;
                padding:7px 10px; font-weight:600;
            }}
            QComboBox::drop-down {{ border:none; width:28px; }}
            QComboBox QAbstractItemView {{
                background:{COLORS['bg_card']}; border:1px solid {COLORS['border']};
                selection-background-color:{COLORS['bg_hover']}; color:{COLORS['text_primary']};
            }}
        """)


# ──────────────────────────────────────────────────────────────────────────────
# Main dialog
# ──────────────────────────────────────────────────────────────────────────────

class ApplicationDialog(QDialog):
    """Add / Edit application — full form with DB integration and file open support."""

    def __init__(self, app_id: int = None, parent=None):
        super().__init__(parent)
        self._app_id  = app_id
        self._edit_mode = app_id is not None
        self._att_rows: List[AttachmentRow] = []

        self.setWindowTitle("Edit Application" if self._edit_mode else "Add New Application")
        self.setMinimumSize(720, 720)
        self.resize(780, 800)
        self.setModal(True)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setStyleSheet(f"QDialog {{ background:{COLORS['bg_primary']}; }}")

        self._build_ui()
        if self._edit_mode:
            self._load_data()

    # ── Build ─────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header gradient bar
        header = QWidget()
        header.setFixedHeight(68)
        header.setStyleSheet(f"""
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 {COLORS['bg_secondary']}, stop:1 {COLORS['bg_tertiary']});
            border-bottom: 1px solid {COLORS['border']};
        """)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(24, 0, 24, 0)
        hl.setSpacing(12)

        icon = QLabel("✏️" if self._edit_mode else "➕")
        icon.setStyleSheet("font-size:22px; background:transparent;")

        title_col = QVBoxLayout()
        title_col.setSpacing(1)
        title = QLabel("Edit Application" if self._edit_mode else "Add New Application")
        title.setStyleSheet(
            f"font-size:17px; font-weight:700; color:{COLORS['text_primary']}; background:transparent;"
        )
        sub = QLabel(
            "Update existing record" if self._edit_mode
            else "Fill in the details to track a new opportunity"
        )
        sub.setStyleSheet(
            f"font-size:11px; color:{COLORS['text_muted']}; background:transparent;"
        )
        title_col.addWidget(title)
        title_col.addWidget(sub)

        hl.addWidget(icon)
        hl.addLayout(title_col)
        hl.addStretch()
        root.addWidget(header)

        # Tabs
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        root.addWidget(self._tabs, 1)

        self._tabs.addTab(self._build_details_tab(),     "📋  Details")
        self._tabs.addTab(self._build_contact_tab(),     "👤  Contact")
        self._tabs.addTab(self._build_attach_tab(),      "📎  Attachments")
        self._tabs.addTab(self._build_notes_tab(),       "📝  Notes")

        # Footer button bar
        footer = QWidget()
        footer.setFixedHeight(64)
        footer.setStyleSheet(f"""
            background:{COLORS['bg_secondary']};
            border-top:1px solid {COLORS['border']};
        """)
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(24, 0, 24, 0)
        fl.setSpacing(10)

        if self._edit_mode:
            delete_btn = QPushButton("🗑  Delete")
            delete_btn.setObjectName("dangerBtn")
            delete_btn.setFixedHeight(38)
            delete_btn.clicked.connect(self._delete_and_close)
            fl.addWidget(delete_btn)

        fl.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(38)
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("  💾  Save Application")
        save_btn.setObjectName("primaryBtn")
        save_btn.setFixedHeight(38)
        save_btn.setMinimumWidth(180)
        save_btn.clicked.connect(self._save)

        fl.addWidget(cancel_btn)
        fl.addWidget(save_btn)
        root.addWidget(footer)

    def _scrollable(self, inner: QWidget) -> QScrollArea:
        sa = QScrollArea()
        sa.setWidgetResizable(True)
        sa.setFrameShape(QFrame.NoFrame)
        sa.setWidget(inner)
        return sa

    # ── Details tab ───────────────────────────────────────────────────

    def _build_details_tab(self) -> QWidget:
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # ─ Job Info ──────────────────────────────────────────────────
        layout.addWidget(_section("JOB INFORMATION"))
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        self.company_edit  = QLineEdit()
        self.company_edit.setPlaceholderText("e.g. Google, Microsoft…")
        self.company_edit.setFixedHeight(36)

        self.position_edit = QLineEdit()
        self.position_edit.setPlaceholderText("e.g. Senior Software Engineer")
        self.position_edit.setFixedHeight(36)

        self.location_edit = QLineEdit()
        self.location_edit.setPlaceholderText("e.g. Remote / New York, NY")
        self.location_edit.setFixedHeight(36)

        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://careers.example.com/…")
        self.url_edit.setFixedHeight(36)

        form.addRow(_label("Company *"),  self.company_edit)
        form.addRow(_label("Position *"), self.position_edit)
        form.addRow(_label("Location"),   self.location_edit)
        form.addRow(_label("Job URL"),    self.url_edit)
        layout.addLayout(form)

        # ─ Status / Priority / Source ─────────────────────────────────
        layout.addWidget(_section("STATUS & TRACKING"))
        row3 = QHBoxLayout()
        row3.setSpacing(14)

        sc = QVBoxLayout()
        sc.addWidget(_label("Status"))
        self.status_combo = StatusCombo()
        self.status_combo.setFixedHeight(36)
        sc.addWidget(self.status_combo)
        row3.addLayout(sc)

        pc = QVBoxLayout()
        pc.addWidget(_label("Priority"))
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(PRIORITIES)
        self.priority_combo.setCurrentText("Medium")
        self.priority_combo.setFixedHeight(36)
        pc.addWidget(self.priority_combo)
        row3.addLayout(pc)

        src = QVBoxLayout()
        src.addWidget(_label("Source"))
        self.source_combo = QComboBox()
        self.source_combo.addItems([""] + SOURCES)
        self.source_combo.setFixedHeight(36)
        src.addWidget(self.source_combo)
        row3.addLayout(src)
        layout.addLayout(row3)

        # ─ Dates ─────────────────────────────────────────────────────
        layout.addWidget(_section("DATES"))
        dates_row = QHBoxLayout()
        dates_row.setSpacing(14)
        for attr, lbl_text, use_today in [
            ("applied_date_edit", "Applied Date", True),
            ("deadline_edit",     "Deadline",     False),
            ("followup_edit",     "Follow-up",    False),
        ]:
            col = QVBoxLayout()
            col.addWidget(_label(lbl_text))
            de = QDateEdit()
            de.setCalendarPopup(True)
            de.setSpecialValueText("Not set")
            de.setDate(QDate.currentDate() if use_today else QDate(2000, 1, 1))
            de.setMinimumDate(QDate(2000, 1, 1))
            de.setFixedHeight(36)
            setattr(self, attr, de)
            col.addWidget(de)
            dates_row.addLayout(col)
        layout.addLayout(dates_row)

        # ─ Salary ────────────────────────────────────────────────────
        layout.addWidget(_section("SALARY RANGE"))
        sal_row = QHBoxLayout()
        sal_row.setSpacing(10)
        sal_row.addWidget(_label("Min"))
        self.salary_min = QDoubleSpinBox()
        self.salary_min.setRange(0, 9_999_999)
        self.salary_min.setSingleStep(5000)
        self.salary_min.setSpecialValueText("—")
        self.salary_min.setFixedHeight(36)
        sal_row.addWidget(self.salary_min)
        sal_row.addWidget(_label("Max"))
        self.salary_max = QDoubleSpinBox()
        self.salary_max.setRange(0, 9_999_999)
        self.salary_max.setSingleStep(5000)
        self.salary_max.setSpecialValueText("—")
        self.salary_max.setFixedHeight(36)
        sal_row.addWidget(self.salary_max)
        self.currency_combo = QComboBox()
        self.currency_combo.addItems(["USD", "EUR", "GBP", "CAD", "AUD", "INR"])
        self.currency_combo.setFixedWidth(75)
        self.currency_combo.setFixedHeight(36)
        sal_row.addWidget(self.currency_combo)
        sal_row.addStretch()
        layout.addLayout(sal_row)

        # ─ Tags ──────────────────────────────────────────────────────
        layout.addWidget(_section("TAGS"))
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("python, backend, fintech  (comma-separated)")
        self.tags_edit.setFixedHeight(36)
        layout.addWidget(self.tags_edit)

        layout.addStretch()
        return self._scrollable(inner)

    # ── Contact tab ───────────────────────────────────────────────────

    def _build_contact_tab(self) -> QWidget:
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        layout.addWidget(_section("RECRUITER / CONTACT"))
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.contact_name  = QLineEdit()
        self.contact_name.setPlaceholderText("Full name")
        self.contact_name.setFixedHeight(36)

        self.contact_email = QLineEdit()
        self.contact_email.setPlaceholderText("recruiter@company.com")
        self.contact_email.setFixedHeight(36)

        self.contact_phone = QLineEdit()
        self.contact_phone.setPlaceholderText("+1 555 000 0000")
        self.contact_phone.setFixedHeight(36)

        form.addRow(_label("Name"),  self.contact_name)
        form.addRow(_label("Email"), self.contact_email)
        form.addRow(_label("Phone"), self.contact_phone)
        layout.addLayout(form)

        layout.addSpacing(4)
        layout.addWidget(_section("JOB DESCRIPTION"))
        hint = QLabel("Paste the full job description — useful for interview prep and ATS matching.")
        hint.setStyleSheet(f"color:{COLORS['text_muted']}; font-size:11px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.job_desc_edit = QTextEdit()
        self.job_desc_edit.setPlaceholderText("Paste job description here…")
        self.job_desc_edit.setMinimumHeight(260)
        layout.addWidget(self.job_desc_edit)

        layout.addStretch()
        return self._scrollable(inner)

    # ── Attachments tab ───────────────────────────────────────────────

    def _build_attach_tab(self) -> QWidget:
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        layout.addWidget(_section("FILE ATTACHMENTS"))

        info = QLabel(
            "Attach your resume, cover letters, or any documents. "
            "Click  📂 Open  to open any file in its default application."
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"color:{COLORS['text_secondary']}; font-size:12px;")
        layout.addWidget(info)

        browse_btn = QPushButton("  📂  Browse & Attach Files…")
        browse_btn.setFixedHeight(40)
        browse_btn.clicked.connect(self._browse_files)
        layout.addWidget(browse_btn)

        # Scrollable list of attachment rows
        self._att_scroll_inner = QWidget()
        self._att_list_layout = QVBoxLayout(self._att_scroll_inner)
        self._att_list_layout.setContentsMargins(0, 0, 0, 0)
        self._att_list_layout.setSpacing(6)
        self._att_list_layout.addStretch()

        att_scroll = QScrollArea()
        att_scroll.setWidgetResizable(True)
        att_scroll.setFrameShape(QFrame.NoFrame)
        att_scroll.setWidget(self._att_scroll_inner)
        att_scroll.setMinimumHeight(200)
        att_scroll.setStyleSheet(f"""
            QScrollArea {{
                background:{COLORS['bg_secondary']};
                border:1px solid {COLORS['border']};
                border-radius:8px;
            }}
        """)
        layout.addWidget(att_scroll, 1)

        self._no_att_lbl = QLabel("No attachments yet")
        self._no_att_lbl.setAlignment(Qt.AlignCenter)
        self._no_att_lbl.setStyleSheet(
            f"color:{COLORS['text_muted']}; font-size:13px; padding:20px;"
        )
        self._att_list_layout.insertWidget(0, self._no_att_lbl)

        layout.addStretch()

        if self._edit_mode:
            self._load_existing_attachments()

        return self._scrollable(inner)

    # ── Notes tab ─────────────────────────────────────────────────────

    def _build_notes_tab(self) -> QWidget:
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        layout.addWidget(_section("PRIVATE NOTES"))
        hint = QLabel(
            "Keep track of interview impressions, salary negotiation notes, "
            "prep materials, or anything else relevant."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color:{COLORS['text_muted']}; font-size:11px;")
        layout.addWidget(hint)

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText(
            "e.g. 'Round 1 went well — focus on system design for round 2.'\n"
            "      'Salary: asking $X, they offered $Y…'"
        )
        layout.addWidget(self.notes_edit, 1)
        return self._scrollable(inner)

    # ── Data load ─────────────────────────────────────────────────────

    def _load_data(self):
        row = db.get_application(self._app_id)
        if not row:
            return

        self.company_edit.setText(row["company"] or "")
        self.position_edit.setText(row["position"] or "")
        self.location_edit.setText(row["location"] or "")
        self.url_edit.setText(row["job_url"] or "")

        self.status_combo.setCurrentText(row["status"] or "Applied")
        self.priority_combo.setCurrentText(row["priority"] or "Medium")

        idx = self.source_combo.findText(row["source"] or "")
        if idx >= 0:
            self.source_combo.setCurrentIndex(idx)

        for db_field, attr in [
            ("applied_date",   "applied_date_edit"),
            ("deadline",       "deadline_edit"),
            ("follow_up_date", "followup_edit"),
        ]:
            val = row[db_field]
            if val:
                try:
                    qd = QDate.fromString(str(val)[:10], "yyyy-MM-dd")
                    getattr(self, attr).setDate(qd)
                except Exception:
                    pass

        self.salary_min.setValue(row["salary_min"] or 0)
        self.salary_max.setValue(row["salary_max"] or 0)
        idx = self.currency_combo.findText(row["currency"] or "USD")
        if idx >= 0:
            self.currency_combo.setCurrentIndex(idx)

        self.tags_edit.setText(row["tags"] or "")
        self.contact_name.setText(row["contact_name"] or "")
        self.contact_email.setText(row["contact_email"] or "")
        self.contact_phone.setText(row["contact_phone"] or "")
        self.job_desc_edit.setPlainText(row["job_description"] or "")
        self.notes_edit.setPlainText(row["notes"] or "")

    def _load_existing_attachments(self):
        for att in db.get_attachments(self._app_id):
            size = att["file_size"] or 0
            label = _human_size(size)
            self._add_att_row(att["filepath"], label, "existing", att["id"])

    # ── Attachment management ─────────────────────────────────────────

    def _browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Files", "",
            "Documents (*.pdf *.docx *.doc *.txt *.png *.jpg *.jpeg);;All Files (*.*)"
        )
        for fp in files:
            # Skip duplicates
            existing_paths = [r._filepath for r in self._att_rows if not r._removed]
            if fp in existing_paths:
                continue
            size = os.path.getsize(fp) if os.path.exists(fp) else 0
            self._add_att_row(fp, _human_size(size), "new", fp)

    def _add_att_row(self, filepath: str, label: str,
                     kind: str, ref):
        self._no_att_lbl.setVisible(False)
        row = AttachmentRow(label, filepath, kind, ref)
        self._att_rows.append(row)
        # Insert before the trailing stretch
        stretch_idx = self._att_list_layout.count() - 1
        self._att_list_layout.insertWidget(stretch_idx, row)

    # ── Save / Delete ─────────────────────────────────────────────────

    def _save(self):
        company  = self.company_edit.text().strip()
        position = self.position_edit.text().strip()

        if not company:
            self._flash_error(self.company_edit, "Company is required")
            self._tabs.setCurrentIndex(0)
            return
        if not position:
            self._flash_error(self.position_edit, "Position is required")
            self._tabs.setCurrentIndex(0)
            return

        def _date_val(editor):
            d = editor.date()
            return None if d == QDate(2000, 1, 1) else d.toString("yyyy-MM-dd")

        data = {
            "company":         company,
            "position":        position,
            "location":        self.location_edit.text().strip() or None,
            "job_url":         self.url_edit.text().strip() or None,
            "status":          self.status_combo.currentText(),
            "priority":        self.priority_combo.currentText(),
            "source":          self.source_combo.currentText() or None,
            "applied_date":    _date_val(self.applied_date_edit),
            "deadline":        _date_val(self.deadline_edit),
            "follow_up_date":  _date_val(self.followup_edit),
            "salary_min":      self.salary_min.value() or None,
            "salary_max":      self.salary_max.value() or None,
            "currency":        self.currency_combo.currentText(),
            "tags":            self.tags_edit.text().strip() or None,
            "contact_name":    self.contact_name.text().strip() or None,
            "contact_email":   self.contact_email.text().strip() or None,
            "contact_phone":   self.contact_phone.text().strip() or None,
            "job_description": self.job_desc_edit.toPlainText().strip() or None,
            "notes":           self.notes_edit.toPlainText().strip() or None,
        }

        if self._edit_mode:
            db.update_application(self._app_id, data)
            app_id = self._app_id
        else:
            app_id = db.add_application(data)

        # Save new attachments
        for row in self._att_rows:
            pending = row.get_pending_path()
            if pending and os.path.exists(pending):
                db.add_attachment(app_id, pending)

        self.accept()

    def _delete_and_close(self):
        app = db.get_application(self._app_id)
        if not app:
            self.reject()
            return

        confirm = QMessageBox.question(
            self, "Delete Application",
            "<b>Permanently delete</b> the application at "
            "<b>{}</b> for <b>{}</b>?<br><br>"
            "All attachments and activity logs will be removed. "
            "This cannot be undone.".format(app["company"], app["position"]),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            db.delete_application(self._app_id)
            self.done(2)   # custom return code 2 = deleted

    def _flash_error(self, widget, msg: str):
        widget.setStyleSheet(f"""
            QLineEdit {{
                background:{COLORS['bg_secondary']};
                border:2px solid {COLORS['accent_red']};
                border-radius:6px; padding:7px 10px; color:{COLORS['text_primary']};
            }}
        """)
        widget.setPlaceholderText(msg)
        QTimer = __import__("PySide6.QtCore", fromlist=["QTimer"]).QTimer
        QTimer.singleShot(2000, lambda: widget.setStyleSheet(""))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _human_size(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return "{:.0f} {}".format(size, unit)
        size /= 1024
    return "{:.1f} TB".format(size)
