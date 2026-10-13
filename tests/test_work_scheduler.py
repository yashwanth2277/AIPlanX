
from schemas.assignment import AssignmentReport, TaskAssignment
from schemas.employee import Employee
from schemas.project_plan import ProjectPlan
from utils.work_scheduler import build_work_schedule


def test_task_spans_multiple_weeks():
    employee = Employee(
        employee_id="EMP001",
        employee_name="Rahul",
        role="Backend Developer",
        skills=["Python", "FastAPI", "API Design"],
        experience=3,
        current_workload_percent=40,
        weekly_capacity_hours=40,
    )

    plan = ProjectPlan.model_validate({
        "project_name": "Test Project",
        "project_summary": "Multi-week scheduling test",
        "total_estimated_hours": 30,
        "tasks": [{
            "task_id": 1,
            "title": "Build backend",
            "description": "Implement core endpoints",
            "required_skills": ["Python", "FastAPI", "API Design"],
            "estimated_hours": 30,
            "priority": "High",
            "dependencies": [],
        }],
    })

    assignments = AssignmentReport(
        assignments=[
            TaskAssignment(
                task_id=1,
                task_title="Build backend",
                employee_id="EMP001",
                employee_name="Rahul",
                match_score=0.9,
                assignment_reason="Strong backend skill match.",
            )
        ]
    )

    schedule = build_work_schedule(plan, [employee], assignments)

    assert len(schedule.scheduled_tasks) == 1
    task = schedule.scheduled_tasks[0]

    assert task.total_estimated_hours == 30
    assert sum(
        allocation.allocated_hours
        for allocation in task.weekly_allocations
    ) == 30
    assert task.start_week == 1
    assert task.completion_week == 2
    assert task.weekly_allocations[0].allocated_hours == 24
    assert task.weekly_allocations[1].allocated_hours == 6
