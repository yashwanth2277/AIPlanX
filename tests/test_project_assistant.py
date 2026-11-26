import json
from unittest.mock import patch

import pytest

from agents.project_assistant import (
    DEFAULT_MAX_REQUEST_TOKENS,
    ask_project_assistant,
    compact_assistant_context,
    estimate_tokens,
    format_and_trim_history,
)
from utils.assistant_context import build_assistant_context


class FakeResponse:
    content = "Task 1 is in progress. I recommend reviewing its delay."


class FakeLLM:
    def __init__(self):
        self.last_prompt = ""

    def invoke(self, prompt):
        assert "PROJECT CONTEXT:" in prompt
        assert "USER QUESTION:" in prompt
        self.last_prompt = prompt
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


def test_context_compaction_reduces_token_footprint():
    # Build actual demo context
    context = build_assistant_context("demo")

    # Intentionally inject redundant heavy blob to verify it is stripped
    context["original_report"] = {"bloat": "x" * 20000}

    compacted = compact_assistant_context(context, question="Status of task 1")

    # Redundant fields should be stripped
    assert "original_report" not in compacted

    # Essential project awareness retained
    assert compacted["project"]["name"]
    assert len(compacted["tasks"]) == 10
    assert len(compacted["team"]) == 6

    # Verify task 1 details are preserved
    t1 = next(t for t in compacted["tasks"] if t["id"] == 1)
    assert t1["status"] == "in_progress"
    assert "25" in t1["progress"]
    assert len(t1["delays"]) == 2

    # Verify token footprint is well within limits (< 2000 tokens)
    serialized = json.dumps(compacted)
    estimated_tokens = estimate_tokens(serialized)
    assert estimated_tokens < 2000


def test_request_token_budget_enforced_in_prompt():
    fake_llm = FakeLLM()
    context = build_assistant_context("demo")

    with patch(
        "agents.project_assistant._get_llm",
        return_value=fake_llm,
    ):
        ask_project_assistant(
            "What tasks are currently in progress?",
            context=context,
        )

    assert fake_llm.last_prompt
    total_prompt_tokens = estimate_tokens(fake_llm.last_prompt)
    assert total_prompt_tokens <= DEFAULT_MAX_REQUEST_TOKENS


def test_history_trimming_keeps_within_budget():
    # Create 30 turns of conversation history
    long_history = [
        {"role": "user" if i % 2 == 0 else "bot", "text": f"Turn message number {i}: " + ("detail " * 25)}
        for i in range(30)
    ]

    formatted_history = format_and_trim_history(long_history, max_history_tokens=300)
    history_tokens = estimate_tokens(formatted_history)

    assert history_tokens <= 350
    # Must preserve the most recent message (turn 29)
    assert "Turn message number 29" in formatted_history
    # Older turns (e.g. turn 0) must have been trimmed
    assert "Turn message number 0:" not in formatted_history


def test_rate_limit_413_handled_gracefully():
    class RateLimit413LLM:
        def invoke(self, prompt):
            raise Exception("Error code: 413 - {'error': {'message': 'Request too large for model openai/gpt-oss-120b', 'code': 'rate_limit_exceeded'}}")

    with patch(
        "agents.project_assistant._get_llm",
        return_value=RateLimit413LLM(),
    ):
        with pytest.raises(ValueError, match="exceeded Groq token or rate limits"):
            ask_project_assistant(
                "Summarize all tasks",
                context={"project": {"name": "Demo"}},
            )


def test_rate_limit_429_handled_gracefully():
    class RateLimit429LLM:
        def invoke(self, prompt):
            raise Exception("Error code: 429 - {'error': {'message': 'Rate limit reached', 'type': 'requests', 'code': 'rate_limit_exceeded'}}")

    with patch(
        "agents.project_assistant._get_llm",
        return_value=RateLimit429LLM(),
    ):
        with pytest.raises(ValueError, match="temporarily rate-limited"):
            ask_project_assistant(
                "Summarize all tasks",
                context={"project": {"name": "Demo"}},
            )


def test_timeout_handled_gracefully():
    class TimeoutLLM:
        def invoke(self, prompt):
            raise Exception("Connection timed out after 30000ms")

    with patch(
        "agents.project_assistant._get_llm",
        return_value=TimeoutLLM(),
    ):
        with pytest.raises(ValueError, match="timed out or could not reach Groq"):
            ask_project_assistant(
                "Summarize all tasks",
                context={"project": {"name": "Demo"}},
            )
