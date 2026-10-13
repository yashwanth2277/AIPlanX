
import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

from schemas.project_plan import ProjectPlan
from schemas.schedule import ProjectSchedule

load_dotenv()

if not os.getenv("GROQ_API_KEY"):
    raise ValueError("GROQ_API_KEY is missing from .env")

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0,
    max_retries=3,
)


def estimate_project_schedule(plan: ProjectPlan) -> ProjectSchedule:
    structured_llm = llm.with_structured_output(
    ProjectSchedule,
    method="json_schema",
)

    result = structured_llm.invoke(
        f"""
        You are an experienced project scheduling assistant.

        Create a realistic schedule for this project plan:
        {plan.model_dump_json(indent=2)}

        Requirements:
        - Use a project day as an 8-hour working day.
        - Schedule tasks according to their dependencies.
        - Tasks may overlap only when their dependencies allow it.
        - Set start_day and end_day as positive, one-based day numbers.
        - Ensure end_day is not earlier than start_day.
        - Include every task from the original plan.
        - Preserve each task's ID, title, estimated hours, and dependencies.
        - Identify the critical path as an ordered list of task IDs.
        - Set total_duration_days to cover the entire schedule.
        - Add concise scheduling notes about parallel work or bottlenecks.
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

    schedule = estimate_project_schedule(sample_plan)
    print(schedule.model_dump_json(indent=2))
