
import pytest

import run_management
from schemas.employee import Employee
from schemas.project_management import TaskStatus


def test_create_session_from_existing_report(tmp_path, monkeypatch):
    monkeypatch.setattr(
        run_management,
        "SESSION_DIR",
        tmp_path / "management_sessions",
    )

    state, schedule, employees = run_management.create_session("demo")

    assert state.plan.project_name
    assert len(state.task_progress) == len(state.plan.tasks)
    assert all(
        item.status == TaskStatus.PENDING
        for item in state.task_progress
    )

    state_path, schedule_path = run_management.session_paths("demo")
    assert state_path.is_file()
    assert schedule_path.is_file()


def test_resume_session_preserves_progress(tmp_path, monkeypatch):
    monkeypatch.setattr(
        run_management,
        "SESSION_DIR",
        tmp_path / "management_sessions",
    )

    original_state, _, _ = run_management.create_session("demo")

    progress = original_state.task_progress[0].model_copy(
        update={
            "status": TaskStatus.IN_PROGRESS,
            "progress_percent": 50,
            "actual_hours_spent": 3,
        }
    )

    updated_state = original_state.model_copy(
        update={
            "task_progress": [
                progress if item.task_id == progress.task_id else item
                for item in original_state.task_progress
            ]
        }
    )

    state_path, _ = run_management.session_paths("demo")
    run_management.save_management_state(updated_state, state_path)

    resumed_state, _, _ = run_management.resume_session("demo")

    restored = next(
        item
        for item in resumed_state.task_progress
        if item.task_id == progress.task_id
    )

    assert restored.status == TaskStatus.IN_PROGRESS
    assert restored.progress_percent == 50
    assert restored.actual_hours_spent == 3


def test_create_session_rejects_existing_session(tmp_path, monkeypatch):
    monkeypatch.setattr(
        run_management,
        "SESSION_DIR",
        tmp_path / "management_sessions",
    )

    run_management.create_session("demo")

    with pytest.raises(FileExistsError):
        run_management.create_session("demo")


@pytest.mark.parametrize(
    "invalid_name",
    ["../outside", ".", "..", "bad name", ""],
)
def test_session_paths_reject_invalid_names(invalid_name):
    with pytest.raises(ValueError):
        run_management.session_paths(invalid_name)


def test_reassignment_updates_management_state_and_schedule(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        run_management,
        "SESSION_DIR",
        tmp_path / "management_sessions",
    )

    state, schedule, employees = run_management.create_session("demo")

    # Find an assigned task that is also scheduled.
    scheduled_task_ids = {
        item.task_id for item in schedule.scheduled_tasks
    }

    assignment = next(
        (
            item
            for item in state.assignments
            if item.task_id in scheduled_task_ids
        ),
        None,
    )

    if assignment is None:
        pytest.skip("No assigned and scheduled task available")

    task = next(
        task
        for task in state.plan.tasks
        if task.task_id == assignment.task_id
    )

    # Create a controlled replacement with every required skill.
    replacement = Employee(
        employee_id="TEST_REPLACEMENT",
        employee_name="Test Replacement",
        role="Test Engineer",
        skills=list(task.required_skills),
        experience=3,
        current_workload_percent=0,
        weekly_capacity_hours=40,
    )

    test_employees = [
        *employees,
        replacement,
    ]

    from agents.management_workflow import build_management_workflow

    result = build_management_workflow().invoke(
        {
            "action": "reassign_task",
            "management_state": state,
            "employees": test_employees,
            "work_schedule": schedule,
            "reassign_task_id": assignment.task_id,
            "new_employee_id": replacement.employee_id,
            "reassignment_reason": "Regression test",
        }
    )

    updated_state = result["management_state"]

    updated_assignment = next(
        item
        for item in updated_state.assignments
        if item.task_id == assignment.task_id
    )

    assert updated_assignment.employee_id == replacement.employee_id
    assert updated_state.task_progress == state.task_progress

    # Verify that the scheduled employee also changes.
    updated_schedule = result["work_schedule"]

    updated_schedule_task = next(
        item
        for item in updated_schedule.scheduled_tasks
        if item.task_id == assignment.task_id
    )

    assert updated_schedule_task.employee_id == replacement.employee_id
    assert updated_schedule_task.employee_name == replacement.employee_name

    # Other scheduled tasks must remain unchanged.
    original_other_tasks = {
        item.task_id: item
        for item in schedule.scheduled_tasks
        if item.task_id != assignment.task_id
    }

    updated_other_tasks = {
        item.task_id: item
        for item in updated_schedule.scheduled_tasks
        if item.task_id != assignment.task_id
    }

    assert updated_other_tasks == original_other_tasks
    assert updated_schedule.unscheduled_tasks == schedule.unscheduled_tasks
