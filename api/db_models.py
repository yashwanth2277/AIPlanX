"""SQLAlchemy models for AIPlanX.

The original planning tables (employees, projects, sessions) are preserved
unchanged in structure. Project-management SaaS tables are added alongside
them and linked by identifiers rather than replacing the existing graph data.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# --------------------------------------------------------------------------- #
# Existing planning tables (unchanged contract)
# --------------------------------------------------------------------------- #
class EmployeeRow(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[str] = mapped_column(String(64), unique=True)
    payload: Mapped[dict] = mapped_column(JSON)


class ProjectRow(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    summary: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    final_report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    team_workflow: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class SessionRow(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    management_state: Mapped[dict] = mapped_column(JSON)
    work_schedule: Mapped[dict] = mapped_column(JSON)


# --------------------------------------------------------------------------- #
# Accounts and access
# --------------------------------------------------------------------------- #
class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Supabase subject ("sub") claim. Null for dev-provider accounts.
    auth_uid: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), default="")
    # Account-level role: owner / manager / employee / intern.
    role: Mapped[str] = mapped_column(String(32), default="employee")
    # Password hash only used by the local dev provider.
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    theme: Mapped[str] = mapped_column(String(16), default="dark")
    notification_prefs: Mapped[dict] = mapped_column(
        JSON, default=lambda: {"in_app": True, "email": True}
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ProjectMemberRow(Base):
    __tablename__ = "project_members"
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_member_user"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(32), default="employee")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TeamMemberRow(Base):
    """A person record inside one project (employee or intern)."""

    __tablename__ = "team_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), index=True)
    role: Mapped[str] = mapped_column(String(255), default="")
    member_type: Mapped[str] = mapped_column(String(16), default="employee")
    skills: Mapped[list] = mapped_column(JSON, default=list)
    experience: Mapped[float] = mapped_column(Float, default=0)
    weekly_capacity_hours: Mapped[float] = mapped_column(Float, default=40)
    current_workload_percent: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class InvitationRow(Base):
    __tablename__ = "invitations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    role: Mapped[str] = mapped_column(String(32), default="employee")
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id"), nullable=True
    )
    team_member_id: Mapped[int | None] = mapped_column(
        ForeignKey("team_members.id"), nullable=True
    )
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    invited_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# --------------------------------------------------------------------------- #
# Project workspace: tasks, assignments, progress, deadlines, reports
# --------------------------------------------------------------------------- #
class TaskRow(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    # Links back to a plan task inside a management session, when AI-derived.
    source_task_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String(16), default="medium")
    status: Mapped[str] = mapped_column(String(32), default="not_started")
    progress_percent: Mapped[float] = mapped_column(Float, default=0)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expected_completion_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    estimated_hours: Mapped[float] = mapped_column(Float, default=0)
    actual_hours: Mapped[float] = mapped_column(Float, default=0)
    completed_work: Mapped[str] = mapped_column(Text, default="")
    remaining_work: Mapped[str] = mapped_column(Text, default="")
    blockers: Mapped[list] = mapped_column(JSON, default=list)
    dependencies: Mapped[list] = mapped_column(JSON, default=list)
    required_skills: Mapped[list] = mapped_column(JSON, default=list)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TaskAssigneeRow(Base):
    __tablename__ = "task_assignees"
    __table_args__ = (
        UniqueConstraint("task_id", "team_member_id", name="uq_task_assignee"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    team_member_id: Mapped[int] = mapped_column(
        ForeignKey("team_members.id"), index=True
    )
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    assigned_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class ProgressUpdateRow(Base):
    __tablename__ = "progress_updates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    user_name: Mapped[str] = mapped_column(String(255), default="")
    user_role: Mapped[str] = mapped_column(String(32), default="")
    previous_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    previous_progress: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32))
    progress_percent: Mapped[float] = mapped_column(Float)
    actual_hours: Mapped[float] = mapped_column(Float, default=0)
    completed_work: Mapped[str] = mapped_column(Text, default="")
    remaining_work: Mapped[str] = mapped_column(Text, default="")
    blockers: Mapped[list] = mapped_column(JSON, default=list)
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DeadlineChangeRow(Base):
    __tablename__ = "deadline_changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    task_id: Mapped[int | None] = mapped_column(
        ForeignKey("tasks.id"), nullable=True, index=True
    )
    previous_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    new_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    reason: Mapped[str] = mapped_column(Text)
    changed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    changed_by_name: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ReportRow(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    generated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class NotificationRow(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id"), nullable=True, index=True
    )
    type: Mapped[str] = mapped_column(String(64), default="general")
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text, default="")
    link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ActivityLogRow(Base):
    __tablename__ = "activity_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    actor_name: Mapped[str] = mapped_column(String(255), default="")
    actor_role: Mapped[str] = mapped_column(String(32), default="")
    action: Mapped[str] = mapped_column(String(64))
    entity_type: Mapped[str] = mapped_column(String(32), default="project")
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    previous_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EmailOutboxRow(Base):
    __tablename__ = "email_outbox"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipient: Mapped[str] = mapped_column(String(255), index=True)
    subject: Mapped[str] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="queued")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class PasswordResetRow(Base):
    __tablename__ = "password_resets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)