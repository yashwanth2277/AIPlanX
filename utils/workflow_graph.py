
import re

from schemas.team_workflow import TeamWorkflow


def _safe_label(value: str) -> str:
    """Escape text for Mermaid node labels."""
    value = value.replace("&", "&amp;")
    value = value.replace('"', "&quot;")
    value = value.replace("<", "&lt;")
    value = value.replace(">", "&gt;")
    value = re.sub(r"[\r\n]+", " ", value)
    value = value.replace("[", "(").replace("]", ")")
    value = value.replace("{", "(").replace("}", ")")
    value = value.replace("|", "/")
    return value.strip()


def render_mermaid(workflow: TeamWorkflow) -> str:
    """Render a TeamWorkflow as a Mermaid flowchart."""

    lines = [
        "flowchart TD",
        '    project(["' + _safe_label(workflow.project_name) + '"])',
    ]

    for node in workflow.nodes:
        label = _safe_label(node.title)

        if node.node_type == "role":
            skills = ", ".join(node.skills)
            if skills:
                label += "\\nSkills: " + _safe_label(skills)

            node_definition = f'{node.node_id}["{label}"]'

        elif node.node_type == "employee":
            node_definition = f'{node.node_id}(["{label}"])'

        else:
            node_definition = f'{node.node_id}("{label}")'

        lines.append(f"    {node_definition}")

    # Connect the project to task nodes.
    for node in workflow.nodes:
        if node.node_type == "task":
            lines.append(f"    project --> {node.node_id}")

    # Add dependency and responsibility relationships.
    for edge in workflow.edges:
        if edge.relationship == "depends_on":
            lines.append(
                f"    {edge.source} -->|depends on| {edge.target}"
            )
        elif edge.relationship == "performs":
            lines.append(
                f"    {edge.source} -->|performs| {edge.target}"
            )
        elif edge.relationship == "handoff":
            lines.append(
                f"    {edge.source} -->|handoff| {edge.target}"
            )

    lines.extend(
        [
            "",
            "    classDef role fill:#dbeafe,stroke:#2563eb,color:#1e3a8a",
            "    classDef employee fill:#dcfce7,stroke:#16a34a,color:#14532d",
            "    classDef task fill:#f3f4f6,stroke:#6b7280,color:#111827",
        ]
    )

    for node in workflow.nodes:
        if node.node_type in {"role", "employee", "task"}:
            lines.append(
                f"    class {node.node_id} {node.node_type}"
            )

    return "\n".join(lines) + "\n"
