from pydantic import BaseModel, Field


class Recommendation(BaseModel):
    recommendation_id: int
    title: str
    description: str
    priority: str
    expected_benefit: str


class RecommendationReport(BaseModel):
    project_name: str
    recommendations: list[Recommendation] = Field(min_length=1)
    summary: str