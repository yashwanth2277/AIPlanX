from unittest.mock import patch

from fastapi.testclient import TestClient

from api.main import create_app
from api.sqlite_store import SqliteStore
from schemas.final_report import FinalProjectReport
from schemas.team_workflow import TeamWorkflow


def make_client(tmp_path):
    store = SqliteStore(tmp_path / "api.db")
    return TestClient(create_app(store)), store


def test_health_and_employees(tmp_path):
    client, _ = make_client(tmp_path)
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    employees = client.get("/api/employees")
    assert employees.status_code == 200
    assert len(employees.json()["employees"]) == 6


def test_overview_and_progress_update(tmp_path):
    client, _ = make_client(tmp_path)
    sessions = client.get("/api/sessions").json()["sessions"]
    assert sessions, "Demo session should be seeded from the planning report"
    name = sessions[0]["name"]
    overview = client.get(f"/api/sessions/{name}/overview")
    assert overview.status_code == 200
    body = overview.json()
    assert body["project"]["name"]
    assert "priority_tasks" in body
    assert body["progress"]["total_tasks"] > 0

    tasks = client.get(f"/api/sessions/{name}/tasks").json()["tasks"]
    pending = next(
        (
            task
            for task in tasks
            if task["status"] == "pending"
        ),
        tasks[0],
    )
    if pending["status"] == "completed":
        return

    updated = client.patch(
        f"/api/sessions/{name}/tasks/{pending['task_id']}/progress",
        json={
            "status": "in_progress",
            "progress_percent": 20,
            "actual_hours_spent": 1,
        },
    )
    assert updated.status_code == 200
    progress = next(
        item
        for item in updated.json()["management_state"]["task_progress"]
        if item["task_id"] == pending["task_id"]
    )
    assert progress["progress_percent"] == 20
    assert updated.json()["management_state"]["assignments"]


def test_assistant_uses_mocked_model(tmp_path):
    client, _ = make_client(tmp_path)
    sessions = client.get("/api/sessions").json()["sessions"]
    assert sessions, "Demo session should be seeded from the planning report"

    with patch(
        "api.main.ask_project_assistant",
        return_value="Task 1 is in progress.",
    ) as mocked:
        response = client.post(
            "/api/assistant/ask",
            json={
                "question": "What is the status of task 1?",
                "session_name": sessions[0]["name"],
            },
        )

    assert response.status_code == 200
    assert "Task 1" in response.json()["answer"]
    mocked.assert_called_once()


def test_planning_job_with_mocked_workflow(tmp_path):
    client, store = make_client(tmp_path)
    report = FinalProjectReport.model_validate_json(
        open("final_report.json", encoding="utf-8").read()
    )
    workflow = type(
        "Workflow",
        (),
        {
            "invoke": lambda self, state: {
                "final_report": report,
                "project_plan": report.project_plan,
                "resource_allocation": report.resource_allocation,
            }
        },
    )()
    team = TeamWorkflow(
        project_name=report.project_plan.project_name,
        mode="role_based",
        nodes=[
            {
                "node_id": "task-1",
                "node_type": "task",
                "title": "Setup",
            }
        ],
    )

    with (
        patch("api.planning.build_project_workflow", return_value=workflow),
        patch("api.planning.build_team_workflow", return_value=team),
        patch("api.planning.Thread") as thread,
    ):
        thread.side_effect = lambda target, args, daemon: type(
            "T",
            (),
            {"start": lambda self: target(*args)},
        )()
        response = client.post(
            "/api/projects/plan",
            json={
                "description": "Build a campus issue reporting platform.",
                "session_name": "apiplan",
                "create_session": True,
            },
        )

    assert response.status_code == 202
    job_id = response.json()["job_id"]
    status = client.get(f"/api/projects/jobs/{job_id}")
    assert status.status_code == 200
    body = status.json()
    assert body["status"] == "completed"
    assert body["session_name"] == "apiplan"
    saved = store.get_session("apiplan")
    assert saved.management_state.plan.project_name == report.project_plan.project_name
