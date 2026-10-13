from pydantic import BaseModel, Field


class ResourceAssignment(BaseModel):
    task_id: int
    required_skills: list[str] = Field(min_length=1)
    recommended_role: str
    estimated_effort_hours: float = Field(gt=0)
    notes: str


class ResourceAllocation(BaseModel):
    project_name: str
    assignments: list[ResourceAssignment] = Field(min_length=1)
    resource_recommendations: list[str] = Field(min_length=1)