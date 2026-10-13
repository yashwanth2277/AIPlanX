
from schemas.employee import Employee
from schemas.project_plan import Task


SKILL_ALIASES = {
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "js": "javascript",
    "javascript": "javascript",
    "py": "python",
    "python": "python",
    "react.js": "react",
    "reactjs": "react",
    "react": "react",
    "node.js": "nodejs",
    "nodejs": "nodejs",
}


def normalize_skill(skill: str) -> str:
    normalized = skill.strip().casefold()
    return SKILL_ALIASES.get(normalized, normalized)


def calculate_skill_match(
    task: Task,
    employee: Employee,
) -> float:
    """
    Return the fraction of required task skills matched
    by the employee, between 0.0 and 1.0.
    """
    required_skills = {
        normalize_skill(skill)
        for skill in task.required_skills
        if skill.strip()
    }

    if not required_skills:
        return 0.0

    employee_skills = {
        normalize_skill(skill)
        for skill in employee.skills
        if skill.strip()
    }

    matched_skills = required_skills & employee_skills

    return len(matched_skills) / len(required_skills)
