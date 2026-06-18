"""
database.py - SQLite database layer for Application Tracker.

Architecture
────────────
  DatabaseManager   – connection lifecycle, migrations, context manager
  ApplicationDAO    – full CRUD for the Application model
  AttachmentDAO     – CRUD for Attachment model
  ActivityLogDAO    – write/query the audit trail

Module-level convenience functions are provided so existing callers
(dashboard, applications_view, etc.) work without changes.

Compatible with Python 3.6+.
"""

import sqlite3
import os
import json
import csv
import io
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

from models import (
    Application, Attachment, ActivityLog, DashboardStats,
    ApplicationStatus, Priority, ValidationError, _now,
)

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "applications.db")

# Schema version — increment when adding migrations
SCHEMA_VERSION = 2


# ──────────────────────────────────────────────────────────────────────────────
# Custom exceptions
# ──────────────────────────────────────────────────────────────────────────────

class DatabaseError(Exception):
    """Raised for unrecoverable DB errors."""

class RecordNotFoundError(DatabaseError):
    """Raised when a requested record does not exist."""
    def __init__(self, model: str, id: int):
        super().__init__("{} with id={} not found.".format(model, id))
        self.model = model
        self.id    = id

class DuplicateError(DatabaseError):
    """Raised on unique-constraint violations."""


# ──────────────────────────────────────────────────────────────────────────────
# DatabaseManager
# ──────────────────────────────────────────────────────────────────────────────

class DatabaseManager:
    """
    Manages the SQLite connection, schema creation, and migrations.

    Usage as context manager (preferred for transactions):
        with DatabaseManager() as db:
            db.conn.execute(...)

    Or use the module-level `get_connection()` for one-off queries.
    """

    _SCHEMA_SQL = """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS applications (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            company         TEXT    NOT NULL,
            position        TEXT    NOT NULL,
            location        TEXT,
            job_url         TEXT,
            salary_min      REAL,
            salary_max      REAL,
            currency        TEXT    NOT NULL DEFAULT 'USD',
            status          TEXT    NOT NULL DEFAULT 'Applied',
            priority        TEXT    NOT NULL DEFAULT 'Medium',
            source          TEXT,
            applied_date    TEXT,
            deadline        TEXT,
            follow_up_date  TEXT,
            contact_name    TEXT,
            contact_email   TEXT,
            contact_phone   TEXT,
            job_description TEXT,
            notes           TEXT,
            tags            TEXT,
            created_at      TEXT    NOT NULL,
            updated_at      TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS attachments (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id  INTEGER NOT NULL
                                REFERENCES applications(id) ON DELETE CASCADE,
            filename        TEXT    NOT NULL,
            filepath        TEXT    NOT NULL,
            file_type       TEXT,
            file_size       INTEGER DEFAULT 0,
            uploaded_at     TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS activity_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id  INTEGER
                                REFERENCES applications(id) ON DELETE CASCADE,
            action          TEXT    NOT NULL,
            description     TEXT,
            timestamp       TEXT    NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_app_status   ON applications(status);
        CREATE INDEX IF NOT EXISTS idx_app_priority ON applications(priority);
        CREATE INDEX IF NOT EXISTS idx_app_company  ON applications(company COLLATE NOCASE);
        CREATE INDEX IF NOT EXISTS idx_app_updated  ON applications(updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_att_app_id   ON attachments(application_id);
        CREATE INDEX IF NOT EXISTS idx_log_app_id   ON activity_log(application_id);
        CREATE INDEX IF NOT EXISTS idx_log_ts       ON activity_log(timestamp DESC);
    """

    # ── Migrations (keyed by target version) ─────────────────────────
    _MIGRATIONS: Dict[int, str] = {
        2: """
            -- v2: add source column if missing (idempotent via ALTER TABLE)
            ALTER TABLE applications ADD COLUMN source TEXT;
        """,
    }

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn: Optional[sqlite3.Connection] = None

    # ── Connection lifecycle ──────────────────────────────────────────

    def open(self) -> "DatabaseManager":
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        return self

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self) -> "DatabaseManager":
        return self.open()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            if exc_type:
                self.conn.rollback()
            else:
                self.conn.commit()
        self.close()
        return False  # do not suppress exceptions

    # ── Schema & migrations ───────────────────────────────────────────

    def init_schema(self):
        """Create tables, indexes, and run any pending migrations."""
        with self:
            self.conn.executescript(self._SCHEMA_SQL)
            self._run_migrations()

    def _current_version(self) -> int:
        try:
            row = self.conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
            return row[0] or 0
        except sqlite3.OperationalError:
            return 0

    def _run_migrations(self):
        current = self._current_version()
        if current == 0:
            # Fresh install — set to latest version directly
            self.conn.execute("DELETE FROM schema_version")
            self.conn.execute("INSERT INTO schema_version VALUES (?)", (SCHEMA_VERSION,))
            return

        for version in sorted(self._MIGRATIONS.keys()):
            if version > current:
                try:
                    self.conn.executescript(self._MIGRATIONS[version])
                    self.conn.execute(
                        "UPDATE schema_version SET version = ?", (version,)
                    )
                except sqlite3.OperationalError:
                    # Column may already exist (idempotent migration)
                    self.conn.execute(
                        "UPDATE schema_version SET version = ?", (version,)
                    )


# ──────────────────────────────────────────────────────────────────────────────
# Module-level helpers (shared by all DAOs)
# ──────────────────────────────────────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    """Return an open SQLite connection with row_factory configured."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db() -> None:
    """Public entry point: initialise schema + run migrations."""
    mgr = DatabaseManager()
    mgr.init_schema()


# ──────────────────────────────────────────────────────────────────────────────
# ApplicationDAO
# ──────────────────────────────────────────────────────────────────────────────

class ApplicationDAO:
    """
    Data Access Object for the `applications` table.

    All write operations automatically append an audit log entry.
    """

    # ── Create ────────────────────────────────────────────────────────

    @staticmethod
    def insert(app: Application) -> int:
        """
        Persist a new Application and return the generated id.
        Raises ValidationError if the model is invalid.
        """
        app.validate()
        data = app.to_dict()
        data.setdefault("created_at", _now())
        data.setdefault("updated_at", _now())

        cols   = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        sql    = "INSERT INTO applications ({}) VALUES ({})".format(cols, placeholders)

        conn = get_connection()
        try:
            with conn:
                cur = conn.execute(sql, list(data.values()))
                app_id = cur.lastrowid
                app.id = app_id
                ActivityLogDAO.write(
                    conn, app_id, "Created",
                    "Application added for {}".format(app.company),
                )
        except sqlite3.IntegrityError as exc:
            raise DuplicateError(str(exc)) from exc
        finally:
            conn.close()
        return app_id

    # ── Read ──────────────────────────────────────────────────────────

    @staticmethod
    def get(app_id: int) -> Application:
        """
        Fetch a single Application by primary key.
        Raises RecordNotFoundError if not found.
        """
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM applications WHERE id = ?", (app_id,)
            ).fetchone()
        finally:
            conn.close()

        if row is None:
            raise RecordNotFoundError("Application", app_id)
        return Application.from_row(row)

    @staticmethod
    def get_or_none(app_id: int) -> Optional[Application]:
        """Like get(), but returns None instead of raising."""
        try:
            return ApplicationDAO.get(app_id)
        except RecordNotFoundError:
            return None

    @staticmethod
    def list_all(
        search: str   = "",
        status: str   = "All",
        priority: str = "All",
        sort_col: str = "updated_at",
        sort_dir: str = "DESC",
        limit: Optional[int] = None,
        offset: int          = 0,
    ) -> List[Application]:
        """
        Return applications matching the given filters.

        Parameters
        ----------
        search   : free-text search across company / position / location / tags
        status   : filter by ApplicationStatus value, or "All"
        priority : filter by Priority value, or "All"
        sort_col : column name to sort by (allowlisted)
        sort_dir : "ASC" or "DESC"
        limit    : optional row cap
        offset   : pagination offset
        """
        _ALLOWED_COLS = {
            "company", "position", "status", "priority",
            "applied_date", "updated_at", "created_at", "salary_min",
        }
        if sort_col not in _ALLOWED_COLS:
            sort_col = "updated_at"
        if sort_dir not in {"ASC", "DESC"}:
            sort_dir = "DESC"

        sql    = "SELECT * FROM applications WHERE 1=1"
        params: List[Any] = []

        if search:
            sql += (" AND (company LIKE ? OR position LIKE ?"
                    " OR location LIKE ? OR tags LIKE ? OR notes LIKE ?)")
            like = "%{}%".format(search)
            params.extend([like, like, like, like, like])

        if status != "All":
            sql += " AND status = ?"
            params.append(status)

        if priority != "All":
            sql += " AND priority = ?"
            params.append(priority)

        sql += " ORDER BY {} {}".format(sort_col, sort_dir)

        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

        conn = get_connection()
        try:
            rows = conn.execute(sql, params).fetchall()
        finally:
            conn.close()

        return [Application.from_row(r) for r in rows]

    @staticmethod
    def count(status: str = "All", priority: str = "All") -> int:
        """Return the total count of applications matching the given filters."""
        sql    = "SELECT COUNT(*) FROM applications WHERE 1=1"
        params: List[Any] = []
        if status != "All":
            sql += " AND status = ?"
            params.append(status)
        if priority != "All":
            sql += " AND priority = ?"
            params.append(priority)

        conn = get_connection()
        try:
            return conn.execute(sql, params).fetchone()[0]
        finally:
            conn.close()

    @staticmethod
    def get_overdue_followups() -> List[Application]:
        """Return active applications whose follow_up_date has passed."""
        today = datetime.now().strftime("%Y-%m-%d")
        sql = """
            SELECT * FROM applications
            WHERE follow_up_date IS NOT NULL
              AND follow_up_date < ?
              AND status NOT IN (?, ?, ?, ?)
            ORDER BY follow_up_date ASC
        """
        terminal = [s.value for s in ApplicationStatus.terminal()]
        conn = get_connection()
        try:
            rows = conn.execute(sql, [today] + terminal[:4]).fetchall()
        finally:
            conn.close()
        return [Application.from_row(r) for r in rows]

    @staticmethod
    def search_by_company(company: str) -> List[Application]:
        """Case-insensitive exact company name lookup."""
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM applications WHERE company = ? COLLATE NOCASE"
                " ORDER BY applied_date DESC",
                (company,),
            ).fetchall()
        finally:
            conn.close()
        return [Application.from_row(r) for r in rows]

    @staticmethod
    def get_by_status(status: str) -> List[Application]:
        return ApplicationDAO.list_all(status=status)

    @staticmethod
    def get_by_tag(tag: str) -> List[Application]:
        """Return all applications that include the given tag."""
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM applications WHERE tags LIKE ?",
                ("%{}%".format(tag),),
            ).fetchall()
        finally:
            conn.close()
        return [Application.from_row(r) for r in rows if tag in Application.from_row(r).tag_list]

    # ── Update ────────────────────────────────────────────────────────

    @staticmethod
    def update(app_id: int, fields: Dict[str, Any]) -> Application:
        """
        Patch specific fields of an application.

        Parameters
        ----------
        app_id : target row id
        fields : dict of column → new value (id, created_at excluded)

        Returns the updated Application.
        Raises RecordNotFoundError if id does not exist.
        """
        # Safety: never allow overriding pk or immutable timestamps
        for key in ("id", "created_at"):
            fields.pop(key, None)

        fields["updated_at"] = _now()

        set_clause = ", ".join("{} = ?".format(k) for k in fields)
        sql = "UPDATE applications SET {} WHERE id = ?".format(set_clause)

        conn = get_connection()
        try:
            with conn:
                cur = conn.execute(sql, list(fields.values()) + [app_id])
                if cur.rowcount == 0:
                    raise RecordNotFoundError("Application", app_id)
                ActivityLogDAO.write(
                    conn, app_id, "Updated",
                    "Fields updated: {}".format(", ".join(str(k) for k in fields.keys()
                                                          if k != "updated_at")),
                )
        finally:
            conn.close()

        return ApplicationDAO.get(app_id)

    @staticmethod
    def update_status(app_id: int, new_status: str) -> Application:
        """
        Change the status of an application and log a dedicated status-change event.
        Raises ValueError for invalid status strings.
        """
        if new_status not in ApplicationStatus.values():
            raise ValueError("Invalid status: {}".format(new_status))

        old_app = ApplicationDAO.get(app_id)   # raises if not found
        old_status = old_app.status

        conn = get_connection()
        try:
            with conn:
                conn.execute(
                    "UPDATE applications SET status = ?, updated_at = ? WHERE id = ?",
                    (new_status, _now(), app_id),
                )
                ActivityLogDAO.write(
                    conn, app_id, "StatusChange",
                    "{} -> {}".format(old_status, new_status),
                )
        finally:
            conn.close()

        return ApplicationDAO.get(app_id)

    @staticmethod
    def update_from_model(app: Application) -> Application:
        """
        Persist all fields from an Application instance.
        The instance must have a non-None `id`.
        """
        if app.id is None:
            raise ValueError("Application.id must be set to call update_from_model().")
        app.validate()
        return ApplicationDAO.update(app.id, app.to_dict())

    # ── Delete ────────────────────────────────────────────────────────

    @staticmethod
    def delete(app_id: int) -> None:
        """
        Hard-delete an application and all its attachments / log entries
        (via FK ON DELETE CASCADE).
        Raises RecordNotFoundError if the id does not exist.
        """
        ApplicationDAO.get(app_id)   # existence check
        conn = get_connection()
        try:
            with conn:
                conn.execute("DELETE FROM applications WHERE id = ?", (app_id,))
        finally:
            conn.close()

    # ── Bulk operations ───────────────────────────────────────────────

    @staticmethod
    def bulk_insert(apps: List[Application]) -> List[int]:
        """
        Insert multiple applications in a single transaction.
        Returns a list of new ids in the same order.
        Rolls back the entire batch on any failure.
        """
        for app in apps:
            app.validate()

        ids: List[int] = []
        conn = get_connection()
        try:
            with conn:
                for app in apps:
                    data = app.to_dict()
                    data.setdefault("created_at", _now())
                    data.setdefault("updated_at", _now())
                    cols         = ", ".join(data.keys())
                    placeholders = ", ".join(["?"] * len(data))
                    cur = conn.execute(
                        "INSERT INTO applications ({}) VALUES ({})".format(cols, placeholders),
                        list(data.values()),
                    )
                    app_id = cur.lastrowid
                    app.id = app_id
                    ids.append(app_id)
                    ActivityLogDAO.write(
                        conn, app_id, "Created",
                        "Bulk import: {} @ {}".format(app.position, app.company),
                    )
        finally:
            conn.close()
        return ids

    @staticmethod
    def bulk_delete(app_ids: List[int]) -> int:
        """Delete multiple applications. Returns the number of rows deleted."""
        if not app_ids:
            return 0
        placeholders = ", ".join(["?"] * len(app_ids))
        conn = get_connection()
        try:
            with conn:
                cur = conn.execute(
                    "DELETE FROM applications WHERE id IN ({})".format(placeholders),
                    app_ids,
                )
                return cur.rowcount
        finally:
            conn.close()

    @staticmethod
    def bulk_update_status(app_ids: List[int], new_status: str) -> int:
        """Set the same status on multiple applications. Returns rows affected."""
        if new_status not in ApplicationStatus.values():
            raise ValueError("Invalid status: {}".format(new_status))
        if not app_ids:
            return 0
        now = _now()
        placeholders = ", ".join(["?"] * len(app_ids))
        conn = get_connection()
        try:
            with conn:
                cur = conn.execute(
                    "UPDATE applications SET status = ?, updated_at = ?"
                    " WHERE id IN ({})".format(placeholders),
                    [new_status, now] + list(app_ids),
                )
                for app_id in app_ids:
                    ActivityLogDAO.write(
                        conn, app_id, "StatusChange",
                        "Bulk status set to {}".format(new_status),
                    )
                return cur.rowcount
        finally:
            conn.close()

    # ── Analytics & aggregation ───────────────────────────────────────

    @staticmethod
    def get_dashboard_stats() -> DashboardStats:
        """Return a fully populated DashboardStats view model."""
        conn = get_connection()
        try:
            total = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]

            by_status_rows = conn.execute(
                "SELECT status, COUNT(*) as cnt FROM applications GROUP BY status"
            ).fetchall()
            by_status = {r["status"]: r["cnt"] for r in by_status_rows}

            recent_rows = conn.execute(
                "SELECT * FROM applications ORDER BY created_at DESC LIMIT 5"
            ).fetchall()
            recent = [Application.from_row(r) for r in recent_rows]

            monthly_rows = conn.execute(
                """SELECT strftime('%Y-%m', applied_date) as month, COUNT(*) as cnt
                   FROM applications
                   WHERE applied_date IS NOT NULL
                   GROUP BY month
                   ORDER BY month DESC
                   LIMIT 12"""
            ).fetchall()
            monthly = [{"month": r["month"], "cnt": r["cnt"]} for r in monthly_rows]

            overdue_count = conn.execute(
                """SELECT COUNT(*) FROM applications
                   WHERE follow_up_date IS NOT NULL
                     AND follow_up_date < date('now')
                     AND status NOT IN (?, ?, ?, ?)""",
                ["Accepted", "Rejected", "Withdrawn", "Ghosted"],
            ).fetchone()[0]

        finally:
            conn.close()

        return DashboardStats(
            total=total,
            by_status=by_status,
            recent=recent,
            monthly=monthly,
            overdue_followups=overdue_count,
        )

    @staticmethod
    def get_status_timeline() -> List[Dict[str, Any]]:
        """Monthly application counts for the last 12 months."""
        conn = get_connection()
        try:
            rows = conn.execute(
                """SELECT strftime('%Y-%m', applied_date) as month,
                          status, COUNT(*) as cnt
                   FROM applications
                   WHERE applied_date IS NOT NULL
                   GROUP BY month, status
                   ORDER BY month ASC"""
            ).fetchall()
        finally:
            conn.close()
        return [{"month": r["month"], "status": r["status"], "cnt": r["cnt"]} for r in rows]

    # ── Export ────────────────────────────────────────────────────────

    @staticmethod
    def export_to_csv(app_ids: Optional[List[int]] = None) -> str:
        """
        Return all (or selected) applications as a CSV string.
        Pass app_ids=None to export everything.
        """
        apps = (
            ApplicationDAO.list_all()
            if app_ids is None
            else [ApplicationDAO.get(i) for i in app_ids]
        )
        if not apps:
            return ""

        output   = io.StringIO()
        fieldnames = list(apps[0].to_export_dict().keys())
        writer   = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for app in apps:
            writer.writerow(app.to_export_dict())
        return output.getvalue()

    @staticmethod
    def export_to_json(app_ids: Optional[List[int]] = None) -> str:
        """Return all (or selected) applications as a pretty-printed JSON string."""
        apps = (
            ApplicationDAO.list_all()
            if app_ids is None
            else [ApplicationDAO.get(i) for i in app_ids]
        )
        return json.dumps([a.to_export_dict() for a in apps], indent=2, default=str)


# ──────────────────────────────────────────────────────────────────────────────
# AttachmentDAO
# ──────────────────────────────────────────────────────────────────────────────

class AttachmentDAO:
    """Data Access Object for the `attachments` table."""

    @staticmethod
    def insert(att: Attachment) -> int:
        """Persist a new Attachment and return its id."""
        conn = get_connection()
        try:
            with conn:
                cur = conn.execute(
                    """INSERT INTO attachments
                       (application_id, filename, filepath, file_type, file_size, uploaded_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (att.application_id, att.filename, att.filepath,
                     att.file_type, att.file_size, att.uploaded_at),
                )
                att_id = cur.lastrowid
                att.id = att_id
                ActivityLogDAO.write(
                    conn, att.application_id, "Attachment",
                    "File attached: {}".format(att.filename),
                )
        finally:
            conn.close()
        return att_id

    @staticmethod
    def insert_file(app_id: int, filepath: str) -> int:
        """Convenience: create an Attachment from a filepath and persist it."""
        att = Attachment(application_id=app_id, filepath=filepath)
        return AttachmentDAO.insert(att)

    @staticmethod
    def get(att_id: int) -> Attachment:
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM attachments WHERE id = ?", (att_id,)
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            raise RecordNotFoundError("Attachment", att_id)
        return Attachment.from_row(row)

    @staticmethod
    def list_for_application(app_id: int) -> List[Attachment]:
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM attachments WHERE application_id = ?"
                " ORDER BY uploaded_at DESC",
                (app_id,),
            ).fetchall()
        finally:
            conn.close()
        return [Attachment.from_row(r) for r in rows]

    @staticmethod
    def delete(att_id: int) -> None:
        """Remove an attachment record (does NOT delete the file on disk)."""
        conn = get_connection()
        try:
            with conn:
                cur = conn.execute(
                    "DELETE FROM attachments WHERE id = ?", (att_id,)
                )
                if cur.rowcount == 0:
                    raise RecordNotFoundError("Attachment", att_id)
        finally:
            conn.close()

    @staticmethod
    def delete_all_for_application(app_id: int) -> int:
        """Remove all attachment records for a given application id."""
        conn = get_connection()
        try:
            with conn:
                cur = conn.execute(
                    "DELETE FROM attachments WHERE application_id = ?", (app_id,)
                )
                return cur.rowcount
        finally:
            conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# ActivityLogDAO
# ──────────────────────────────────────────────────────────────────────────────

class ActivityLogDAO:
    """Data Access Object for the `activity_log` table."""

    @staticmethod
    def write(
        conn: sqlite3.Connection,
        app_id: int,
        action: str,
        description: str,
    ) -> None:
        """Insert a log entry using an existing open connection (in-transaction)."""
        conn.execute(
            "INSERT INTO activity_log (application_id, action, description, timestamp)"
            " VALUES (?, ?, ?, ?)",
            (app_id, action, description, _now()),
        )

    @staticmethod
    def log(app_id: int, action: str, description: str) -> int:
        """Open a new connection, write a log entry, return the new id."""
        conn = get_connection()
        try:
            with conn:
                cur = conn.execute(
                    "INSERT INTO activity_log (application_id, action, description, timestamp)"
                    " VALUES (?, ?, ?, ?)",
                    (app_id, action, description, _now()),
                )
                return cur.lastrowid
        finally:
            conn.close()

    @staticmethod
    def get_for_application(app_id: int, limit: int = 50) -> List[ActivityLog]:
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM activity_log WHERE application_id = ?"
                " ORDER BY timestamp DESC LIMIT ?",
                (app_id, limit),
            ).fetchall()
        finally:
            conn.close()
        return [ActivityLog.from_row(r) for r in rows]

    @staticmethod
    def get_recent(limit: int = 20) -> List[ActivityLog]:
        """Return the most recent log entries across all applications (with joined company/position)."""
        conn = get_connection()
        try:
            rows = conn.execute(
                """SELECT al.*, a.company, a.position
                   FROM activity_log al
                   LEFT JOIN applications a ON al.application_id = a.id
                   ORDER BY al.timestamp DESC
                   LIMIT ?""",
                (limit,),
            ).fetchall()
        finally:
            conn.close()
        return [ActivityLog.from_row(r) for r in rows]

    @staticmethod
    def clear_for_application(app_id: int) -> int:
        """Remove all log entries for a given application. Returns rows deleted."""
        conn = get_connection()
        try:
            with conn:
                cur = conn.execute(
                    "DELETE FROM activity_log WHERE application_id = ?", (app_id,)
                )
                return cur.rowcount
        finally:
            conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# Backwards-compatible module-level shims
# (keep existing callers in dashboard.py / applications_view.py working)
# ──────────────────────────────────────────────────────────────────────────────

def add_application(data: dict) -> int:
    """Shim: build Application from dict and insert. Returns new id."""
    app = Application(
        company  = data.get("company", ""),
        position = data.get("position", ""),
        **{k: v for k, v in data.items() if k not in ("company", "position")},
    )
    return ApplicationDAO.insert(app)


def update_application(app_id: int, data: dict) -> None:
    """Shim: patch application fields from a plain dict."""
    ApplicationDAO.update(app_id, data)


def delete_application(app_id: int) -> None:
    """Shim: delete application by id."""
    ApplicationDAO.delete(app_id)


def get_application(app_id: int):
    """Shim: return raw sqlite3.Row for backward compatibility with dialog._load_data()."""
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT * FROM applications WHERE id = ?", (app_id,)
        ).fetchone()
    finally:
        conn.close()


def get_all_applications(
    search: str   = "",
    status: str   = "All",
    priority: str = "All",
    sort_col: str = "updated_at",
    sort_dir: str = "DESC",
) -> list:
    """Shim: returns raw sqlite3.Rows (preserves table-widget compatibility)."""
    conn = get_connection()
    _ALLOWED = {"company", "position", "status", "priority",
                "applied_date", "updated_at", "created_at"}
    if sort_col not in _ALLOWED:
        sort_col = "updated_at"
    if sort_dir not in {"ASC", "DESC"}:
        sort_dir = "DESC"

    sql    = "SELECT * FROM applications WHERE 1=1"
    params: list = []

    if search:
        sql += (" AND (company LIKE ? OR position LIKE ?"
                " OR location LIKE ? OR tags LIKE ?)")
        like = "%{}%".format(search)
        params.extend([like, like, like, like])
    if status != "All":
        sql += " AND status = ?"
        params.append(status)
    if priority != "All":
        sql += " AND priority = ?"
        params.append(priority)

    sql += " ORDER BY {} {}".format(sort_col, sort_dir)
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def get_dashboard_stats() -> dict:
    """Shim: return the legacy dict shape that dashboard.py expects."""
    stats = ApplicationDAO.get_dashboard_stats()
    conn  = get_connection()
    try:
        recent_rows = conn.execute(
            "SELECT * FROM applications ORDER BY created_at DESC LIMIT 5"
        ).fetchall()
        monthly_rows = conn.execute(
            """SELECT strftime('%Y-%m', applied_date) as month, COUNT(*) as cnt
               FROM applications WHERE applied_date IS NOT NULL
               GROUP BY month ORDER BY month DESC LIMIT 12"""
        ).fetchall()
    finally:
        conn.close()

    return {
        "total":    stats.total,
        "by_status":stats.by_status,
        "recent":   recent_rows,   # raw rows for RecentAppRow widget
        "monthly":  monthly_rows,
    }


def add_attachment(app_id: int, filepath: str) -> int:
    """Shim: add file attachment."""
    return AttachmentDAO.insert_file(app_id, filepath)


def get_attachments(app_id: int) -> list:
    """Shim: return raw sqlite3.Rows for attachment list widget."""
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT * FROM attachments WHERE application_id = ? ORDER BY uploaded_at DESC",
            (app_id,),
        ).fetchall()
    finally:
        conn.close()


def delete_attachment(att_id: int) -> None:
    """Shim: delete attachment by id."""
    AttachmentDAO.delete(att_id)


def get_activity_log(app_id: int) -> list:
    """Shim: return raw rows."""
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT * FROM activity_log WHERE application_id = ? ORDER BY timestamp DESC LIMIT 50",
            (app_id,),
        ).fetchall()
    finally:
        conn.close()


def get_recent_activity(limit: int = 20) -> list:
    """Shim: return raw rows with joined company/position."""
    conn = get_connection()
    try:
        return conn.execute(
            """SELECT al.*, a.company, a.position
               FROM activity_log al
               LEFT JOIN applications a ON al.application_id = a.id
               ORDER BY al.timestamp DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    finally:
        conn.close()
