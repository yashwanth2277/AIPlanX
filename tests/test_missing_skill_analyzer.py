
from schemas.project_plan import ProjectPlan, Task
from schemas.employee import Employee
from utils.missing_skill_analyzer import analyze_missing_skills


def make_plan():
    return ProjectPlan(
        project_name="Demo Project",
        project_summary="Test employee recommendations",
        total_estimated_hours=20,
        tasks=[
            Task(
                task_id=1,
                title="Cloud Deployment",
                description="Deploy the application",
                required_skills=["Docker", "Deployment", "AWS"],
                estimated_hours=12,
                priority="High",
                dependencies=[],
            ),
            Task(
                task_id=2,
                title="Documentation",
                description="Document the application",
                required_skills=["Documentation", "Git"],
                estimated_hours=8,
                priority="Medium",
                dependencies=[1],
            ),
        ],
    )


def make_employee():
    return Employee(
        employee_id="EMP001",
        employee_name="Rahul",
        role="Backend Developer",
        skills=["Python", "FastAPI"],
        experience=3,
        current_workload_percent=40,
        weekly_capacity_hours=40,
    )


def test_missing_skills_recommend_new_employee():
    result = analyze_missing_skills(
        plan=make_plan(),
        employees=[make_employee()],
        scheduled_task_ids=set(),
        unscheduled_tasks=[
            {"task_id": 1, "reason": "No employee matches"}
        ],
    )

    recommendation = result["recommendations"][0]

    assert recommendation["status"] == "additional_employee_required"
    assert recommendation["recommended_role"] == "DevOps / Cloud Engineer"
    assert set(recommendation["required_skills"]) == {
        "Docker", "Deployment", "AWS"
    }
    assert recommendation["estimated_hours"] == 12


def test_unscheduled_task_with_qualified_employee_flags_capacity():
    plan = make_plan()
    employee = Employee(
        employee_id="EMP002",
        employee_name="Priya",
        role="DevOps Engineer",
        skills=["Docker", "Deployment", "AWS"],
        experience=4,
        current_workload_percent=50,
        weekly_capacity_hours=40,
    )

    result = analyze_missing_skills(
        plan=plan,
        employees=[employee],
        scheduled_task_ids=set(),
        unscheduled_tasks=[
            {"task_id": 1, "reason": "Insufficient schedulable capacity"}
        ],
    )

    recommendation = result["recommendations"][0]

    assert recommendation["status"] == "capacity_issue"
    assert recommendation["potential_candidates"][0]["employee_id"] == "EMP002"


def test_task_with_unscheduled_dependency_is_blocked():
    result = analyze_missing_skills(
        plan=make_plan(),
        employees=[make_employee()],
        scheduled_task_ids=set(),
        unscheduled_tasks=[
            {"task_id": 2, "reason": "Prerequisite not scheduled"}
        ],
    )

    recommendation = result["recommendations"][0]

    assert recommendation["status"] == "dependency_blocked"
    assert recommendation["recommended_role"] is None
    assert "1" in recommendation["reason"]
