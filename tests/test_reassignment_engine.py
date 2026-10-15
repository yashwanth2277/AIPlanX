
import pytest

from schemas.assignment import TaskAssignment
from schemas.employee import Employee, EmployeeRoster
from schemas.project_management import (
    ProjectManagementState,
    TaskProgress,
)
from schemas.project_plan import ProjectPlan
from utils.reassignment_engine import reassign_task


@pytest.fixture
def setup_data():
    plan = ProjectPlan(
        project_name="Demo",
        project_summary="Test project",
        total_estimated_hours=5,
        tasks=[
            {
                "task_id": 1,
                "title": "Build API",
                "description": "Implement API",
                "required_skills": ["Python"],
                "estimated_hours": 5,
                "priority": "High",
                "dependencies": [],
            }
        ],
    )

    roster = EmployeeRoster(
        employees=[
            {
                "employee_id": "E1",
                "employee_name": "Alice",
                "role": "Backend Developer",
                "skills": ["Python"],
                "experience": 3,
                "current_workload_percent": 20,
                "weekly_capacity_hours": 40,
            },
            {
                "employee_id": "E2",
                "employee_name": "Bob",
                "role": "Backend Developer",
                "skills": ["Python"],
                "experience": 4,
                "current_workload_percent": 30,
                "weekly_capacity_hours": 40,
            },
        ]
    )

    state = ProjectManagementState(
        plan=plan,
        task_progress=[TaskProgress(task_id=1)],
        assignments=[
            TaskAssignment(
                task_id=1,
                task_title="Build API",
                employee_id="E1",
                employee_name="Alice",
                match_score=0.9,
                assignment_reason="Best skill match",
            )
        ],
    )

    return state, roster


def test_successful_reassignment(setup_data):
    state, roster = setup_data

    updated = reassign_task(
        state,
        roster,
        task_id=1,
        new_employee_id="E2",
        reason="Alice is unavailable",
    )

    assignment = updated.assignments[0]

    assert assignment.employee_id == "E2"
    assert assignment.employee_name == "Bob"
    assert assignment.assignment_reason == "Reassigned: Alice is unavailable"


def test_reassignment_history_is_recorded(setup_data):
    state, roster = setup_data

    updated = reassign_task(
        state,
        roster,
        task_id=1,
        new_employee_id="E2",
        reason="Workload balancing",
    )

    change = updated.assignment_changes[0]

    assert change.task_id == 1
    assert change.previous_employee_id == "E1"
    assert change.new_employee_id == "E2"
    assert change.reason == "Workload balancing"


def test_original_state_is_unchanged(setup_data):
    state, roster = setup_data

    reassign_task(
        state,
        roster,
        task_id=1,
        new_employee_id="E2",
        reason="Rebalance workload",
    )

    assert state.assignments[0].employee_id == "E1"
    assert state.assignment_changes == []


def test_unknown_employee_is_rejected(setup_data):
    state, roster = setup_data

    with pytest.raises(ValueError, match="Unknown employee ID"):
        reassign_task(
            state,
            roster,
            task_id=1,
            new_employee_id="E999",
            reason="Reassignment test",
        )


def test_unknown_task_is_rejected(setup_data):
    state, roster = setup_data

    with pytest.raises(ValueError, match="Unknown task ID"):
        reassign_task(
            state,
            roster,
            task_id=999,
            new_employee_id="E2",
            reason="Reassignment test",
        )


def test_same_employee_reassignment_is_rejected(setup_data):
    state, roster = setup_data

    with pytest.raises(ValueError, match="already assigned"):
        reassign_task(
            state,
            roster,
            task_id=1,
            new_employee_id="E1",
            reason="Reassignment test",
        )

def test_reassignment_rejects_missing_skills(setup_data):
    state, roster = setup_data

    with pytest.raises(ValueError, match="lacks required skills"):
        reassign_task(
            state,
            roster,
            task_id=1,
            new_employee_id="E2",
            reason="Test missing skills",
        ) if False else reassign_task(
            state,
            EmployeeRoster(
                employees=[
                    Employee(
                        employee_id="E3",
                        employee_name="Charlie",
                        role="Designer",
                        skills=["Figma"],
                        experience=2,
                        current_workload_percent=10,
                        weekly_capacity_hours=40,
                    ),
                    *roster.employees,
                ]
            ),
            task_id=1,
            new_employee_id="E3",
            reason="Test missing skills",
        )


def test_reassignment_rejects_insufficient_capacity(setup_data):
    state, roster = setup_data

    limited_roster = EmployeeRoster(
        employees=[
            roster.employees[0],
            Employee(
                employee_id="E3",
                employee_name="Charlie",
                role="Backend Developer",
                skills=["Python"],
                experience=3,
                current_workload_percent=95,
                weekly_capacity_hours=40,
            ),
        ]
    )

    with pytest.raises(ValueError, match="Insufficient weekly capacity"):
        reassign_task(
            state,
            limited_roster,
            task_id=1,
            new_employee_id="E3",
            reason="Test insufficient capacity",
        )


def test_reassignment_rejects_blank_reason(setup_data):
    state, roster = setup_data

    with pytest.raises(ValueError, match="reason"):
        reassign_task(
            state,
            roster,
            task_id=1,
            new_employee_id="E2",
            reason="  ",
        )
