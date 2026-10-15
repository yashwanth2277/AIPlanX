
import pytest

from agents.management_workflow import build_management_workflow
from schemas.employee import Employee
from schemas.project_management import (
    ProjectManagementState,
    TaskProgress,
)
from schemas.project_plan import ProjectPlan
from schemas.work_schedule import ScheduledTask, WorkSchedule


@pytest.fixture
def integration_data():
    plan = ProjectPlan(
        project_name="Integration Demo",
        project_summary="Test delay analysis and rescheduling",
        total_estimated_hours=8,
        tasks=[
            {
                "task_id": 1,
                "title": "Build API",
                "description": "Implement the API",
                "required_skills": ["Python"],
                "estimated_hours": 4,
                "priority": "High",
                "dependencies": [],
            },
            {
                "task_id": 2,
                "title": "Build UI",
                "description": "Implement the UI",
                "required_skills": ["React"],
                "estimated_hours": 4,
                "priority": "High",
                "dependencies": [1],
            },
        ],
    )

    management_state = ProjectManagementState(
        plan=plan,
        task_progress=[
            TaskProgress(task_id=1),
            TaskProgress(task_id=2),
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
                    {"week": 2, "allocated_hours": 4}
                ],
                start_week=2,
                completion_week=2,
                assignment_reason="React skills",
            ),
        ]
    )

    return management_state, employees, schedule


def test_analyze_delay_returns_report_and_revised_schedule(
    integration_data,
):
    management_state, employees, schedule = integration_data

    workflow = build_management_workflow()

    result = workflow.invoke({
        "action": "analyze_delay",
        "management_state": management_state,
        "employees": employees,
        "work_schedule": schedule,
        "delay_task_id": 1,
        "delay_hours": 8.0,
        "delay_reason": "API dependency delayed",
        "delayed_task_id": 1,
        "delay_weeks": 2,
    })

    report = result["schedule_impact_report"]
    revised_schedule = result["work_schedule"]

    revised_tasks = {
        task.task_id: task
        for task in revised_schedule.scheduled_tasks
    }

    assert report.project_name == "Integration Demo"
    assert report.project_delay_weeks == 2
    assert report.revised_project_completion_week == 4

    assert revised_tasks[1].start_week == 3
    assert revised_tasks[1].completion_week == 3
    assert revised_tasks[2].start_week >= 4

    updated_progress = {
        item.task_id: item
        for item in result["management_state"].task_progress
    }

    assert len(updated_progress[1].delays) == 1
    assert updated_progress[1].delays[0].delay_hours == 8.0
    assert (
        updated_progress[1].delays[0].reason
        == "API dependency delayed"
    )


def test_analyze_delay_preserves_original_state_and_schedule(
    integration_data,
):
    management_state, employees, schedule = integration_data

    original_start_weeks = [
        task.start_week for task in schedule.scheduled_tasks
    ]

    workflow = build_management_workflow()

    result = workflow.invoke({
        "action": "analyze_delay",
        "management_state": management_state,
        "employees": employees,
        "work_schedule": schedule,
        "delay_task_id": 1,
        "delay_hours": 8.0,
        "delay_reason": "API dependency delayed",
        "delayed_task_id": 1,
        "delay_weeks": 2,
    })

    assert management_state.task_progress[0].delays == []
    assert [
        task.start_week for task in schedule.scheduled_tasks
    ] == original_start_weeks

    assert len(
        result["management_state"].task_progress[0].delays
    ) == 1


def test_analyze_delay_rejects_unknown_task(integration_data):
    management_state, employees, schedule = integration_data

    workflow = build_management_workflow()

    with pytest.raises(ValueError, match="Unknown task ID"):
        workflow.invoke({
            "action": "analyze_delay",
            "management_state": management_state,
            "employees": employees,
            "work_schedule": schedule,
            "delay_task_id": 999,
            "delay_hours": 8.0,
            "delay_reason": "Invalid task",
            "delayed_task_id": 999,
            "delay_weeks": 2,
        })

def test_analyze_delay_report_includes_recorded_delay_and_impact(
    integration_data,
):
    management_state, employees, schedule = integration_data

    workflow = build_management_workflow()

    # First analyze the delay.
    delay_result = workflow.invoke({
        "action": "analyze_delay",
        "management_state": management_state,
        "employees": employees,
        "work_schedule": schedule,
        "delay_task_id": 1,
        "delay_hours": 8.0,
        "delay_reason": "API dependency delayed",
        "delayed_task_id": 1,
        "delay_weeks": 2,
    })

    # Then generate a report using the updated state and schedule.
    report_result = workflow.invoke({
        "action": "generate_report",
        "management_state": delay_result["management_state"],
        "work_schedule": delay_result["work_schedule"],
        "schedule_impact_report": delay_result[
            "schedule_impact_report"
        ],
    })

    report = report_result["management_report"]

    assert report["project_name"] == "Integration Demo"
    assert report["progress"]["total_tasks"] == 2

    assert len(report["task_delays"]) == 1
    assert report["task_delays"][0]["task_id"] == 1
    assert report["task_delays"][0]["delay_hours"] == 8.0

    assert report["schedule_impact"]["project_delay_weeks"] == 2
    assert report["revised_completion_week"] == max(
        task.completion_week
        for task in delay_result["work_schedule"].scheduled_tasks
    )

    assert report["recommendations"]

def test_analyze_delay_does_not_apply_same_delay_twice(
    integration_data,
):
    management_state, employees, schedule = integration_data
    workflow = build_management_workflow()

    first_result = workflow.invoke({
        "action": "analyze_delay",
        "management_state": management_state,
        "employees": employees,
        "work_schedule": schedule,
        "delay_task_id": 1,
        "delay_hours": 8.0,
        "delay_reason": "API dependency delayed",
        "delayed_task_id": 1,
        "delay_weeks": 2,
    })

    first_schedule = first_result["work_schedule"]

    second_result = workflow.invoke({
        "action": "analyze_delay",
        "management_state": first_result["management_state"],
        "employees": employees,
        "work_schedule": first_schedule,
        "delayed_task_id": 1,
        "delay_weeks": 2,
    })

    first_tasks = {
        task.task_id: task
        for task in first_schedule.scheduled_tasks
    }
    second_tasks = {
        task.task_id: task
        for task in second_result["work_schedule"].scheduled_tasks
    }

    assert second_tasks[1].start_week == first_tasks[1].start_week
    assert (
        second_tasks[1].completion_week
        == first_tasks[1].completion_week
    )
    assert len(
        second_result["management_state"].task_progress[0].delays
    ) == 1
