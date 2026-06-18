"""
models.py - Domain model classes for Application Tracker.

Provides strongly-typed Python objects for every database entity,
including validation, serialization, and convenience factory methods.
Compatible with Python 3.6+.
"""

import os
from datetime import datetime, date
from enum import Enum
from typing import Optional, List, Dict, Any


# ──────────────────────────────────────────────────────────────────────────────
# Enumerations
# ──────────────────────────────────────────────────────────────────────────────

class ApplicationStatus(Enum):
    APPLIED    = "Applied"
    SCREENING  = "Screening"
    INTERVIEW  = "Interview"
    TECHNICAL  = "Technical"
    OFFER      = "Offer"
    ACCEPTED   = "Accepted"
    REJECTED   = "Rejected"
    WITHDRAWN  = "Withdrawn"
    GHOSTED    = "Ghosted"

    @classmethod
    def values(cls) -> List[str]:
        return [m.value for m in cls]

    @classmethod
    def from_str(cls, value: str) -> "ApplicationStatus":
        for member in cls:
            if member.value.lower() == value.lower():
                return member
        raise ValueError("Unknown status: {}".format(value))

    # Active pipeline stages (not terminal)
    @classmethod
    def active(cls) -> List["ApplicationStatus"]:
        return [cls.APPLIED, cls.SCREENING, cls.INTERVIEW, cls.TECHNICAL, cls.OFFER]

    # Terminal stages
    @classmethod
    def terminal(cls) -> List["ApplicationStatus"]:
        return [cls.ACCEPTED, cls.REJECTED, cls.WITHDRAWN, cls.GHOSTED]


class Priority(Enum):
    HIGH   = "High"
    MEDIUM = "Medium"
    LOW    = "Low"

    @classmethod
    def values(cls) -> List[str]:
        return [m.value for m in cls]

    @classmethod
    def from_str(cls, value: str) -> "Priority":
        for member in cls:
            if member.value.lower() == value.lower():
                return member
        raise ValueError("Unknown priority: {}".format(value))


class JobSource(Enum):
    LINKEDIN        = "LinkedIn"
    INDEED          = "Indeed"
    COMPANY_WEBSITE = "Company Website"
    REFERRAL        = "Referral"
    GLASSDOOR       = "Glassdoor"
    ANGELLIST       = "AngelList"
    HANDSHAKE       = "Handshake"
    OTHER           = "Other"

    @classmethod
    def values(cls) -> List[str]:
        return [m.value for m in cls]


# ──────────────────────────────────────────────────────────────────────────────
# Validation helpers
# ──────────────────────────────────────────────────────────────────────────────

class ValidationError(Exception):
    """Raised when model data fails validation."""
    def __init__(self, field: str, message: str):
        self.field   = field
        self.message = message
        super().__init__("[{}] {}".format(field, message))


def _require_non_empty(value: Optional[str], field: str) -> str:
    if not value or not value.strip():
        raise ValidationError(field, "is required and cannot be empty.")
    return value.strip()


def _validate_date_str(value: Optional[str], field: str) -> Optional[str]:
    """Accept ISO-8601 date (YYYY-MM-DD) or None."""
    if not value:
        return None
    try:
        datetime.strptime(value[:10], "%Y-%m-%d")
        return value[:10]
    except ValueError:
        raise ValidationError(field, "must be in YYYY-MM-DD format, got: {}".format(value))


def _validate_email(value: Optional[str], field: str = "contact_email") -> Optional[str]:
    if not value:
        return None
    value = value.strip()
    if "@" not in value or "." not in value.split("@")[-1]:
        raise ValidationError(field, "is not a valid e-mail address.")
    return value


def _validate_salary(value: Optional[float], field: str) -> Optional[float]:
    if value is None:
        return None
    if value < 0:
        raise ValidationError(field, "cannot be negative.")
    return value


# ──────────────────────────────────────────────────────────────────────────────
# Application model
# ──────────────────────────────────────────────────────────────────────────────

class Application:
    """
    Full representation of a job application.

    All fields mirror the `applications` table columns.
    Instances can be created from a dict (raw DB row) via `Application.from_row()`
    or built directly for insert/update via the constructor.
    """

    # Fields that may be set on construction
    FIELDS = [
        "id", "company", "position", "location", "job_url",
        "salary_min", "salary_max", "currency",
        "status", "priority", "source",
        "applied_date", "deadline", "follow_up_date",
        "contact_name", "contact_email", "contact_phone",
        "job_description", "notes", "tags",
        "created_at", "updated_at",
    ]

    def __init__(
        self,
        company: str,
        position: str,
        *,
        id: Optional[int]            = None,
        location: Optional[str]      = None,
        job_url: Optional[str]       = None,
        salary_min: Optional[float]  = None,
        salary_max: Optional[float]  = None,
        currency: str                = "USD",
        status: str                  = ApplicationStatus.APPLIED.value,
        priority: str                = Priority.MEDIUM.value,
        source: Optional[str]        = None,
        applied_date: Optional[str]  = None,
        deadline: Optional[str]      = None,
        follow_up_date: Optional[str]= None,
        contact_name: Optional[str]  = None,
        contact_email: Optional[str] = None,
        contact_phone: Optional[str] = None,
        job_description: Optional[str] = None,
        notes: Optional[str]         = None,
        tags: Optional[str]          = None,
        created_at: Optional[str]    = None,
        updated_at: Optional[str]    = None,
    ):
        now = _now()

        # Required
        self.id:           Optional[int]   = id
        self.company:      str             = _require_non_empty(company,  "company")
        self.position:     str             = _require_non_empty(position, "position")

        # Contact / location
        self.location:     Optional[str]   = location
        self.job_url:      Optional[str]   = job_url
        self.contact_name: Optional[str]   = contact_name
        self.contact_email:Optional[str]   = _validate_email(contact_email)
        self.contact_phone:Optional[str]   = contact_phone

        # Salary
        self.salary_min:   Optional[float] = _validate_salary(salary_min, "salary_min")
        self.salary_max:   Optional[float] = _validate_salary(salary_max, "salary_max")
        self.currency:     str             = currency or "USD"

        # Status / meta
        self.status:       str             = status   or ApplicationStatus.APPLIED.value
        self.priority:     str             = priority or Priority.MEDIUM.value
        self.source:       Optional[str]   = source

        # Dates (validated as ISO strings)
        self.applied_date:    Optional[str] = _validate_date_str(applied_date,   "applied_date")
        self.deadline:        Optional[str] = _validate_date_str(deadline,        "deadline")
        self.follow_up_date:  Optional[str] = _validate_date_str(follow_up_date,  "follow_up_date")

        # Content
        self.job_description: Optional[str] = job_description
        self.notes:           Optional[str] = notes
        self.tags:            Optional[str] = tags

        # Timestamps
        self.created_at: str = created_at or now
        self.updated_at: str = updated_at or now

        # Cross-field validation
        self._validate_salary_range()

    # ── Validation ────────────────────────────────────────────────────

    def _validate_salary_range(self):
        if (self.salary_min is not None and
                self.salary_max is not None and
                self.salary_min > self.salary_max):
            raise ValidationError(
                "salary_max",
                "salary_max ({}) must be >= salary_min ({}).".format(
                    self.salary_max, self.salary_min
                ),
            )

    def validate(self):
        """Run all field validations. Raises ValidationError on failure."""
        _require_non_empty(self.company,  "company")
        _require_non_empty(self.position, "position")
        self._validate_salary_range()
        if self.status not in ApplicationStatus.values():
            raise ValidationError("status", "Invalid status: {}".format(self.status))
        if self.priority not in Priority.values():
            raise ValidationError("priority", "Invalid priority: {}".format(self.priority))

    # ── Tags helpers ──────────────────────────────────────────────────

    @property
    def tag_list(self) -> List[str]:
        """Return tags as a cleaned list of strings."""
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(",") if t.strip()]

    def add_tag(self, tag: str):
        existing = self.tag_list
        if tag.strip() and tag.strip() not in existing:
            existing.append(tag.strip())
            self.tags = ", ".join(existing)

    def remove_tag(self, tag: str):
        self.tags = ", ".join(t for t in self.tag_list if t != tag.strip())

    # ── Status helpers ────────────────────────────────────────────────

    @property
    def is_active(self) -> bool:
        return self.status in [s.value for s in ApplicationStatus.active()]

    @property
    def is_terminal(self) -> bool:
        return self.status in [s.value for s in ApplicationStatus.terminal()]

    @property
    def days_since_applied(self) -> Optional[int]:
        if not self.applied_date:
            return None
        try:
            d = datetime.strptime(self.applied_date, "%Y-%m-%d").date()
            return (date.today() - d).days
        except ValueError:
            return None

    @property
    def is_overdue_followup(self) -> bool:
        if not self.follow_up_date:
            return False
        try:
            d = datetime.strptime(self.follow_up_date, "%Y-%m-%d").date()
            return date.today() > d and self.is_active
        except ValueError:
            return False

    @property
    def salary_display(self) -> str:
        """Human-readable salary range string."""
        cur = self.currency or "USD"
        if self.salary_min and self.salary_max:
            return "{} {:,.0f} – {:,.0f}".format(cur, self.salary_min, self.salary_max)
        if self.salary_min:
            return "{} {:,.0f}+".format(cur, self.salary_min)
        if self.salary_max:
            return "Up to {} {:,.0f}".format(cur, self.salary_max)
        return ""

    # ── Serialization ─────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Return all fields as a plain dict (suitable for DB insert/update)."""
        return {
            "company":         self.company,
            "position":        self.position,
            "location":        self.location,
            "job_url":         self.job_url,
            "salary_min":      self.salary_min,
            "salary_max":      self.salary_max,
            "currency":        self.currency,
            "status":          self.status,
            "priority":        self.priority,
            "source":          self.source,
            "applied_date":    self.applied_date,
            "deadline":        self.deadline,
            "follow_up_date":  self.follow_up_date,
            "contact_name":    self.contact_name,
            "contact_email":   self.contact_email,
            "contact_phone":   self.contact_phone,
            "job_description": self.job_description,
            "notes":           self.notes,
            "tags":            self.tags,
            "created_at":      self.created_at,
            "updated_at":      self.updated_at,
        }

    def to_export_dict(self) -> Dict[str, Any]:
        """Flat dict including id, salary display, and tag list for CSV/JSON export."""
        d = self.to_dict()
        d["id"]             = self.id
        d["salary_display"] = self.salary_display
        d["tag_list"]       = self.tag_list
        d["days_applied"]   = self.days_since_applied
        d["overdue"]        = self.is_overdue_followup
        return d

    @classmethod
    def from_row(cls, row) -> "Application":
        """
        Factory: build an Application from a sqlite3.Row (or dict-like object).
        Returns None-safe for missing columns.
        """
        def _get(key, default=None):
            try:
                return row[key]
            except (IndexError, KeyError):
                return default

        obj = cls.__new__(cls)
        obj.id             = _get("id")
        obj.company        = _get("company", "")
        obj.position       = _get("position", "")
        obj.location       = _get("location")
        obj.job_url        = _get("job_url")
        obj.salary_min     = _get("salary_min")
        obj.salary_max     = _get("salary_max")
        obj.currency       = _get("currency", "USD")
        obj.status         = _get("status", ApplicationStatus.APPLIED.value)
        obj.priority       = _get("priority", Priority.MEDIUM.value)
        obj.source         = _get("source")
        obj.applied_date   = _get("applied_date")
        obj.deadline       = _get("deadline")
        obj.follow_up_date = _get("follow_up_date")
        obj.contact_name   = _get("contact_name")
        obj.contact_email  = _get("contact_email")
        obj.contact_phone  = _get("contact_phone")
        obj.job_description= _get("job_description")
        obj.notes          = _get("notes")
        obj.tags           = _get("tags")
        obj.created_at     = _get("created_at", _now())
        obj.updated_at     = _get("updated_at", _now())
        return obj

    def __repr__(self):
        return "Application(id={}, company={!r}, position={!r}, status={!r})".format(
            self.id, self.company, self.position, self.status
        )

    def __eq__(self, other):
        if not isinstance(other, Application):
            return False
        return self.id is not None and self.id == other.id


# ──────────────────────────────────────────────────────────────────────────────
# Attachment model
# ──────────────────────────────────────────────────────────────────────────────

class Attachment:
    """Represents a file attached to a job application."""

    def __init__(
        self,
        application_id: int,
        filepath: str,
        *,
        id: Optional[int]          = None,
        filename: Optional[str]    = None,
        file_type: Optional[str]   = None,
        file_size: Optional[int]   = None,
        uploaded_at: Optional[str] = None,
    ):
        self.id             = id
        self.application_id = application_id
        self.filepath       = filepath
        self.filename       = filename or os.path.basename(filepath)
        _, ext              = os.path.splitext(self.filename)
        self.file_type      = file_type or ext.lstrip(".").upper() or "FILE"
        self.file_size      = file_size if file_size is not None else (
            os.path.getsize(filepath) if os.path.exists(filepath) else 0
        )
        self.uploaded_at    = uploaded_at or _now()

    @classmethod
    def from_row(cls, row) -> "Attachment":
        def _get(key, default=None):
            try:
                return row[key]
            except (IndexError, KeyError):
                return default

        obj = cls.__new__(cls)
        obj.id             = _get("id")
        obj.application_id = _get("application_id")
        obj.filepath       = _get("filepath", "")
        obj.filename       = _get("filename", "")
        obj.file_type      = _get("file_type", "FILE")
        obj.file_size      = _get("file_size", 0)
        obj.uploaded_at    = _get("uploaded_at", _now())
        return obj

    @property
    def size_display(self) -> str:
        size = self.file_size or 0
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return "{:.0f} {}".format(size, unit)
            size /= 1024
        return "{:.1f} TB".format(size)

    @property
    def exists_on_disk(self) -> bool:
        return os.path.isfile(self.filepath)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "application_id": self.application_id,
            "filename":       self.filename,
            "filepath":       self.filepath,
            "file_type":      self.file_type,
            "file_size":      self.file_size,
            "uploaded_at":    self.uploaded_at,
        }

    def __repr__(self):
        return "Attachment(id={}, filename={!r}, size={})".format(
            self.id, self.filename, self.size_display
        )


# ──────────────────────────────────────────────────────────────────────────────
# ActivityLog model
# ──────────────────────────────────────────────────────────────────────────────

class ActivityLog:
    """Represents a single audit-trail entry for an application."""

    ACTIONS = ["Created", "Updated", "Attachment", "StatusChange", "Deleted", "Note"]

    def __init__(
        self,
        application_id: int,
        action: str,
        description: str,
        *,
        id: Optional[int]         = None,
        timestamp: Optional[str]  = None,
        # Joined fields (not stored, populated on query)
        company: Optional[str]    = None,
        position: Optional[str]   = None,
    ):
        self.id             = id
        self.application_id = application_id
        self.action         = action
        self.description    = description
        self.timestamp      = timestamp or _now()
        self.company        = company
        self.position       = position

    @classmethod
    def from_row(cls, row) -> "ActivityLog":
        def _get(key, default=None):
            try:
                return row[key]
            except (IndexError, KeyError):
                return default

        obj = cls.__new__(cls)
        obj.id             = _get("id")
        obj.application_id = _get("application_id")
        obj.action         = _get("action", "")
        obj.description    = _get("description", "")
        obj.timestamp      = _get("timestamp", _now())
        obj.company        = _get("company")
        obj.position       = _get("position")
        return obj

    def to_dict(self) -> Dict[str, Any]:
        return {
            "application_id": self.application_id,
            "action":         self.action,
            "description":    self.description,
            "timestamp":      self.timestamp,
        }

    def __repr__(self):
        return "ActivityLog(id={}, action={!r}, app_id={})".format(
            self.id, self.action, self.application_id
        )


# ──────────────────────────────────────────────────────────────────────────────
# Dashboard stats model
# ──────────────────────────────────────────────────────────────────────────────

class DashboardStats:
    """Aggregated view model for the dashboard page."""

    def __init__(
        self,
        total: int,
        by_status: Dict[str, int],
        recent: List[Application],
        monthly: List[Dict[str, Any]],
        overdue_followups: int = 0,
    ):
        self.total             = total
        self.by_status         = by_status
        self.recent            = recent
        self.monthly           = monthly
        self.overdue_followups = overdue_followups

    # Convenience accessors
    @property
    def applied_count(self) -> int:
        return self.by_status.get(ApplicationStatus.APPLIED.value, 0)

    @property
    def interview_count(self) -> int:
        return (self.by_status.get(ApplicationStatus.INTERVIEW.value, 0) +
                self.by_status.get(ApplicationStatus.TECHNICAL.value, 0))

    @property
    def offer_count(self) -> int:
        return (self.by_status.get(ApplicationStatus.OFFER.value, 0) +
                self.by_status.get(ApplicationStatus.ACCEPTED.value, 0))

    @property
    def rejected_count(self) -> int:
        return self.by_status.get(ApplicationStatus.REJECTED.value, 0)

    @property
    def in_progress_count(self) -> int:
        return sum(
            self.by_status.get(s.value, 0)
            for s in ApplicationStatus.active()
        )

    @property
    def success_rate(self) -> float:
        """Offer / (total - active) as a percentage."""
        closed = self.total - self.in_progress_count
        if closed == 0:
            return 0.0
        return round(self.offer_count / closed * 100, 1)

    def __repr__(self):
        return "DashboardStats(total={}, offers={}, success_rate={}%)".format(
            self.total, self.offer_count, self.success_rate
        )


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now().isoformat(sep=" ", timespec="seconds")
