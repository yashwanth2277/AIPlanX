from api.sqlite_store import SqliteStore
from schemas.final_report import FinalProjectReport


def test_sqlite_store_imports_employees_and_demo(tmp_path):
    store = SqliteStore(tmp_path / "aiplanx.db")
    store.import_demo_data()

    employees = store.list_employees()
    assert len(employees) == 6
    assert employees[0].employee_id == "EMP001"

    projects = store.list_projects()
    assert projects
    assert projects[0].final_report is not None
    assert isinstance(projects[0].final_report, FinalProjectReport)

    sessions = store.list_sessions()
    names = {item.name for item in sessions}
    assert "demo" in names
    demo = store.get_session("demo")
    assert demo.management_state.plan.tasks
    assert demo.work_schedule.scheduled_tasks


def test_sqlite_round_trip_preserves_assignments(tmp_path):
    store = SqliteStore(tmp_path / "aiplanx.db")
    store.import_demo_data()
    sessions = store.list_sessions()
    assert sessions
    original = store.get_session(sessions[0].name)
    saved = store.save_session(
        original.name,
        original.management_state,
        original.work_schedule,
        project_id=original.project_id,
    )
    assert len(saved.management_state.assignments) == len(
        original.management_state.assignments
    )
