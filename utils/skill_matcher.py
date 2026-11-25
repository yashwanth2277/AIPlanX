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
    """Normalize skill name: lowercase, strip whitespace, and resolve common aliases."""
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


def check_skill_match_details(
    candidate_skills: list[str],
    task_required_skills: list[str],
    threshold: float = 0.5,
) -> tuple[bool, float, list[str], list[str]]:
    """
    Deterministically check if candidate qualifies for task required skills.

    Returns:
        (qualifies, match_ratio, matched_skills, required_skills)
        - qualifies: True if match_ratio >= threshold or if no skills required.
        - match_ratio: float between 0.0 and 1.0 (1.0 if no skills required).
        - matched_skills: sorted list of normalized matched skill names.
        - required_skills: sorted list of normalized required skill names.
    """
    req_set = {
        normalize_skill(s)
        for s in task_required_skills
        if s and normalize_skill(s)
    }
    if not req_set:
        return True, 1.0, [], []

    cand_set = {
        normalize_skill(s)
        for s in candidate_skills
        if s and normalize_skill(s)
    }
    matched = sorted(cand_set & req_set)
    ratio = len(matched) / len(req_set)
    qualifies = ratio >= threshold
    return qualifies, ratio, matched, sorted(req_set)


def qualifies_for_task(
    candidate_skills: list[str],
    task_required_skills: list[str],
    threshold: float = 0.5,
) -> bool:
    """Return True if candidate matches at least threshold (default 50%) of required skills."""
    qualifies, _, _, _ = check_skill_match_details(
        candidate_skills, task_required_skills, threshold
    )
    return qualifies
