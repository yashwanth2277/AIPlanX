from schemas.assignment import AssignmentReport
from schemas.employee import Employee
from schemas.project_plan import ProjectPlan
from schemas.resource_allocation import ResourceAllocation
from schemas.team_workflow import (
    TeamWorkflow,
    TeamWorkflowEdge,
    TeamWorkflowNode,
)


def build_team_workflow(
    plan: ProjectPlan,
    employees: list[Employee] | None = None,
    assignments: AssignmentReport | None = None,
    resource_allocation: ResourceAllocation | None = None,
) -> TeamWorkflow:
    """Build a role-based or employee-based project workflow."""

    employee_map = {
        employee.employee_id: employee
        for employee in (employees or [])
    }
    assignment_map = {
        assignment.task_id: assignment
        for assignment in (assignments.assignments if assignments else [])
    }
    resource_map = {
        assignment.task_id: assignment
        for assignment in (
            resource_allocation.assignments if resource_allocation else []
        )
    }

    employee_mode = bool(employee_map and assignment_map)

    nodes_by_id: dict[str, TeamWorkflowNode] = {}
    edges_by_key: dict[tuple[str, str, str], TeamWorkflowEdge] = {}

    def add_node(node: TeamWorkflowNode) -> None:
        existing = nodes_by_id.get(node.node_id)

        if existing is None:
            nodes_by_id[node.node_id] = node
            return

        existing.skills = sorted(
            set(existing.skills) | set(node.skills),
            key=str.casefold,
        )
        existing.task_ids = sorted(
            set(existing.task_ids) | set(node.task_ids)
        )

        if node.description and node.description not in existing.description:
            existing.description = (
                f"{existing.description}; {node.description}"
                if existing.description
                else node.description
            )

    def add_edge(
        source: str,
        target: str,
        relationship: str,
    ) -> None:
        key = (source, target, relationship)
        edges_by_key[key] = TeamWorkflowEdge(
            source=source,
            target=target,
            relationship=relationship,
        )

    for task in plan.tasks:
        task_node_id = f"task_{task.task_id}"

        add_node(
            TeamWorkflowNode(
                node_id=task_node_id,
                node_type="task",
                title=task.title,
                description=task.description,
                skills=task.required_skills,
                task_ids=[task.task_id],
            )
        )

        for dependency_id in task.dependencies:
            add_edge(
                f"task_{dependency_id}",
                task_node_id,
                "depends_on",
            )

        assignment = assignment_map.get(task.task_id)
        employee = (
            employee_map.get(assignment.employee_id)
            if employee_mode and assignment is not None
            else None
        )

        resource = resource_map.get(task.task_id)

        if employee is not None:
            role_title = employee.role
            role_description = f"Responsibilities include: {task.title}"
        elif resource is not None:
            role_title = resource.recommended_role
            role_description = (
                f"Responsibilities include: {task.title}. "
                f"{resource.notes}"
            )
        else:
            role_title = _recommend_role(task.required_skills)
            role_description = f"Responsibilities include: {task.title}"

        role_id = f"role_{_slug(role_title)}"

        add_node(
            TeamWorkflowNode(
                node_id=role_id,
                node_type="role",
                title=role_title,
                description=role_description,
                skills=(
                    resource.required_skills
                    if resource is not None
                    else task.required_skills
                ),
                task_ids=[task.task_id],
            )
        )

        if employee is not None:
            employee_node_id = f"employee_{_slug(employee.employee_id)}"

            add_node(
                TeamWorkflowNode(
                    node_id=employee_node_id,
                    node_type="employee",
                    title=employee.employee_name,
                    description=employee.role,
                    skills=employee.skills,
                    task_ids=[task.task_id],
                    employee_id=employee.employee_id,
                    employee_name=employee.employee_name,
                )
            )

            add_edge(employee_node_id, role_id, "performs")

        add_edge(role_id, task_node_id, "performs")

    return TeamWorkflow(
        project_name=plan.project_name,
        mode="employee_based" if employee_mode else "role_based",
        nodes=list(nodes_by_id.values()),
        edges=list(edges_by_key.values()),
    )


def _slug(value: str) -> str:
    return "".join(
        character.lower() if character.isalnum() else "_"
        for character in value
    ).strip("_")


def _recommend_role(skills: list[str]) -> str:
    normalized = {
        skill.strip().casefold()
        for skill in skills
        if skill.strip()
    }

    role_rules = [
        (
            {"react", "javascript", "html", "css", "tailwind"},
            "Frontend Developer",
        ),
        (
            {"python", "fastapi", "django", "flask", "rest api"},
            "Backend Developer",
        ),
        (
            {"sql", "postgresql", "mysql", "database"},
            "Database Engineer",
        ),
        (
            {"testing", "pytest", "automation", "qa", "unit testing"},
            "QA Engineer",
        ),
        (
            {"docker", "kubernetes", "deployment", "ci/cd"},
            "DevOps Engineer",
        ),
        (
            {"machine learning", "pytorch", "tensorflow", "scikit-learn"},
            "ML Engineer",
        ),
    ]

    for matched_skills, role in role_rules:
        if normalized & matched_skills:
            return role

    return "Software Engineer"