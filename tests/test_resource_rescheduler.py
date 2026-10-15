
import pytest

from schemas.employee import Employee
from schemas.project_plan import ProjectPlan
from schemas.work_schedule import ScheduledTask, WorkSchedule
from utils.resource_rescheduler import reschedule_work_schedule


@pytest.fixture
def setup_data():
    plan = ProjectPlan(
        project_name="Demo",
        project_summary="Rescheduling test",
        total_estimated_hours=8,
        tasks=[
            {
                "task_id": 1,
                "title": "Build API",
                "description": "Implement API",
                "required_skills": ["Python"],
                "estimated_hours": 4,
                "priority": "High",
                "dependencies": [],
            },
            {
                "task_id": 2,
                "title": "Build UI",
                "description": "Implement UI",
                "required_skills": ["React"],
                "estimated_hours": 4,
                "priority": "High",
                "dependencies": [1],
            },
        ],
    )

    employees = [
        Employee(
            employee_id="E1",
            employee_name="Alice",
            role="Developer",
            skills=["Python"],
            experience=3,
            current_workload_percent=0,
            weekly_capacity_hours=8,
        ),
        Employee(
            employee_id="E2",
            employee_name="Bob",
            role="Developer",
            skills=["React"],
            experience=2,
            current_workload_percent=0,
            weekly_capacity_hours=8,
        ),
    ]

    schedule = WorkSchedule(
        scheduled_tasks=[
            ScheduledTask(
                task_id=1,
                task_title="Build API",
                employee_id="E1",
                employee_name="Alice",
                total_estimated_hours=4,
                weekly_allocations=[
                    {"week": 1, "allocated_hours": 4}
                ],
                start_week=1,
                completion_week=1,
                assignment_reason="Python skills",
            ),
            ScheduledTask(
                task_id=2,
                task_title="Build UI",
                employee_id="E2",
                employee_name="Bob",
                total_estimated_hours=4,
                weekly_allocations=[
                    {"week": 1, "allocated_hours": 4}
                ],
                start_week=1,
                completion_week=1,
                assignment_reason="React skills",
            ),
        ]
    )

    return plan, employees, schedule


def test_delay_reschedules_dependent_tasks(setup_data):
    plan, employees, schedule = setup_data

    revised = reschedule_work_schedule(
        plan, employees, schedule, delayed_task_id=1, delay_weeks=2
    )

    tasks = {task.task_id: task for task in revised.scheduled_tasks}

    assert tasks[1].start_week == 3
    assert tasks[1].completion_week == 3
    assert tasks[2].start_week >= tasks[1].completion_week


def test_original_schedule_is_unchanged(setup_data):
    plan, employees, schedule = setup_data
    original_start = [
        task.start_week for task in schedule.scheduled_tasks
    ]

    reschedule_work_schedule(
        plan, employees, schedule, delayed_task_id=1, delay_weeks=2
    )

    assert [
        task.start_week for task in schedule.scheduled_tasks
    ] == original_start


def test_negative_delay_is_rejected(setup_data):
    plan, employees, schedule = setup_data

    with pytest.raises(ValueError, match="delay_weeks"):
        reschedule_work_schedule(
            plan, employees, schedule, delayed_task_id=1, delay_weeks=-1
        )


def test_unknown_task_is_rejected(setup_data):
    plan, employees, schedule = setup_data

    with pytest.raises(ValueError, match="Unknown task ID"):
        reschedule_work_schedule(
            plan, employees, schedule, delayed_task_id=999, delay_weeks=1
        )


def test_weekly_capacity_is_respected(setup_data):
    plan, employees, schedule = setup_data

    revised = reschedule_work_schedule(
        plan, employees, schedule, delayed_task_id=1, delay_weeks=2
    )

    for task in revised.scheduled_tasks:
        employee = next(
            item for item in employees
            if item.employee_id == task.employee_id
        )

        for allocation in task.weekly_allocations:
            assert allocation.allocated_hours <= employee.weekly_capacity_hours

def test_unscheduled_tasks_are_preserved(setup_data):
    plan, employees, schedule = setup_data

    # Remove task 2 from the schedule while keeping it in the project plan.
    schedule.scheduled_tasks = [
        task for task in schedule.scheduled_tasks
        if task.task_id != 2
    ]
    schedule.unscheduled_tasks = [
        {"task_id": 2, "reason": "No available resource"}
    ]

    revised = reschedule_work_schedule(
        plan=plan,
        employees=employees,
        schedule=schedule,
        delayed_task_id=1,
        delay_weeks=2,
    )

    assert [task.task_id for task in revised.scheduled_tasks] == [1]
    assert any(
        item.get("task_id") == 2
        for item in revised.unscheduled_tasks
    )
