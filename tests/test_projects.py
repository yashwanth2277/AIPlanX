from fastapi.testclient import TestClient

from api.main import create_app
from api.sqlite_store import SqliteStore


def make_client(tmp_path):
    store = SqliteStore(tmp_path / "test_projects.db")
    return TestClient(create_app(store)), store


def test_create_project_success(tmp_path):
    client, _ = make_client(tmp_path)
    response = client.post(
        "/api/projects",
        json={"name": "New Website Redesign", "description": "Revamp the customer portal"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Website Redesign"
    assert data["description"] == "Revamp the customer portal"
    assert data["id"] > 0
    assert data["created_at"]
    assert data["updated_at"]
    assert data["has_report"] is False


def test_create_project_validation(tmp_path):
    client, _ = make_client(tmp_path)
    # Empty name
    response = client.post("/api/projects", json={"name": ""})
    assert response.status_code in (400, 422)

    # Whitespace-only name
    response = client.post("/api/projects", json={"name": "   "})
    assert response.status_code in (400, 422)

    # Missing name field
    response = client.post("/api/projects", json={})
    assert response.status_code in (400, 422)


def test_get_project_and_list_projects(tmp_path):
    client, _ = make_client(tmp_path)
    created = client.post(
        "/api/projects",
        json={"name": "Alpha Project", "description": "First project"},
    ).json()

    # Get single project
    response = client.get(f"/api/projects/{created['id']}")
    assert response.status_code == 200
    single = response.json()
    assert single["id"] == created["id"]
    assert single["name"] == "Alpha Project"
    assert single["description"] == "First project"
    assert single["has_report"] is False

    # Get missing project
    missing = client.get("/api/projects/999999")
    assert missing.status_code == 404

    # List projects
    list_res = client.get("/api/projects")
    assert list_res.status_code == 200
    projects = list_res.json()["projects"]
    assert any(p["id"] == created["id"] for p in projects)
    matching = next(p for p in projects if p["id"] == created["id"])
    assert matching["name"] == "Alpha Project"
    assert matching["description"] == "First project"
    assert "updated_at" in matching


def test_update_project(tmp_path):
    client, _ = make_client(tmp_path)
    created = client.post(
        "/api/projects",
        json={"name": "Beta Project", "description": "Original description"},
    ).json()

    # Update name and description
    updated = client.patch(
        f"/api/projects/{created['id']}",
        json={"name": "Beta Project Renamed", "description": "Updated description"},
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["name"] == "Beta Project Renamed"
    assert body["description"] == "Updated description"

    # Verify via get
    get_res = client.get(f"/api/projects/{created['id']}")
    assert get_res.json()["name"] == "Beta Project Renamed"

    # Update missing project
    assert client.patch("/api/projects/999999", json={"name": "X"}).status_code == 404

    # Invalid update (empty name)
    invalid = client.patch(f"/api/projects/{created['id']}", json={"name": "  "})
    assert invalid.status_code in (400, 422)


def test_delete_project_and_unlinks_sessions(tmp_path):
    client, store = make_client(tmp_path)
    created = client.post(
        "/api/projects",
        json={"name": "Gamma Project", "description": "To be deleted"},
    ).json()
    proj_id = created["id"]

    # Link demo session to this project
    sessions = client.get("/api/sessions").json()["sessions"]
    if sessions:
        session_name = sessions[0]["name"]
        sess = store.get_session(session_name)
        store.save_session(
            session_name,
            sess.management_state,
            sess.work_schedule,
            project_id=proj_id,
        )
        assert store.get_session(session_name).project_id == proj_id

    # Delete project
    del_res = client.delete(f"/api/projects/{proj_id}")
    assert del_res.status_code == 204

    # Verify project is gone
    assert client.get(f"/api/projects/{proj_id}").status_code == 404

    # Delete missing project
    assert client.delete(f"/api/projects/{proj_id}").status_code == 404

    # Verify session unlinked (project_id became None) rather than crashing or deleting session
    if sessions:
        sess_after = store.get_session(session_name)
        assert sess_after.project_id is None


def test_project_persistence_across_restarts(tmp_path):
    db_file = tmp_path / "persistent.db"
    store1 = SqliteStore(db_file)
    client1 = TestClient(create_app(store1))

    created = client1.post(
        "/api/projects",
        json={"name": "Persistent Project", "description": "Survives restart"},
    ).json()
    project_id = created["id"]

    # Simulate restart by creating a new store and app instance pointing to the same DB file
    store2 = SqliteStore(db_file)
    client2 = TestClient(create_app(store2))

    res = client2.get(f"/api/projects/{project_id}")
    assert res.status_code == 200
    assert res.json()["name"] == "Persistent Project"
    assert res.json()["description"] == "Survives restart"
