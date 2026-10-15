
from schemas.project_plan import ProjectPlan, Task
from schemas.project_management import (
    ProjectManagementState,
    TaskProgress,
    TaskStatus,
    DelayRecord,
)
from schemas.work_schedule import (
    WorkSchedule,
    ScheduledTask,
    WeeklyAllocation,
)
from utils.management_report_generator import generate_management_report


def create_management_state():
    plan = ProjectPlan(
        project_name="AIPlanX",
        project_summary="Live project management system",
        total_estimated_hours=15,
        tasks=[
            Task(
                task_id=1,
                title="Build backend",
                description="Implement backend APIs",
                required_skills=["Python"],
                estimated_hours=10,
                priority="High",
            ),
            Task(
                task_id=2,
                title="Build frontend",
                description="Implement frontend UI",
                required_skills=["React"],
                estimated_hours=5,
                priority="Medium",
                dependencies=[1],
            ),
        ],
    )

    management_state = ProjectManagementState(
        plan=plan,
        task_progress=[
            TaskProgress(
                task_id=1,
                status=TaskStatus.IN_PROGRESS,
                progress_percent=50,
                actual_hours_spent=5,
                delays=[
                    DelayRecord(
                        task_id=1,
                        delay_hours=3,
                        reason="Backend API integration delayed",
                    )
                ],
            ),
            TaskProgress(
                task_id=2,
                status=TaskStatus.PENDING,
                progress_percent=0,
                actual_hours_spent=0,
            ),
        ],
    )

    return management_state


def create_work_schedule():
    return WorkSchedule(
        scheduled_tasks=[
            ScheduledTask(
                task_id=1,
                task_title="Build backend",
                employee_id="E001",
                employee_name="Alex",
                total_estimated_hours=10,
                weekly_allocations=[
                    WeeklyAllocation(week=1, allocated_hours=10)
                ],
                start_week=1,
                completion_week=1,
                assignment_reason="Python skill match",
            ),
            ScheduledTask(
                task_id=2,
                task_title="Build frontend",
                employee_id="E002",
                employee_name="Sam",
                total_estimated_hours=5,
                weekly_allocations=[
                    WeeklyAllocation(week=2, allocated_hours=5)
                ],
                start_week=2,
                completion_week=2,
                assignment_reason="React skill match",
            ),
        ]
    )


def test_generates_report_with_task_status_counts():
    report = generate_management_report(
        management_state=create_management_state()
    )

    assert report.project_name == "AIPlanX"
    assert report.progress.total_tasks == 2
    assert report.progress.in_progress_tasks == 1
    assert report.progress.pending_tasks == 1
    assert report.progress.blocked_tasks == 0
    assert report.progress.completed_tasks == 0


def test_includes_recorded_task_delays():
    report = generate_management_report(
        management_state=create_management_state()
    )

    assert len(report.task_delays) == 1
    assert report.task_delays[0].task_id == 1
    assert report.task_delays[0].task_title == "Build backend"
    assert report.task_delays[0].delay_hours == 3
    assert report.task_delays[0].reason == (
        "Backend API integration delayed"
    )


def test_includes_schedule_completion_week():
    report = generate_management_report(
        management_state=create_management_state(),
        work_schedule=create_work_schedule(),
    )

    assert report.revised_completion_week == 2


def test_recommends_action_for_blocked_tasks():
    management_state = create_management_state()
    management_state.task_progress[0].status = TaskStatus.BLOCKED

    report = generate_management_report(
        management_state=management_state
    )

    assert any(
        "blocked tasks" in recommendation.lower()
        for recommendation in report.recommendations
    )


def test_returns_default_recommendation_when_no_issues():
    management_state = create_management_state()
    management_state.task_progress[0].delays = []

    report = generate_management_report(
        management_state=management_state
    )

    assert report.recommendations
    assert any(
        "continue monitoring" in recommendation.lower()
        for recommendation in report.recommendations
    )


def test_does_not_modify_original_management_state():
    management_state = create_management_state()
    original_progress = [
        record.model_dump(mode="json")
        for record in management_state.task_progress
    ]

    generate_management_report(
        management_state=management_state,
        work_schedule=create_work_schedule(),
    )

    assert [
        record.model_dump(mode="json")
        for record in management_state.task_progress
    ] == original_progress
