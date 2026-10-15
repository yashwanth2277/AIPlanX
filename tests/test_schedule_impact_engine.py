
import pytest

from schemas.project_plan import ProjectPlan
from schemas.work_schedule import ScheduledTask, WorkSchedule
from utils.schedule_impact_engine import calculate_schedule_impact
from schemas.project_plan import ProjectPlan
from schemas.work_schedule import ScheduledTask, WorkSchedule
from utils.schedule_impact_engine import calculate_schedule_impact


@pytest.fixture
def project_data():
    plan = ProjectPlan(
        project_name="Demo Project",
        project_summary="Schedule impact test",
        total_estimated_hours=12,
        tasks=[
            {
                "task_id": 1,
                "title": "Design",
                "description": "Design the system",
                "required_skills": ["Design"],
                "estimated_hours": 4,
                "priority": "High",
                "dependencies": [],
            },
            {
                "task_id": 2,
                "title": "Build API",
                "description": "Build the API",
                "required_skills": ["Python"],
                "estimated_hours": 4,
                "priority": "High",
                "dependencies": [1],
            },
            {
                "task_id": 3,
                "title": "Build UI",
                "description": "Build the UI",
                "required_skills": ["React"],
                "estimated_hours": 4,
                "priority": "Medium",
                "dependencies": [2],
            },
        ],
    )

    schedule = WorkSchedule(
        scheduled_tasks=[
            ScheduledTask(
                task_id=1,
                task_title="Design",
                employee_id="E1",
                employee_name="Alice",
                total_estimated_hours=4,
                weekly_allocations=[{"week": 1, "allocated_hours": 4}],
                start_week=1,
                completion_week=1,
                assignment_reason="Design skills",
            ),
            ScheduledTask(
                task_id=2,
                task_title="Build API",
                employee_id="E2",
                employee_name="Bob",
                total_estimated_hours=4,
                weekly_allocations=[{"week": 2, "allocated_hours": 4}],
                start_week=2,
                completion_week=2,
                assignment_reason="Python skills",
            ),
            ScheduledTask(
                task_id=3,
                task_title="Build UI",
                employee_id="E3",
                employee_name="Charlie",
                total_estimated_hours=4,
                weekly_allocations=[{"week": 3, "allocated_hours": 4}],
                start_week=3,
                completion_week=3,
                assignment_reason="React skills",
            ),
        ]
    )

    return plan, schedule


def test_delay_propagates_to_dependent_tasks(project_data):
    plan, schedule = project_data

    report = calculate_schedule_impact(
        plan, schedule, delayed_task_id=1, delay_weeks=2
    )

    revised = {
        task.task_id: task
        for task in report.affected_tasks
    }

    assert revised[1].revised_completion_week == 3
    assert revised[2].revised_start_week == 4
    assert revised[2].revised_completion_week == 4
    assert revised[3].revised_start_week == 5
    assert revised[3].revised_completion_week == 5

    assert report.original_project_completion_week == 3
    assert report.revised_project_completion_week == 5
    assert report.project_delay_weeks == 2


def test_negative_delay_is_rejected(project_data):
    plan, schedule = project_data

    with pytest.raises(ValueError, match="delay_weeks"):
        calculate_schedule_impact(
            plan, schedule, delayed_task_id=1, delay_weeks=-1
        )


def test_unknown_task_is_rejected(project_data):
    plan, schedule = project_data

    with pytest.raises(ValueError, match="Unknown task ID"):
        calculate_schedule_impact(
            plan, schedule, delayed_task_id=999, delay_weeks=1
        )



def test_unscheduled_tasks_are_reported_in_impact_notes(project_data):
    plan, schedule = project_data

    # Remove one scheduled task to simulate an incomplete schedule.
    removed_task_id = schedule.scheduled_tasks[-1].task_id
    schedule.scheduled_tasks.pop()

    # Pick a task that remains scheduled and has analyzable dependencies.
    delayed_task_id = schedule.scheduled_tasks[0].task_id

    report = calculate_schedule_impact(
        plan=plan,
        schedule=schedule,
        delayed_task_id=delayed_task_id,
        delay_weeks=1,
    )

    assert any(
        "Unscheduled tasks excluded from impact analysis" in note
        and str(removed_task_id) in note
        for note in report.notes
    )

    assert any(
        "not necessarily the complete project" in note
        for note in report.notes
    )


def test_original_schedule_is_unchanged(project_data):
    plan, schedule = project_data
    original_weeks = [
        (task.start_week, task.completion_week)
        for task in schedule.scheduled_tasks
    ]

    calculate_schedule_impact(
        plan, schedule, delayed_task_id=1, delay_weeks=1
    )

    assert [
        (task.start_week, task.completion_week)
        for task in schedule.scheduled_tasks
    ] == original_weeks

def test_zero_delay_does_not_change_schedule(project_data):
    plan, schedule = project_data

    report = calculate_schedule_impact(
        plan,
        schedule,
        delayed_task_id=1,
        delay_weeks=0,
    )

    assert report.project_delay_weeks == 0
    assert report.original_project_completion_week == 3
    assert report.revised_project_completion_week == 3
    assert report.affected_tasks == []


def test_independent_task_is_not_delayed():
    plan = ProjectPlan(
        project_name="Parallel Project",
        project_summary="Independent tasks",
        total_estimated_hours=8,
        tasks=[
            {
                "task_id": 1,
                "title": "Task A",
                "description": "First independent task",
                "required_skills": ["Python"],
                "estimated_hours": 4,
                "priority": "High",
                "dependencies": [],
            },
            {
                "task_id": 2,
                "title": "Task B",
                "description": "Second independent task",
                "required_skills": ["React"],
                "estimated_hours": 4,
                "priority": "High",
                "dependencies": [],
            },
        ],
    )

    schedule = WorkSchedule(
        scheduled_tasks=[
            ScheduledTask(
                task_id=1,
                task_title="Task A",
                employee_id="E1",
                employee_name="Alice",
                total_estimated_hours=4,
                weekly_allocations=[{"week": 1, "allocated_hours": 4}],
                start_week=1,
                completion_week=1,
                assignment_reason="Python skills",
            ),
            ScheduledTask(
                task_id=2,
                task_title="Task B",
                employee_id="E2",
                employee_name="Bob",
                total_estimated_hours=4,
                weekly_allocations=[{"week": 1, "allocated_hours": 4}],
                start_week=1,
                completion_week=1,
                assignment_reason="React skills",
            ),
        ]
    )

    report = calculate_schedule_impact(
        plan, schedule, delayed_task_id=1, delay_weeks=2
    )

    revised = {task.task_id: task for task in report.affected_tasks}

    assert revised[1].revised_completion_week == 3
    assert 2 not in revised
    assert report.revised_project_completion_week == 3


def test_task_with_multiple_dependencies():
    plan = ProjectPlan(
        project_name="Multi Dependency Project",
        project_summary="A task depends on two prerequisites",
        total_estimated_hours=12,
        tasks=[
            {
                "task_id": 1,
                "title": "Prerequisite A",
                "description": "First prerequisite",
                "required_skills": ["Python"],
                "estimated_hours": 4,
                "priority": "High",
                "dependencies": [],
            },
            {
                "task_id": 2,
                "title": "Prerequisite B",
                "description": "Second prerequisite",
                "required_skills": ["React"],
                "estimated_hours": 4,
                "priority": "High",
                "dependencies": [],
            },
            {
                "task_id": 3,
                "title": "Integration",
                "description": "Requires both prerequisites",
                "required_skills": ["Python"],
                "estimated_hours": 4,
                "priority": "High",
                "dependencies": [1, 2],
            },
        ],
    )

    schedule = WorkSchedule(
        scheduled_tasks=[
            ScheduledTask(
                task_id=1,
                task_title="Prerequisite A",
                employee_id="E1",
                employee_name="Alice",
                total_estimated_hours=4,
                weekly_allocations=[{"week": 1, "allocated_hours": 4}],
                start_week=1,
                completion_week=1,
                assignment_reason="Python skills",
            ),
            ScheduledTask(
                task_id=2,
                task_title="Prerequisite B",
                employee_id="E2",
                employee_name="Bob",
                total_estimated_hours=4,
                weekly_allocations=[
                    {"week": 1, "allocated_hours": 4},
                    {"week": 2, "allocated_hours": 0.01},
                ],
                start_week=1,
                completion_week=2,
                assignment_reason="React skills",
            ),
            ScheduledTask(
                task_id=3,
                task_title="Integration",
                employee_id="E1",
                employee_name="Alice",
                total_estimated_hours=4,
                weekly_allocations=[{"week": 3, "allocated_hours": 4}],
                start_week=3,
                completion_week=3,
                assignment_reason="Python skills",
            ),
        ]
    )

    report = calculate_schedule_impact(
        plan, schedule, delayed_task_id=1, delay_weeks=2
    )

    revised = {task.task_id: task for task in report.affected_tasks}

    # Prerequisite B still finishes in week 2, so integration
    # must wait for the later prerequisite.
    assert revised[3].revised_start_week == 4
    assert revised[3].revised_completion_week == 4
    assert report.revised_project_completion_week == 4
