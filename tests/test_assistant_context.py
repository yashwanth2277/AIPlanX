
import json

import pytest

from utils.assistant_context import build_assistant_context


def test_build_context_from_demo_session():
    context = build_assistant_context("demo")

    assert context["session_name"] == "demo"
    assert context["project"]["name"]
    assert len(context["tasks"]) == 10
    assert len(context["employees"]) == 6
    assert len(context["schedule"]["scheduled_tasks"]) == 10


def test_context_includes_task_progress_and_delays():
    context = build_assistant_context("demo")

    task = next(
        task for task in context["tasks"]
        if task["task_id"] == 1
    )

    assert task["status"] == "in_progress"
    assert task["progress_percent"] == 25.0
    assert len(task["delays"]) == 2


@pytest.mark.parametrize(
    "session_name",
    ["", ".", "..", "../demo", "demo/name"],
)
def test_invalid_session_name_is_rejected(session_name):
    with pytest.raises(ValueError, match="Session name"):
        build_assistant_context(session_name)


def test_missing_report_is_rejected(tmp_path):
    with pytest.raises(FileNotFoundError, match="Project report"):
        build_assistant_context(
            "demo",
            report_path=tmp_path / "missing_report.json",
        )


def test_context_does_not_modify_source_files():
    from pathlib import Path

    paths = [
        Path("final_report.json"),
        Path("employees.csv"),
        Path("management_sessions/demo/management_state.json"),
        Path("management_sessions/demo/work_schedule.json"),
    ]
    before = {
        path: path.read_bytes()
        for path in paths
    }

    build_assistant_context("demo")

    after = {
        path: path.read_bytes()
        for path in paths
    }

    assert after == before
