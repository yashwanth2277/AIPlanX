
import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

from schemas.task_breakdown import TaskBreakdown

load_dotenv()

if not os.getenv("GROQ_API_KEY"):
    raise ValueError("GROQ_API_KEY is missing from .env")

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0,
)


def break_down_task(
    task_id: int,
    task_title: str,
    task_description: str,
    parent_estimated_hours: float,
) -> TaskBreakdown:
    structured_llm = llm.with_structured_output(TaskBreakdown)

    result = structured_llm.invoke(
        f"""
        You are an expert task breakdown assistant.

        Break the following project task into smaller, actionable subtasks.

        Task ID: {task_id}
        Task title: {task_title}
        Task description: {task_description}
        Parent task estimated hours: {parent_estimated_hours}

        Requirements:
        - Return 3 to 7 practical subtasks.
        - Assign each subtask a unique integer subtask_id, starting from 1.
        - Give every subtask a clear title and description.
        - Every subtask estimate must be greater than zero.
        - The SUM of all subtask estimated_hours MUST equal
          {parent_estimated_hours} hours.
        - Distribute the hour budget realistically across the subtasks.
        - Do not increase or decrease the parent task's total hours.
        - Keep all subtasks relevant to the original task.
        """
    )

    # Preserve the authoritative parent task information.
    result.task_id = task_id
    result.task_title = task_title
    result.parent_estimated_hours = parent_estimated_hours

    # Validate again after setting the authoritative values.
    result = TaskBreakdown.model_validate(result.model_dump())

    return result
