
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class TeamWorkflowNode(BaseModel):
    node_id: str = Field(min_length=1)
    node_type: Literal["task", "role", "employee"]
    title: str = Field(min_length=1)
    description: str = ""
    skills: list[str] = Field(default_factory=list)
    task_ids: list[int] = Field(default_factory=list)
    employee_id: str | None = None
    employee_name: str | None = None


class TeamWorkflowEdge(BaseModel):
    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    relationship: Literal[
        "depends_on",
        "performs",
        "handoff",
    ]


class TeamWorkflow(BaseModel):
    project_name: str
    mode: Literal["role_based", "employee_based"]
    nodes: list[TeamWorkflowNode] = Field(min_length=1)
    edges: list[TeamWorkflowEdge] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_graph(self):
        node_ids = [node.node_id for node in self.nodes]

        if len(node_ids) != len(set(node_ids)):
            raise ValueError("Workflow node IDs must be unique")

        known_ids = set(node_ids)

        for edge in self.edges:
            if edge.source not in known_ids:
                raise ValueError(
                    f"Unknown edge source: {edge.source}"
                )

            if edge.target not in known_ids:
                raise ValueError(
                    f"Unknown edge target: {edge.target}"
                )

            if edge.source == edge.target:
                raise ValueError(
                    "Workflow edges cannot connect a node to itself"
                )

        if self.mode == "role_based":
            if any(
                node.node_type == "employee"
                for node in self.nodes
            ):
                raise ValueError(
                    "Role-based workflows must not invent employees"
                )

        return self
