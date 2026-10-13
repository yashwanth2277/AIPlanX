
import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

from schemas.project_plan import ProjectPlan
from schemas.resource_allocation import ResourceAllocation

load_dotenv()

if not os.getenv("GROQ_API_KEY"):
    raise ValueError("GROQ_API_KEY is missing from .env")

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0,
)


def allocate_resources(plan: ProjectPlan) -> ResourceAllocation:
    structured_llm = llm.with_structured_output(ResourceAllocation)

    result = structured_llm.invoke(
        f"""
        You are an experienced project resource planning assistant.

        Analyze this project plan:
        {plan.model_dump_json(indent=2)}

        Recommend the skills and roles needed for each task.

        Requirements:
        - Create one assignment for every task in the project plan.
        - Preserve each original task_id.
        - List relevant technical or professional skills.
        - Recommend a suitable role for each task.
        - Preserve the estimated effort hours for each task.
        - Do not invent real team members.
        - Include practical recommendations for workload distribution,
          skill coverage, and resource constraints.
        """
    )

    result.project_name = plan.project_name
    return result


if __name__ == "__main__":
    sample_plan = ProjectPlan(
        project_name="Student Task Manager",
        project_summary="A task management app built with Python.",
        total_estimated_hours=12,
        tasks=[
            {
                "task_id": 1,
                "title": "Design database",
                "description": "Design the task database.",
                "estimated_hours": 4,
                "priority": "High",
                "dependencies": [],
            },
            {
                "task_id": 2,
                "title": "Build API",
                "description": "Implement task management endpoints.",
                "estimated_hours": 8,
                "priority": "High",
                "dependencies": [1],
            },
        ],
    )

    allocation = allocate_resources(sample_plan)
    print(allocation.model_dump_json(indent=2))
