import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from schemas.task_breakdown import TaskBreakdown, Subtask

load_dotenv()

if not os.getenv("GROQ_API_KEY"):
    raise ValueError("GROQ_API_KEY is missing from .env")

llm = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0,
)


class TaskBreakdownDraft(BaseModel):
    """LLM output schema without the final hours-total validator."""

    subtasks: list[Subtask] = Field(min_length=3, max_length=7)


def break_down_task(
    task_id: int,
    task_title: str,
    task_description: str,
    parent_estimated_hours: float,
) -> TaskBreakdown:
    structured_llm = llm.with_structured_output(TaskBreakdownDraft)

    draft = structured_llm.invoke(
        f"""
        You are an expert task breakdown assistant.

        Break the following project task into smaller, actionable subtasks.

        Task ID: {task_id}
        Task title: {task_title}
        Task description: {task_description}
        Parent task estimated hours: {parent_estimated_hours}

        Requirements:
        - Return 3 to 7 practical subtasks.
        - Use unique integer subtask IDs starting from 1.
        - Give every subtask a clear title and description.
        - Every subtask estimate must be greater than zero.
        - Make the estimates add up to exactly
          {parent_estimated_hours} hours.
        - Distribute the hours realistically.
        - Do not change the parent task's total hours.
        """
    )

    subtasks = draft.subtasks

    # Scale the generated estimates to the authoritative parent budget.
    original_total = sum(
        subtask.estimated_hours for subtask in subtasks
    )

    if original_total <= 0:
        raise ValueError("Generated subtask hours must have a positive total.")

    normalized_subtasks = []
    allocated_hours = 0.0

    for subtask in subtasks[:-1]:
        normalized_hours = (
            subtask.estimated_hours
            / original_total
            * parent_estimated_hours
        )

        normalized_subtasks.append(
            subtask.model_copy(
                update={"estimated_hours": normalized_hours}
            )
        )
        allocated_hours += normalized_hours

    # Use the remaining budget for the final subtask to avoid rounding drift.
    last_subtask = subtasks[-1]
    remaining_hours = parent_estimated_hours - allocated_hours

    if remaining_hours <= 0:
        raise ValueError(
            "Could not distribute the parent task's hours across subtasks."
        )

    normalized_subtasks.append(
        last_subtask.model_copy(
            update={"estimated_hours": remaining_hours}
        )
    )

    # Final strict validation remains enabled.
    return TaskBreakdown(
        task_id=task_id,
        task_title=task_title,
        parent_estimated_hours=parent_estimated_hours,
        subtasks=normalized_subtasks,
    )