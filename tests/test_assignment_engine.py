
from schemas.project_plan import ProjectPlan, Task
from schemas.employee import Employee
from utils.assignment_engine import assign_tasks
import pytest


def make_employee(
    employee_id="EMP001",
    name="Rahul",
    skills=None,
    workload=40,
    capacity=40,
):
    return Employee(
        employee_id=employee_id,
        employee_name=name,
        role="Developer",
        skills=skills or ["Python", "FastAPI"],
        experience=3,
        current_workload_percent=workload,
        weekly_capacity_hours=capacity,
    )


def make_plan(tasks):
    return ProjectPlan.model_validate({
        "project_name": "Test Project",
        "project_summary": "Assignment engine tests",
        "total_estimated_hours": sum(
            task.estimated_hours for task in tasks
        ),
        "tasks": [
            task.model_dump() for task in tasks
        ],
    })


def make_task(
    task_id=1,
    hours=8,
    skills=None,
    dependencies=None,
):
    return Task(
        task_id=task_id,
        title="Build backend",
        description="Build the backend API",
        required_skills=skills or ["Python", "FastAPI"],
        estimated_hours=hours,
        priority="High",
        dependencies=dependencies or [],
    )


def test_assigns_employee_with_all_required_skills():
    report = assign_tasks(
        make_plan([make_task()]),
        [make_employee()],
    )

    assert len(report.assignments) == 1
    assert report.assignments[0].employee_name == "Rahul"
    assert report.assignments[0].match_score > 0
    assert len(report.unassigned_tasks) == 0



def test_allows_partial_skill_match_and_explains_gap():
    employee = make_employee(skills=["Python"])

    report = assign_tasks(
        make_plan([
            make_task(skills=["Python", "FastAPI"])
        ]),
        [employee],
    )

    assert len(report.assignments) == 1
    assert report.assignments[0].match_score > 0
    reason = report.assignments[0].assignment_reason

    assert "python" in reason
    assert "fastapi" in reason
    assert "50%" in reason
    assert len(report.unassigned_tasks) == 0


def test_does_not_exceed_weekly_capacity():
    employee = make_employee(workload=40, capacity=40)

    report = assign_tasks(
        make_plan([
            make_task(task_id=1, hours=18),
            make_task(task_id=2, hours=12),
        ]),
        [employee],
    )

    assert len(report.assignments) == 1
    assert len(report.unassigned_tasks) == 1
    assert report.assignments[0].task_id == 1


def test_employee_can_receive_multiple_tasks_within_capacity():
    employee = make_employee(workload=40, capacity=40)

    report = assign_tasks(
        make_plan([
            make_task(task_id=1, hours=8),
            make_task(task_id=2, hours=8),
        ]),
        [employee],
    )

    assert len(report.assignments) == 2
    assert len(report.unassigned_tasks) == 0
    assert {
        assignment.employee_id
        for assignment in report.assignments
    } == {"EMP001"}

def test_assigns_dependent_tasks_in_valid_order():
    employee = make_employee()

    plan = make_plan([
        make_task(
            task_id=2,
            hours=4,
            dependencies=[1],
        ),
        make_task(
            task_id=1,
            hours=4,
            dependencies=[],
        ),
    ])

    report = assign_tasks(plan, [employee])

    assert len(report.assignments) == 2
    assert len(report.unassigned_tasks) == 0

    assigned_ids = [
        assignment.task_id
        for assignment in report.assignments
    ]

    assert assigned_ids.index(1) < assigned_ids.index(2)

def test_rejects_circular_task_dependencies():
    with pytest.raises(
        ValueError,
        match="Task dependencies must not contain a cycle",
    ):
        make_plan([
            make_task(
                task_id=1,
                hours=4,
                dependencies=[2],
            ),
            make_task(
                task_id=2,
                hours=4,
                dependencies=[1],
            ),
        ])

def test_project_plan_rejects_tasks_without_required_skills():
    from pydantic import ValidationError

    with pytest.raises(
        ValidationError,
        match="must have at least one required skill",
    ):
        ProjectPlan.model_validate({
            "project_name": "Test Project",
            "project_summary": "Missing skills test",
            "total_estimated_hours": 4,
            "tasks": [{
                "task_id": 1,
                "title": "Project Setup",
                "description": "Initialize the repository",
                "required_skills": [],
                "estimated_hours": 4,
                "priority": "High",
                "dependencies": [],
            }],
        })
