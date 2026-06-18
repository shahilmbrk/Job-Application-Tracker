"""
ui/styles.py - Global stylesheet and theme tokens for Application Tracker
"""

COLORS = {
    "bg_primary":    "#0d1117",
    "bg_secondary":  "#161b22",
    "bg_tertiary":   "#1c2330",
    "bg_card":       "#21262d",
    "bg_hover":      "#2d333b",
    "border":        "#30363d",
    "border_focus":  "#58a6ff",
    "text_primary":  "#e6edf3",
    "text_secondary":"#8b949e",
    "text_muted":    "#484f58",
    "accent_blue":   "#58a6ff",
    "accent_green":  "#3fb950",
    "accent_orange": "#f0883e",
    "accent_red":    "#f85149",
    "accent_purple": "#bc8cff",
    "accent_yellow": "#d29922",
    "accent_teal":   "#39d353",
    "gradient_start":"#1f6feb",
    "gradient_end":  "#388bfd",
}

STATUS_COLORS = {
    "Applied":       ("#388bfd", "#1f4280"),
    "Screening":     ("#bc8cff", "#3d2a5c"),
    "Interview":     ("#f0883e", "#5a3319"),
    "Technical":     ("#d29922", "#5a4008"),
    "Offer":         ("#3fb950", "#1a4a1f"),
    "Accepted":      ("#39d353", "#163820"),
    "Rejected":      ("#f85149", "#5c1c19"),
    "Withdrawn":     ("#8b949e", "#2d333b"),
    "Ghosted":       ("#484f58", "#1c2330"),
}

PRIORITY_COLORS = {
    "High":   ("#f85149", "#5c1c19"),
    "Medium": ("#f0883e", "#5a3319"),
    "Low":    ("#3fb950", "#1a4a1f"),
}

APP_STYLESHEET = """
/* ── Global ────────────────────────────────────────────────────────── */
* {
    font-family: 'Segoe UI', 'SF Pro Display', Arial, sans-serif;
    color: #e6edf3;
}

QMainWindow, QDialog {
    background-color: #0d1117;
}

QWidget {
    background-color: transparent;
    font-size: 13px;
}

/* ── Scrollbars ─────────────────────────────────────────────────────── */
QScrollBar:vertical {
    background: #0d1117;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #30363d;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #58a6ff; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QScrollBar:horizontal {
    background: #0d1117;
    height: 8px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background: #30363d;
    border-radius: 4px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover { background: #58a6ff; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ── Labels ─────────────────────────────────────────────────────────── */
QLabel {
    color: #e6edf3;
    background: transparent;
}

/* ── Line Edits & Text Inputs ───────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 7px 10px;
    color: #e6edf3;
    selection-background-color: #1f4280;
    font-size: 13px;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border-color: #58a6ff;
    background-color: #1c2330;
}
QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover,
QSpinBox:hover, QDoubleSpinBox:hover {
    border-color: #484f58;
}
QLineEdit::placeholder { color: #484f58; }

/* ── ComboBox ───────────────────────────────────────────────────────── */
QComboBox {
    padding-right: 30px;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border-left: 1px solid #30363d;
    border-radius: 0 6px 6px 0;
}
QComboBox::down-arrow {
    image: none;
    width: 10px;
    height: 10px;
    border-left: 2px solid #8b949e;
    border-bottom: 2px solid #8b949e;
    margin: 0 auto;
    transform: rotate(-45deg);
}
QComboBox QAbstractItemView {
    background-color: #21262d;
    border: 1px solid #30363d;
    border-radius: 6px;
    selection-background-color: #1f4280;
    outline: none;
    padding: 4px;
}
QComboBox QAbstractItemView::item {
    height: 32px;
    padding-left: 8px;
    border-radius: 4px;
}
QComboBox QAbstractItemView::item:hover {
    background-color: #2d333b;
}

/* ── Buttons ─────────────────────────────────────────────────────────── */
QPushButton {
    background-color: #21262d;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px 16px;
    color: #e6edf3;
    font-weight: 500;
    font-size: 13px;
}
QPushButton:hover {
    background-color: #2d333b;
    border-color: #484f58;
}
QPushButton:pressed { background-color: #1c2330; }
QPushButton:disabled { opacity: 0.5; }

QPushButton#primaryBtn {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #1f6feb, stop:1 #388bfd);
    border: none;
    color: #ffffff;
    font-weight: 600;
}
QPushButton#primaryBtn:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #388bfd, stop:1 #58a6ff);
}
QPushButton#dangerBtn {
    background-color: #5c1c19;
    border: 1px solid #f85149;
    color: #f85149;
}
QPushButton#dangerBtn:hover {
    background-color: #f85149;
    color: #ffffff;
}
QPushButton#successBtn {
    background-color: #1a4a1f;
    border: 1px solid #3fb950;
    color: #3fb950;
}
QPushButton#successBtn:hover {
    background-color: #3fb950;
    color: #ffffff;
}
QPushButton#iconBtn {
    background: transparent;
    border: none;
    padding: 4px 8px;
    color: #8b949e;
}
QPushButton#iconBtn:hover { color: #58a6ff; background: #21262d; border-radius: 4px; }

/* ── Table View ─────────────────────────────────────────────────────── */
QTableWidget {
    background-color: #0d1117;
    alternate-background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    gridline-color: #21262d;
    selection-background-color: #1f4280;
    selection-color: #e6edf3;
    outline: none;
}
QTableWidget::item {
    padding: 8px 10px;
    border: none;
}
QTableWidget::item:hover { background-color: #21262d; }
QTableWidget::item:selected { background-color: #1f4280; }

QHeaderView::section {
    background-color: #161b22;
    border: none;
    border-bottom: 2px solid #30363d;
    border-right: 1px solid #30363d;
    padding: 10px 12px;
    font-weight: 600;
    font-size: 12px;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
QHeaderView::section:hover { background-color: #21262d; color: #e6edf3; }
QHeaderView::section:checked { background-color: #1f4280; }

/* ── Tab Widget ─────────────────────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #30363d;
    border-radius: 0 8px 8px 8px;
    background: #161b22;
}
QTabBar::tab {
    background: #0d1117;
    border: 1px solid #30363d;
    border-bottom: none;
    padding: 8px 20px;
    color: #8b949e;
    border-radius: 6px 6px 0 0;
    margin-right: 2px;
}
QTabBar::tab:selected { background: #161b22; color: #e6edf3; border-bottom: 2px solid #58a6ff; }
QTabBar::tab:hover:!selected { background: #21262d; color: #c9d1d9; }

/* ── Checkboxes ─────────────────────────────────────────────────────── */
QCheckBox {
    spacing: 8px;
    color: #e6edf3;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1.5px solid #30363d;
    border-radius: 4px;
    background: #161b22;
}
QCheckBox::indicator:checked {
    background: #388bfd;
    border-color: #388bfd;
}

/* ── Splitter ───────────────────────────────────────────────────────── */
QSplitter::handle {
    background: #30363d;
    width: 1px;
}

/* ── ToolTip ────────────────────────────────────────────────────────── */
QToolTip {
    background-color: #21262d;
    border: 1px solid #30363d;
    color: #e6edf3;
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 12px;
}

/* ── Menu ───────────────────────────────────────────────────────────── */
QMenu {
    background-color: #21262d;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 4px;
}
QMenu::item {
    padding: 8px 24px;
    border-radius: 4px;
    color: #e6edf3;
}
QMenu::item:selected { background-color: #1f4280; }
QMenu::separator { height: 1px; background: #30363d; margin: 4px 8px; }

/* ── Message Box ────────────────────────────────────────────────────── */
QMessageBox {
    background-color: #161b22;
}
QMessageBox QLabel { color: #e6edf3; }

/* ── Date Edit ──────────────────────────────────────────────────────── */
QDateEdit {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 7px 10px;
    color: #e6edf3;
    font-size: 13px;
}
QDateEdit:focus { border-color: #58a6ff; }
QDateEdit::drop-down { subcontrol-origin: padding; subcontrol-position: right; width: 28px; }
QCalendarWidget { background-color: #21262d; border: 1px solid #30363d; border-radius: 8px; }
QCalendarWidget QAbstractItemView { background: #21262d; selection-background-color: #1f4280; }

/* ── Group Box ──────────────────────────────────────────────────────── */
QGroupBox {
    border: 1px solid #30363d;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 8px;
    font-weight: 600;
    color: #8b949e;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    left: 12px;
}

/* ── Frame ──────────────────────────────────────────────────────────── */
QFrame[frameShape="4"], QFrame[frameShape="5"] {
    color: #30363d;
}

/* ── Progress Bar ───────────────────────────────────────────────────── */
QProgressBar {
    background: #21262d;
    border: 1px solid #30363d;
    border-radius: 4px;
    text-align: center;
    color: #e6edf3;
    font-size: 11px;
    height: 10px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1f6feb,stop:1 #388bfd);
    border-radius: 4px;
}
"""
