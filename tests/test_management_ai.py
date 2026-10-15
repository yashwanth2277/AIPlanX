
import pytest

from schemas.project_plan import ProjectPlan, Task
from schemas.project_management import (
    ProjectManagementState,
    TaskProgress,
    TaskStatus,
)
from schemas.management_ai import ManagementAIInsights
from agents import management_ai


def make_management_state():
    plan = ProjectPlan(
        project_name="Demo",
        project_summary="Management AI test",
        total_estimated_hours=4,
        tasks=[
            Task(
                task_id=1,
                title="Build API",
                description="Create API",
                required_skills=["Python"],
                estimated_hours=4,
                priority="high",
                dependencies=[],
            )
        ],
        risks=[],
    )

    return ProjectManagementState(
        plan=plan,
        task_progress=[
            TaskProgress(
                task_id=1,
                status=TaskStatus.IN_PROGRESS,
                progress_percent=50,
                actual_hours_spent=2,
            )
        ],
    )


class FakeModels:
    def __init__(self, response):
        self.response = response
        self.last_call = None

    def generate_content(self, **kwargs):
        self.last_call = kwargs
        return self.response


class FakeClient:
    def __init__(self, response):
        self.models = FakeModels(response)


def test_generate_management_insights_success(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

    fake_client = FakeClient(
        type(
            "Response",
            (),
            {
                "text": (
                    '{"executive_summary":"Project is progressing.",'
                    '"delay_explanations":[],"identified_risks":[],'
                    '"recovery_recommendations":["Review API progress."]}'
                )
            },
        )()
    )

    monkeypatch.setattr(
        management_ai.genai,
        "Client",
        lambda **kwargs: fake_client,
    )

    result = management_ai.generate_management_insights(
        make_management_state()
    )

    assert isinstance(result, ManagementAIInsights)
    assert result.executive_summary == "Project is progressing."
    assert result.recovery_recommendations == ["Review API progress."]

    assert fake_client.models.last_call["model"]
    assert fake_client.models.last_call["config"]["response_schema"] \
        is ManagementAIInsights


def test_generate_management_insights_requires_api_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    with pytest.raises(ValueError, match="GOOGLE_API_KEY is missing"):
        management_ai.generate_management_insights(
            make_management_state()
        )


def test_generate_management_insights_rejects_empty_response(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

    fake_client = FakeClient(
        type("Response", (), {"text": None})()
    )

    monkeypatch.setattr(
        management_ai.genai,
        "Client",
        lambda **kwargs: fake_client,
    )

    with pytest.raises(ValueError, match="empty management assessment"):
        management_ai.generate_management_insights(
            make_management_state()
        )


def test_generate_management_insights_rejects_invalid_json(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

    fake_client = FakeClient(
        type("Response", (), {"text": "{invalid json"})()
    )

    monkeypatch.setattr(
        management_ai.genai,
        "Client",
        lambda **kwargs: fake_client,
    )

    with pytest.raises(
        ValueError,
        match="invalid management assessment",
    ):
        management_ai.generate_management_insights(
            make_management_state()
        )
