from typing import Literal

from pydantic import BaseModel, Field, field_validator

from schemas.project_management import TaskStatus


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=10000)
    summary: str = Field(default="", max_length=2000)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Project name cannot be empty")
        return stripped


class UpdateProjectRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10000)
    summary: str | None = Field(default=None, max_length=2000)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is not None:
            stripped = value.strip()
            if not stripped:
                raise ValueError("Project name cannot be empty")
            return stripped
        return value


class PlanRequest(BaseModel):
    description: str = Field(min_length=10, max_length=8000)
    session_name: str | None = Field(default=None, max_length=64)
    create_session: bool = True


class CreateSessionRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    project_id: int | None = None


class ProgressUpdateRequest(BaseModel):
    status: TaskStatus
    progress_percent: float = Field(ge=0, le=100)
    actual_hours_spent: float | None = Field(default=None, ge=0)

    completed_work: str | None = Field(default=None, max_length=5000)
    remaining_work: str | None = Field(default=None, max_length=5000)
    blockers: list[str] = Field(default_factory=list)
    comment: str | None = Field(default=None, max_length=3000)

    updated_by: str = Field(default="Unspecified", max_length=200)
    updater_role: str | None = Field(default=None, max_length=100)


class DelayRequest(BaseModel):
    delay_hours: float = Field(gt=0)
    reason: str = Field(min_length=3, max_length=2000)


class AnalyzeDelayRequest(BaseModel):
    delay_weeks: int = Field(ge=1, le=52)
    delay_hours: float | None = Field(default=None, gt=0)
    delay_reason: str | None = Field(default=None, min_length=3, max_length=2000)


class ReassignRequest(BaseModel):
    employee_id: str = Field(min_length=1)
    reason: str = Field(min_length=3, max_length=2000)


class AddCollaboratorRequest(BaseModel):
    employee_id: str = Field(min_length=1)
    reason: str = Field(default="Collaborator added", min_length=3, max_length=2000)


class RemoveCollaboratorRequest(BaseModel):
    reason: str = Field(default="Collaborator removed", min_length=3, max_length=2000)


class AssistantAskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=8000)
    session_name: str = Field(min_length=1, max_length=64)


# --------------------------------------------------------------------------- #
# Team members (System B – project-scoped)
# --------------------------------------------------------------------------- #

class CreateTeamMemberRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    role: str = Field(min_length=1, max_length=255)
    member_type: Literal["employee", "intern"] = "employee"
    skills: list[str] = Field(min_length=1)
    allocation_days: int = Field(gt=0)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Name cannot be empty")
        return stripped

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Role cannot be empty")
        return stripped

    @field_validator("skills", mode="before")
    @classmethod
    def validate_skills(cls, value: list) -> list[str]:
        cleaned = [s.strip() for s in value if isinstance(s, str) and s.strip()]
        if not cleaned:
            raise ValueError("At least one skill is required")
        return cleaned


class UpdateTeamMemberRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    role: str | None = Field(default=None, min_length=1, max_length=255)
    member_type: Literal["employee", "intern"] | None = None
    skills: list[str] | None = Field(default=None, min_length=1)
    allocation_days: int | None = Field(default=None, gt=0)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("Name cannot be empty")
        return stripped

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("Role cannot be empty")
        return stripped

    @field_validator("skills", mode="before")
    @classmethod
    def validate_skills(cls, value: list | None) -> list[str] | None:
        if value is None:
            return None
        cleaned = [s.strip() for s in value if isinstance(s, str) and s.strip()]
        if not cleaned:
            raise ValueError("At least one skill is required")
        return cleaned


class TeamMemberResponse(BaseModel):
    id: int
    project_id: int
    name: str
    role: str
    member_type: str
    skills: list[str]
    allocation_days: int | None
    experience: float
    weekly_capacity_hours: float
    current_workload_percent: float
    created_at: str
    updated_at: str
