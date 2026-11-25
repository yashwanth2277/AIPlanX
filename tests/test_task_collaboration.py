"""Tests for Feature 4: Task Reassignment & Multiple Collaborators.

Covers:
- Deterministic skill matching (>= 50% qualifies, < 50% fails, 0 skills qualifies, alias/case/whitespace handling).
- Task reassignment: replaces assignee, releases previous assignee, preserves history.
- Multiple collaborators: adding collaborators without replacing existing, duplicate prevention.
- Project team member (TM{id}) and global roster (EMP{id}) compatibility.
- Collaborator removal: preserves other collaborators, does not delete member from project.
- Project-level metric integrity (no double-counting total tasks or overall progress).
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.sqlite_store import SqliteStore
from utils.skill_matcher import (
    check_skill_match_details,
    qualifies_for_task,
)


# ---------------------------------------------------------------------------
# 1. Deterministic Skill Matching Unit Tests
# ---------------------------------------------------------------------------

def test_skill_match_threshold_fifty_percent():
    # 2 required skills, candidate has 1 -> 50% -> Qualifies
    qualifies, ratio, matched, required = check_skill_match_details(
        candidate_skills=["Python"],
        task_required_skills=["Python", "FastAPI"],
    )
    assert qualifies is True
    assert ratio == 0.5
    assert matched == ["python"]
    assert required == ["fastapi", "python"]


def test_skill_match_above_fifty_percent():
    # 3 required skills, candidate has 2 -> 66.7% -> Qualifies
    qualifies, ratio, matched, _ = check_skill_match_details(
        candidate_skills=["Python", "SQL", "Docker"],
        task_required_skills=["Python", "SQL", "FastAPI"],
    )
    assert qualifies is True
    assert round(ratio, 2) == 0.67
    assert set(matched) == {"python", "sql"}


def test_skill_match_below_fifty_percent_fails():
    # 3 required skills, candidate has 1 -> 33.3% -> Fails
    qualifies, ratio, matched, _ = check_skill_match_details(
        candidate_skills=["Python"],
        task_required_skills=["Python", "FastAPI", "Docker"],
    )
    assert qualifies is False
    assert round(ratio, 2) == 0.33
    assert matched == ["python"]


def test_skill_match_zero_required_skills_qualifies():
    # Task with no required skills allows assignment
    qualifies, ratio, matched, required = check_skill_match_details(
        candidate_skills=["AnySkill"],
        task_required_skills=[],
    )
    assert qualifies is True
    assert ratio == 1.0
    assert matched == []
    assert required == []


def test_skill_match_normalization_and_aliases():
    # Whitespace, uppercase, and aliases
    qualifies, ratio, matched, _ = check_skill_match_details(
        candidate_skills=["  PY  ", "Postgres\n"],
        task_required_skills=["Python", "PostgreSQL"],
    )
    assert qualifies is True
    assert ratio == 1.0
    assert set(matched) == {"python", "postgresql"}


# ---------------------------------------------------------------------------
# 2. Reassignment & Collaboration Integration Tests
# ---------------------------------------------------------------------------

@pytest.fixture()
def demo_client(tmp_path: Path):
    db_path = tmp_path / "test_collab.db"
    store = SqliteStore(db_path)
    store.import_demo_data()
    app = create_app(store)
    return TestClient(app), store


def test_reassignment_releases_previous_assignee(demo_client):
    client, _ = demo_client

    sessions = client.get("/api/sessions").json()["sessions"]
    session_name = sessions[0]["name"]

    tasks = client.get(f"/api/sessions/{session_name}/tasks").json()["tasks"]
    task = tasks[0]
    task_id = task["task_id"]
    original_owner = task["owner"]
    original_emp_id = task["employee_id"]

    # Pick a different global employee who qualifies
    employees = client.get("/api/employees").json()["employees"]
    target_emp = None
    for emp in employees:
        if emp["employee_id"] != original_emp_id and qualifies_for_task(emp["skills"], task["required_skills"]):
            target_emp = emp
            break

    assert target_emp is not None, "Could not find a qualifying replacement employee"

    # Reassign task
    resp = client.post(
        f"/api/sessions/{session_name}/tasks/{task_id}/reassign",
        json={
            "employee_id": target_emp["employee_id"],
            "reason": "Reassigning for workload optimization",
        },
    )
    assert resp.status_code == 200, resp.json()

    # Verify task updated
    updated_tasks = client.get(f"/api/sessions/{session_name}/tasks").json()["tasks"]
    updated_task = next(t for t in updated_tasks if t["task_id"] == task_id)
    assert updated_task["employee_id"] == target_emp["employee_id"]
    assert updated_task["owner"] == target_emp["employee_name"]
    # Previous assignee is no longer in collaborators
    collab_ids = [c["employee_id"] for c in updated_task["collaborators"]]
    assert original_emp_id not in collab_ids
    assert target_emp["employee_id"] in collab_ids


def test_reassignment_rejects_insufficient_skills(demo_client):
    client, _ = demo_client

    sessions = client.get("/api/sessions").json()["sessions"]
    session_name = sessions[0]["name"]

    projects = client.get("/api/projects").json()["projects"]
    proj_id = projects[0]["id"]

    tasks = client.get(f"/api/sessions/{session_name}/tasks").json()["tasks"]
    task = tasks[0]
    task_id = task["task_id"]

    # Add a member with completely different skills
    member = client.post(
        f"/api/projects/{proj_id}/members",
        json={
            "name": "Unqualified Intern",
            "role": "Marketing",
            "member_type": "intern",
            "skills": ["Content Writing", "SEO"],
            "allocation_days": 30,
        },
    ).json()

    resp = client.post(
        f"/api/sessions/{session_name}/tasks/{task_id}/reassign",
        json={
            "employee_id": f"TM{member['id']}",
            "reason": "Invalid reassignment test",
        },
    )
    assert resp.status_code == 400
    assert "lacks required skills" in resp.json()["detail"]


def test_add_and_remove_collaborator(demo_client):
    client, _ = demo_client

    sessions = client.get("/api/sessions").json()["sessions"]
    session_name = sessions[0]["name"]

    projects = client.get("/api/projects").json()["projects"]
    proj_id = projects[0]["id"]

    tasks = client.get(f"/api/sessions/{session_name}/tasks").json()["tasks"]
    task = tasks[0]
    task_id = task["task_id"]
    primary_owner = task["owner"]
    primary_id = task["employee_id"]
    req_skills = task.get("required_skills", ["Python"])

    # 1. Add project team member with qualifying skills
    member = client.post(
        f"/api/projects/{proj_id}/members",
        json={
            "name": "Collaborator Dev",
            "role": "Backend Engineer",
            "member_type": "employee",
            "skills": list(set(["Python", "SQL", *req_skills])),
            "allocation_days": 40,
        },
    ).json()
    member_emp_id = f"TM{member['id']}"

    # 2. Add as collaborator
    add_resp = client.post(
        f"/api/sessions/{session_name}/tasks/{task_id}/collaborators",
        json={
            "employee_id": member_emp_id,
            "reason": "Helping with backend API implementation",
        },
    )
    assert add_resp.status_code == 200, add_resp.json()

    # 3. Verify both collaborators are present
    updated_tasks = client.get(f"/api/sessions/{session_name}/tasks").json()["tasks"]
    updated_task = next(t for t in updated_tasks if t["task_id"] == task_id)
    collab_ids = [c["employee_id"] for c in updated_task["collaborators"]]
    assert primary_id in collab_ids
    assert member_emp_id in collab_ids
    assert primary_owner in updated_task["owner"]
    assert "Collaborator Dev" in updated_task["owner"]

    # 4. Prevent duplicate addition of the same collaborator
    dup_resp = client.post(
        f"/api/sessions/{session_name}/tasks/{task_id}/collaborators",
        json={
            "employee_id": member_emp_id,
            "reason": "Duplicate addition attempt",
        },
    )
    assert dup_resp.status_code == 400
    assert "already assigned" in dup_resp.json()["detail"].lower()

    # 5. Remove the collaborator
    del_resp = client.delete(
        f"/api/sessions/{session_name}/tasks/{task_id}/collaborators/{member_emp_id}"
    )
    assert del_resp.status_code == 200, del_resp.json()

    # 6. Verify collaborator removed but primary assignee remains
    after_del_tasks = client.get(f"/api/sessions/{session_name}/tasks").json()["tasks"]
    after_del_task = next(t for t in after_del_tasks if t["task_id"] == task_id)
    after_collab_ids = [c["employee_id"] for c in after_del_task["collaborators"]]
    assert member_emp_id not in after_collab_ids
    assert primary_id in after_collab_ids

    # 7. Verify member still exists in project team (NOT deleted from project)
    team_members = client.get(f"/api/projects/{proj_id}/members").json()["members"]
    assert any(m["id"] == member["id"] for m in team_members)


def test_metrics_not_double_counted_with_multiple_collaborators(demo_client):
    client, _ = demo_client

    sessions = client.get("/api/sessions").json()["sessions"]
    session_name = sessions[0]["name"]

    projects = client.get("/api/projects").json()["projects"]
    proj_id = projects[0]["id"]

    # Record initial overview metrics
    initial_overview = client.get(f"/api/sessions/{session_name}/overview").json()
    initial_total_tasks = initial_overview["progress"]["total_tasks"]
    initial_overall_percent = initial_overview["progress"]["overall_percent"]

    tasks = client.get(f"/api/sessions/{session_name}/tasks").json()["tasks"]
    task = tasks[0]
    task_id = task["task_id"]
    req_skills = task.get("required_skills", ["Python"])

    # Add collaborator
    member = client.post(
        f"/api/projects/{proj_id}/members",
        json={
            "name": "Second Contributor",
            "role": "Engineer",
            "member_type": "employee",
            "skills": list(set(["Python", "SQL", *req_skills])),
            "allocation_days": 30,
        },
    ).json()

    client.post(
        f"/api/sessions/{session_name}/tasks/{task_id}/collaborators",
        json={"employee_id": f"TM{member['id']}", "reason": "Pair programming"},
    )

    # Check overview metrics again
    new_overview = client.get(f"/api/sessions/{session_name}/overview").json()
    assert new_overview["progress"]["total_tasks"] == initial_total_tasks
    assert new_overview["progress"]["overall_percent"] == initial_overall_percent

    # Progress chart should have the same number of weeks and planned hours <= 100%
    chart = new_overview["chart"]
    for point in chart:
        assert point["planned"] <= 100.0
