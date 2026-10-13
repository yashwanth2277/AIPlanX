import pytest
from schemas.employee import Employee
from schemas.project_plan import Task
from utils.skill_matcher import calculate_skill_match


def make_employee(skills):
    return Employee(
        employee_id="EMP001",
        employee_name="Rahul",
        role="Developer",
        skills=skills,
        experience=3,
        current_workload_percent=20,
        weekly_capacity_hours=40,
    )


def make_task(required_skills):
    return Task(
        task_id=1,
        title="Build API",
        description="Build the backend API",
        required_skills=required_skills,
        estimated_hours=8,
        priority="High",
        dependencies=[],
    )


def test_matches_postgres_with_postgresql():
    task = make_task(["PostgreSQL"])
    employee = make_employee(["Postgres"])

    assert calculate_skill_match(task, employee) == 1.0


def test_matches_javascript_alias():
    task = make_task(["JavaScript"])
    employee = make_employee(["JS"])

    assert calculate_skill_match(task, employee) == 1.0


def test_matches_multiple_aliases():
    task = make_task(["Python", "React"])
    employee = make_employee(["Py", "React.js"])

    assert calculate_skill_match(task, employee) == 1.0


def test_partial_skill_match():
    task = make_task(["Python", "FastAPI"])
    employee = make_employee(["Python"])

    assert calculate_skill_match(task, employee) == 0.5



def test_rejects_task_without_required_skills():
    with pytest.raises(
        ValueError,
        match="must have at least one required skill",
    ):
        make_task([])