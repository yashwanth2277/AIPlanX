"""Tests for project-scoped team member endpoints (Feature 3 – System B).

Covers: add employee, add intern, list, skills persistence, allocation_days
persistence, validation errors, missing project, missing member,
project/member mismatch on delete, deletion, and DB persistence across restarts.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.sqlite_store import SqliteStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_db(tmp_path: Path):
    return tmp_path / "test.db"


@pytest.fixture()
def store(tmp_db: Path):
    s = SqliteStore(tmp_db)
    s.initialize()
    return s


@pytest.fixture()
def client(store: SqliteStore):
    app = create_app(store)
    return TestClient(app)


@pytest.fixture()
def project_id(client: TestClient) -> int:
    resp = client.post("/api/projects", json={"name": "Test Project"})
    assert resp.status_code == 201
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

EMPLOYEE_PAYLOAD = {
    "name": "Alice",
    "role": "Backend Developer",
    "member_type": "employee",
    "skills": ["Python", "FastAPI", "SQL"],
    "allocation_days": 30,
}

INTERN_PAYLOAD = {
    "name": "Bob",
    "role": "Frontend Intern",
    "member_type": "intern",
    "skills": ["React", "CSS"],
    "allocation_days": 14,
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAddEmployee:
    def test_add_employee_returns_201(self, client: TestClient, project_id: int):
        resp = client.post(f"/api/projects/{project_id}/members", json=EMPLOYEE_PAYLOAD)
        assert resp.status_code == 201

    def test_add_employee_fields(self, client: TestClient, project_id: int):
        resp = client.post(f"/api/projects/{project_id}/members", json=EMPLOYEE_PAYLOAD)
        data = resp.json()
        assert data["name"] == "Alice"
        assert data["role"] == "Backend Developer"
        assert data["member_type"] == "employee"
        assert data["project_id"] == project_id
        assert isinstance(data["id"], int)

    def test_add_intern_member_type(self, client: TestClient, project_id: int):
        resp = client.post(f"/api/projects/{project_id}/members", json=INTERN_PAYLOAD)
        assert resp.status_code == 201
        assert resp.json()["member_type"] == "intern"


class TestSkillsAndAllocationDays:
    def test_skills_persisted(self, client: TestClient, project_id: int):
        resp = client.post(f"/api/projects/{project_id}/members", json=EMPLOYEE_PAYLOAD)
        assert resp.json()["skills"] == ["Python", "FastAPI", "SQL"]

    def test_skills_trimmed(self, client: TestClient, project_id: int):
        payload = {**EMPLOYEE_PAYLOAD, "skills": ["  Python  ", " FastAPI "]}
        resp = client.post(f"/api/projects/{project_id}/members", json=payload)
        assert resp.json()["skills"] == ["Python", "FastAPI"]

    def test_allocation_days_persisted(self, client: TestClient, project_id: int):
        resp = client.post(f"/api/projects/{project_id}/members", json=EMPLOYEE_PAYLOAD)
        assert resp.json()["allocation_days"] == 30

    def test_intern_allocation_days(self, client: TestClient, project_id: int):
        resp = client.post(f"/api/projects/{project_id}/members", json=INTERN_PAYLOAD)
        assert resp.json()["allocation_days"] == 14


class TestListMembers:
    def test_list_empty_initially(self, client: TestClient, project_id: int):
        resp = client.get(f"/api/projects/{project_id}/members")
        assert resp.status_code == 200
        assert resp.json()["members"] == []

    def test_list_after_adding(self, client: TestClient, project_id: int):
        client.post(f"/api/projects/{project_id}/members", json=EMPLOYEE_PAYLOAD)
        client.post(f"/api/projects/{project_id}/members", json=INTERN_PAYLOAD)
        resp = client.get(f"/api/projects/{project_id}/members")
        assert resp.status_code == 200
        members = resp.json()["members"]
        assert len(members) == 2
        names = {m["name"] for m in members}
        assert names == {"Alice", "Bob"}

    def test_list_scoped_to_project(self, client: TestClient, project_id: int):
        # Create a second project
        resp2 = client.post("/api/projects", json={"name": "Other Project"})
        other_id = resp2.json()["id"]
        # Add member to other project
        client.post(f"/api/projects/{other_id}/members", json=EMPLOYEE_PAYLOAD)
        # project_id should still be empty
        resp = client.get(f"/api/projects/{project_id}/members")
        assert resp.json()["members"] == []


class TestValidationErrors:
    def test_empty_name_rejected(self, client: TestClient, project_id: int):
        payload = {**EMPLOYEE_PAYLOAD, "name": "   "}
        resp = client.post(f"/api/projects/{project_id}/members", json=payload)
        # Pydantic field_validator raises ValueError → FastAPI returns 422
        assert resp.status_code == 422

    def test_empty_role_rejected(self, client: TestClient, project_id: int):
        payload = {**EMPLOYEE_PAYLOAD, "role": ""}
        resp = client.post(f"/api/projects/{project_id}/members", json=payload)
        assert resp.status_code == 422

    def test_empty_skills_list_rejected(self, client: TestClient, project_id: int):
        payload = {**EMPLOYEE_PAYLOAD, "skills": []}
        resp = client.post(f"/api/projects/{project_id}/members", json=payload)
        assert resp.status_code == 422

    def test_all_blank_skills_rejected(self, client: TestClient, project_id: int):
        payload = {**EMPLOYEE_PAYLOAD, "skills": ["  ", ""]}
        resp = client.post(f"/api/projects/{project_id}/members", json=payload)
        # Pydantic field_validator raises ValueError → FastAPI returns 422
        assert resp.status_code == 422

    def test_invalid_member_type_rejected(self, client: TestClient, project_id: int):
        payload = {**EMPLOYEE_PAYLOAD, "member_type": "contractor"}
        resp = client.post(f"/api/projects/{project_id}/members", json=payload)
        assert resp.status_code == 422

    def test_zero_allocation_days_rejected(self, client: TestClient, project_id: int):
        payload = {**EMPLOYEE_PAYLOAD, "allocation_days": 0}
        resp = client.post(f"/api/projects/{project_id}/members", json=payload)
        assert resp.status_code == 422

    def test_negative_allocation_days_rejected(self, client: TestClient, project_id: int):
        payload = {**EMPLOYEE_PAYLOAD, "allocation_days": -5}
        resp = client.post(f"/api/projects/{project_id}/members", json=payload)
        assert resp.status_code == 422


class TestMissingProject:
    def test_add_to_missing_project(self, client: TestClient):
        resp = client.post("/api/projects/9999/members", json=EMPLOYEE_PAYLOAD)
        assert resp.status_code == 404

    def test_list_from_missing_project(self, client: TestClient):
        resp = client.get("/api/projects/9999/members")
        assert resp.status_code == 404

    def test_delete_from_missing_project(self, client: TestClient):
        resp = client.delete("/api/projects/9999/members/1")
        assert resp.status_code == 404


class TestDeleteMember:
    def test_delete_returns_204(self, client: TestClient, project_id: int):
        member = client.post(
            f"/api/projects/{project_id}/members", json=EMPLOYEE_PAYLOAD
        ).json()
        resp = client.delete(f"/api/projects/{project_id}/members/{member['id']}")
        assert resp.status_code == 204

    def test_deleted_member_not_in_list(self, client: TestClient, project_id: int):
        member = client.post(
            f"/api/projects/{project_id}/members", json=EMPLOYEE_PAYLOAD
        ).json()
        client.delete(f"/api/projects/{project_id}/members/{member['id']}")
        members = client.get(f"/api/projects/{project_id}/members").json()["members"]
        assert all(m["id"] != member["id"] for m in members)

    def test_delete_missing_member(self, client: TestClient, project_id: int):
        resp = client.delete(f"/api/projects/{project_id}/members/9999")
        assert resp.status_code == 404

    def test_delete_member_wrong_project(self, client: TestClient, project_id: int):
        """Deleting a member using the wrong project_id must be rejected."""
        # Create a second project and add a member to it
        other = client.post("/api/projects", json={"name": "Other"}).json()["id"]
        member = client.post(
            f"/api/projects/{other}/members", json=EMPLOYEE_PAYLOAD
        ).json()
        # Attempt to delete via project_id (wrong project)
        resp = client.delete(f"/api/projects/{project_id}/members/{member['id']}")
        assert resp.status_code == 400

    def test_delete_does_not_affect_other_members(
        self, client: TestClient, project_id: int
    ):
        m1 = client.post(
            f"/api/projects/{project_id}/members", json=EMPLOYEE_PAYLOAD
        ).json()
        m2 = client.post(
            f"/api/projects/{project_id}/members", json=INTERN_PAYLOAD
        ).json()
        client.delete(f"/api/projects/{project_id}/members/{m1['id']}")
        members = client.get(f"/api/projects/{project_id}/members").json()["members"]
        assert len(members) == 1
        assert members[0]["id"] == m2["id"]


class TestPersistenceAcrossRestarts:
    def test_members_survive_store_reinitialisation(self, tmp_db: Path):
        """Members added in one store instance must be readable from another."""
        store1 = SqliteStore(tmp_db)
        store1.initialize()
        app1 = create_app(store1)
        client1 = TestClient(app1)

        proj = client1.post("/api/projects", json={"name": "Persist"}).json()["id"]
        client1.post(f"/api/projects/{proj}/members", json=EMPLOYEE_PAYLOAD)

        # Simulate restart by creating a fresh store pointing at the same DB
        store2 = SqliteStore(tmp_db)
        store2.initialize()
        app2 = create_app(store2)
        client2 = TestClient(app2)

        resp = client2.get(f"/api/projects/{proj}/members")
        assert resp.status_code == 200
        members = resp.json()["members"]
        assert len(members) == 1
        assert members[0]["name"] == "Alice"
        assert members[0]["allocation_days"] == 30
        assert members[0]["skills"] == ["Python", "FastAPI", "SQL"]

    def test_migration_idempotent(self, tmp_db: Path):
        """Calling initialize() twice on the same DB must not raise."""
        store = SqliteStore(tmp_db)
        store.initialize()
        store.initialize()  # second call: ALTER TABLE should silently skip


class TestWorkspaceIntegration:
    """Tests verifying project team member integration across workspace features."""

    def test_effective_employees_includes_project_members(
        self, store: SqliteStore, client: TestClient, project_id: int
    ):
        """Project team members must be returned with prefix TM."""
        client.post(f"/api/projects/{project_id}/members", json=EMPLOYEE_PAYLOAD)
        effective = store.list_effective_employees(project_id)
        tm_member = next(
            (e for e in effective if e.employee_name == "Alice"), None
        )
        assert tm_member is not None
        assert tm_member.employee_id.startswith("TM")
        assert "Python" in tm_member.skills

    def test_effective_employees_project_isolation(
        self, store: SqliteStore, client: TestClient
    ):
        """Project 1 members must never leak into Project 2."""
        p1 = client.post("/api/projects", json={"name": "Project 1"}).json()["id"]
        p2 = client.post("/api/projects", json={"name": "Project 2"}).json()["id"]

        client.post(
            f"/api/projects/{p1}/members",
            json={**EMPLOYEE_PAYLOAD, "name": "Member For P1"},
        )
        client.post(
            f"/api/projects/{p2}/members",
            json={**EMPLOYEE_PAYLOAD, "name": "Member For P2"},
        )

        p1_emps = store.list_effective_employees(p1)
        p2_emps = store.list_effective_employees(p2)

        p1_names = {e.employee_name for e in p1_emps}
        p2_names = {e.employee_name for e in p2_emps}

        assert "Member For P1" in p1_names
        assert "Member For P1" not in p2_names
        assert "Member For P2" in p2_names
        assert "Member For P2" not in p1_names

    def test_effective_employees_deduplication(
        self, store: SqliteStore, client: TestClient, project_id: int
    ):
        """A project member with the same name as a global employee takes precedence."""
        store.import_demo_data()
        # Add Rahul as a project team member with distinct role
        client.post(
            f"/api/projects/{project_id}/members",
            json={
                "name": "Rahul",
                "role": "Lead Architect",
                "member_type": "employee",
                "skills": ["Python", "FastAPI"],
                "allocation_days": 60,
            },
        )
        effective = store.list_effective_employees(project_id)
        rahuls = [e for e in effective if e.employee_name.casefold() == "rahul"]
        assert len(rahuls) == 1
        assert rahuls[0].role == "Lead Architect"
        assert rahuls[0].employee_id.startswith("TM")

    def test_employees_endpoint_with_project_id(
        self, client: TestClient, project_id: int
    ):
        """GET /api/employees?project_id=... returns project team members."""
        client.post(f"/api/projects/{project_id}/members", json=EMPLOYEE_PAYLOAD)

        # Scoped request
        scoped_resp = client.get(f"/api/employees?project_id={project_id}")
        assert scoped_resp.status_code == 200
        scoped_names = [e["employee_name"] for e in scoped_resp.json()["employees"]]
        assert "Alice" in scoped_names

        # Unscoped request (global only)
        unscoped_resp = client.get("/api/employees")
        assert unscoped_resp.status_code == 200
        unscoped_names = [e["employee_name"] for e in unscoped_resp.json()["employees"]]
        assert "Alice" not in unscoped_names

    def test_reassign_task_to_project_team_member(self, tmp_db: Path):
        """Reassigning a task to a project team member updates tasks, schedule, and overview."""
        store = SqliteStore(tmp_db)
        store.import_demo_data()
        client = TestClient(create_app(store))

        projects = client.get("/api/projects").json()["projects"]
        assert len(projects) > 0
        proj_id = projects[0]["id"]

        sessions = client.get("/api/sessions").json()["sessions"]
        session_name = sessions[0]["name"]

        # Get initial tasks and identify target task skills
        initial_tasks = client.get(f"/api/sessions/{session_name}/tasks").json()["tasks"]
        target_task = initial_tasks[0]
        task_id = target_task["task_id"]
        required_skills = target_task.get("required_skills", ["Python", "FastAPI"])

        # Add project team member with the necessary skills
        member = client.post(
            f"/api/projects/{proj_id}/members",
            json={
                "name": "Maya Chen",
                "role": "Full Stack Lead",
                "member_type": "employee",
                "skills": list(set(["Python", "FastAPI", "SQL", *required_skills])),
                "allocation_days": 45,
            },
        ).json()

        # Reassign to Maya Chen using prefix TM{id}
        reassign_resp = client.post(
            f"/api/sessions/{session_name}/tasks/{task_id}/reassign",
            json={
                "employee_id": f"TM{member['id']}",
                "reason": "Allocated to dedicated project member",
            },
        )
        assert reassign_resp.status_code == 200, reassign_resp.json()

        # Verify task list shows Maya Chen as owner
        updated_tasks = client.get(f"/api/sessions/{session_name}/tasks").json()["tasks"]
        updated_task = next(t for t in updated_tasks if t["task_id"] == task_id)
        assert updated_task["owner"] == "Maya Chen"
        assert updated_task["employee_id"] == f"TM{member['id']}"

        # Verify schedule shows Maya Chen
        schedule = client.get(f"/api/sessions/{session_name}/schedule").json()
        scheduled_target = next(
            (t for t in schedule["scheduled_tasks"] if t["task_id"] == task_id), None
        )
        if scheduled_target:
            assert scheduled_target["employee_name"] == "Maya Chen"
            assert scheduled_target["employee_id"] == f"TM{member['id']}"

        # Verify overview shows Maya Chen in priority tasks if listed
        overview = client.get(f"/api/sessions/{session_name}/overview").json()
        matching_priority = [
            t for t in overview["priority_tasks"] if t["task_id"] == task_id
        ]
        if matching_priority:
            assert matching_priority[0]["owner"] == "Maya Chen"

    def test_update_team_member_success(self, client: TestClient, project_id: int):
        """Updating member details persists and returns updated member."""
        created = client.post(
            f"/api/projects/{project_id}/members",
            json={
                "name": "Original Name",
                "role": "Junior Dev",
                "member_type": "intern",
                "skills": ["HTML", "CSS"],
                "allocation_days": 15,
            },
        ).json()

        mid = created["id"]
        update_resp = client.patch(
            f"/api/projects/{project_id}/members/{mid}",
            json={
                "name": "Updated Name",
                "role": "Frontend Dev",
                "member_type": "employee",
                "skills": ["HTML", "CSS", "React"],
                "allocation_days": 45,
            },
        )
        assert update_resp.status_code == 200, update_resp.json()
        data = update_resp.json()
        assert data["name"] == "Updated Name"
        assert data["role"] == "Frontend Dev"
        assert data["member_type"] == "employee"
        assert data["skills"] == ["HTML", "CSS", "React"]
        assert data["allocation_days"] == 45

        # Verify persistence on subsequent get
        members = client.get(f"/api/projects/{project_id}/members").json()["members"]
        m = next(item for item in members if item["id"] == mid)
        assert m["name"] == "Updated Name"
        assert m["role"] == "Frontend Dev"

    def test_update_team_member_partial(self, client: TestClient, project_id: int):
        """Partial update updates only the provided fields."""
        created = client.post(
            f"/api/projects/{project_id}/members",
            json={
                "name": "Sam",
                "role": "Tester",
                "member_type": "employee",
                "skills": ["QA"],
                "allocation_days": 20,
            },
        ).json()
        mid = created["id"]

        update_resp = client.put(
            f"/api/projects/{project_id}/members/{mid}",
            json={"allocation_days": 60},
        )
        assert update_resp.status_code == 200
        data = update_resp.json()
        assert data["name"] == "Sam"
        assert data["role"] == "Tester"
        assert data["allocation_days"] == 60

    def test_update_team_member_project_mismatch(self, client: TestClient, project_id: int):
        """Updating member with wrong project_id returns 400."""
        created = client.post(f"/api/projects/{project_id}/members", json=EMPLOYEE_PAYLOAD).json()
        mid = created["id"]

        other_proj = client.post("/api/projects", json={"name": "Other Project"}).json()["id"]
        resp = client.patch(f"/api/projects/{other_proj}/members/{mid}", json={"name": "Hacked"})
        assert resp.status_code == 400
        assert "does not belong to project" in resp.json()["detail"]

