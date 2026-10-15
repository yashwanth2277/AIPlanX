
from schemas.project_plan import ProjectPlan, Task
from schemas.assignment import TaskAssignment
from schemas.project_management import TaskStatus
from utils.management_initializer import initialize_management_state


def test_planned_tasks_initialize_with_assignments_and_pending_progress():
    plan = ProjectPlan(
        project_name="Demo",
        project_summary="Demo project",
        total_estimated_hours=8,
        tasks=[
            Task(
                task_id=1,
                title="Build API",
                description="Create API",
                required_skills=["Python"],
                estimated_hours=4,
                priority="high",
                dependencies=[],
            ),
            Task(
                task_id=2,
                title="Build UI",
                description="Create UI",
                required_skills=["JavaScript"],
                estimated_hours=4,
                priority="medium",
                dependencies=[1],
            ),
        ],
        risks=[],
    )

    assignments = [
        TaskAssignment(
            task_id=1,
            task_title="Build API",
            employee_id="E1",
            employee_name="Alice",
            match_score=0.9,
            assignment_reason="Matched Python skills",
        )
    ]

    management_state = initialize_management_state(
        plan=plan,
        assignments=assignments,
    )

    # Every planned task must have a progress record.
    assert len(management_state.task_progress) == 2

    progress_by_id = {
        progress.task_id: progress
        for progress in management_state.task_progress
    }

    assert set(progress_by_id) == {1, 2}

    # All tasks start with clean progress.
    for progress in progress_by_id.values():
        assert progress.status == TaskStatus.PENDING
        assert progress.progress_percent == 0
        assert progress.actual_hours_spent == 0

    # Actual assignments are preserved.
    assert len(management_state.assignments) == 1
    assert management_state.assignments[0].task_id == 1
    assert management_state.assignments[0].employee_id == "E1"

    # New management sessions start without assignment history.
    assert management_state.assignment_changes == []
