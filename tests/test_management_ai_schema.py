
from pydantic import ValidationError
import pytest

from schemas.management_ai import ManagementAIInsights


def test_management_ai_insights_accept_valid_response():
    insights = ManagementAIInsights(
        executive_summary="The project is progressing with one delayed task.",
        delay_explanations=["The API delay may postpone dependent UI work."],
        identified_risks=["Integration testing may start late."],
        recovery_recommendations=["Review the API blocker with the assigned employee."],
    )

    assert len(insights.delay_explanations) == 1
    assert len(insights.identified_risks) == 1
    assert len(insights.recovery_recommendations) == 1


def test_management_ai_insights_allow_empty_optional_lists():
    insights = ManagementAIInsights(
        executive_summary="The project is currently on track."
    )

    assert insights.delay_explanations == []
    assert insights.identified_risks == []
    assert insights.recovery_recommendations == []


def test_management_ai_insights_reject_empty_summary():
    with pytest.raises(ValidationError):
        ManagementAIInsights(executive_summary="Too short")
