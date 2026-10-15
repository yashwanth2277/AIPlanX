
from pydantic import BaseModel, Field


class ManagementAIInsights(BaseModel):
    """Structured AI insights for live project management."""

    executive_summary: str = Field(min_length=10)

    delay_explanations: list[str] = Field(default_factory=list)

    identified_risks: list[str] = Field(default_factory=list)

    recovery_recommendations: list[str] = Field(default_factory=list)
