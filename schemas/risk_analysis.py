from pydantic import BaseModel, Field


class ProjectRisk(BaseModel):
    risk_id: int
    title: str
    description: str
    severity: str
    mitigation: str


class RiskAnalysis(BaseModel):
    project_name: str
    overall_risk_level: str
    risks: list[ProjectRisk] = Field(min_length=1)
    recommendations: list[str] = Field(min_length=1)