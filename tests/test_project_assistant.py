
from unittest.mock import patch

import pytest

from agents.project_assistant import ask_project_assistant


class FakeResponse:
    content = "Task 1 is in progress. I recommend reviewing its delay."


class FakeLLM:
    def invoke(self, prompt):
        assert "PROJECT CONTEXT:" in prompt
        assert "USER QUESTION:" in prompt
        return FakeResponse()


def test_assistant_answers_using_supplied_context():
    context = {
        "project": {"name": "Demo Project"},
        "tasks": [{"task_id": 1, "status": "in_progress"}],
    }

    with patch(
        "agents.project_assistant._get_llm",
        return_value=FakeLLM(),
    ):
        answer = ask_project_assistant(
            "What is the status of Task 1?",
            context=context,
        )

    assert "Task 1" in answer
    assert "recommend" in answer.lower()


@pytest.mark.parametrize("question", ["", "   ", "\n"])
def test_assistant_rejects_empty_questions(question):
    with pytest.raises(ValueError, match="Question"):
        ask_project_assistant(question, context={})


def test_assistant_rejects_oversized_questions():
    with pytest.raises(ValueError, match="8000"):
        ask_project_assistant("a" * 8001, context={})


def test_assistant_rejects_empty_model_response():
    class EmptyLLM:
        def invoke(self, prompt):
            class Response:
                content = "   "

            return Response()

    with patch(
        "agents.project_assistant._get_llm",
        return_value=EmptyLLM(),
    ):
        with pytest.raises(ValueError, match="empty response"):
            ask_project_assistant(
                "Summarize the project",
                context={"project": {"name": "Demo"}},
            )
