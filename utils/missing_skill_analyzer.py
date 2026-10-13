from schemas.project_plan import ProjectPlan
from schemas.employee import Employee
from utils.skill_matcher import calculate_skill_match

MIN_SKILL_MATCH = 0.5


def recommend_role(required_skills: list[str]) -> str:
    skills = {skill.strip().casefold() for skill in required_skills}

    if {"aws", "deployment", "docker"} & skills:
        return "DevOps / Cloud Engineer"
    if {"documentation", "project management"} & skills:
        return "Technical Writer / Project Coordinator"
    if {"react", "javascript", "html", "css"} & skills:
        return "Frontend Developer"
    if {"python", "fastapi"} & skills:
        return "Backend Developer"
    if {"sql", "postgresql", "database design"} & skills:
        return "Database Engineer"

    return "Specialist matching the required skills"


def analyze_missing_skills(
    plan: ProjectPlan,
    employees: list[Employee],
    scheduled_task_ids: set[int],
    unscheduled_tasks: list[dict],
) -> dict:
    tasks_by_id = {task.task_id: task for task in plan.tasks}
    recommendations = []

    for item in unscheduled_tasks:
        task = tasks_by_id[item["task_id"]]

        blocked_dependencies = [
            dep for dep in task.dependencies
            if dep not in scheduled_task_ids
        ]

        if blocked_dependencies:
            recommendations.append({
                "task_id": task.task_id,
                "task_title": task.title,
                "status": "dependency_blocked",
                "reason": (
                    "Waiting for unscheduled prerequisite tasks: "
                    f"{blocked_dependencies}"
                ),
                "recommended_role": None,
                "required_skills": [],
                "estimated_hours": task.estimated_hours,
            })
            continue

        candidates = [
            employee for employee in employees
            if calculate_skill_match(task, employee) >= MIN_SKILL_MATCH
        ]

        if candidates:
            recommendations.append({
                "task_id": task.task_id,
                "task_title": task.title,
                "status": "capacity_issue",
                "reason": (
                    "Qualified candidates exist, but the task was not "
                    "scheduled. Review capacity and scheduling constraints."
                ),
                "recommended_role": None,
                "required_skills": [],
                "estimated_hours": task.estimated_hours,
                "potential_candidates": [
                    {
                        "employee_id": employee.employee_id,
                        "employee_name": employee.employee_name,
                        "skill_match": round(
                            calculate_skill_match(task, employee), 3
                        ),
                    }
                    for employee in candidates
                ],
            })
            continue

        recommendations.append({
            "task_id": task.task_id,
            "task_title": task.title,
            "status": "additional_employee_required",
            "reason": (
                "No employee meets the minimum "
                f"{MIN_SKILL_MATCH:.0%} skill-match threshold."
            ),
            "recommended_role": recommend_role(task.required_skills),
            "required_skills": task.required_skills,
            "estimated_hours": task.estimated_hours,
        })

    return {
        "project_name": plan.project_name,
        "minimum_skill_match": MIN_SKILL_MATCH,
        "recommendations": recommendations,
    }
