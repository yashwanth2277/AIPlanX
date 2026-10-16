import json
import logging

from pydantic import ValidationError

from schemas.project_plan import ProjectPlan
from utils.groq_client import LazyChatGroq

logger = logging.getLogger(__name__)

llm = LazyChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0,
)

_PROMPT_TEMPLATE = """
Create a practical project plan for the following project:

{project_description}



Rules:
    - Generate 8 to 12 actionable tasks.
    - Give every task a unique integer task_id.
    - Include a short title and clear description.
    - Estimate positive hours for every task.
    - Set priority to High, Medium, or Low.

    - Add dependencies only when a task genuinely requires the
      output of another task before it can begin.
    - Every dependency must reference an existing task ID.
    - Do not create a single long dependency chain for convenience.
    - Allow independent tasks to run in parallel when practical.
    - Frontend development may start with mock data before the
      backend is complete.
    - Testing can begin on completed components before full integration.
    - Documentation can be developed alongside implementation.
    - Ensure the dependency graph contains no circular dependencies.

    - Identify 3 to 5 important project risks.
    - total_estimated_hours must equal the sum of all task hours.
    - Return data matching the ProjectPlan schema exactly.

    - Include a required_skills list for every task.
    - List 2 to 5 specific technical or professional skills needed
      to complete each task.
    - Use consistent skill names such as Python, FastAPI, React,
      SQL, Testing, and Machine Learning.
    - Never return an empty required_skills list.
    - Choose skills that directly match the task's work.
    - For project setup tasks, use relevant skills such as Git,
      GitHub, or Project Setup.
    - For database tasks, use SQL, PostgreSQL, or Database Design
      as appropriate.
    - For backend tasks, use Python, FastAPI, or API Design
      as appropriate.
    - For frontend tasks, use React, JavaScript, HTML, or CSS
      as appropriate.
    - For testing and deployment tasks, use Pytest, Docker,
      CI/CD, or Deployment as appropriate.

    """


def _fix_total_hours(raw: dict) -> dict:
    """Correct total_estimated_hours to match the sum of task hours.

    LLMs frequently return a rounded or incorrect total.  Fixing this before
    Pydantic construction avoids a ValidationError that would otherwise prevent
    the otherwise valid plan from being used.
    """
    tasks = raw.get("tasks") or []
    actual_total = sum(float(task.get("estimated_hours", 0)) for task in tasks)
    if actual_total > 0:
        raw["total_estimated_hours"] = actual_total
    return raw


def create_project_plan(project_description: str, *, max_retries: int = 2) -> ProjectPlan:
    """Invoke the LLM planner and return a validated ProjectPlan.

    Strategy:
    1. Request raw JSON from the LLM (bypassing Pydantic inline validation).
    2. Correct total_estimated_hours before construction (the model often
       returns a rounded figure that doesn't match the sum of task hours).
    3. If Pydantic still rejects the plan, send the error back to the LLM and
       retry (up to max_retries times).

    When the LLM mock returns a ProjectPlan directly (as in unit tests), the
    plan is returned as-is since it has already been validated.
    """
    # Use raw JSON to avoid inline validation that fires before we can fix the total.
    raw_llm = llm.with_structured_output(
        ProjectPlan.model_json_schema(),
        method="json_schema",
    )

    prompt = _PROMPT_TEMPLATE.format(project_description=project_description)
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        feedback = ""
        if last_error is not None:
            feedback = (
                f"\n\nPrevious attempt failed validation:\n{last_error}\n"
                "Correct the issues and try again.  "
                "Ensure total_estimated_hours equals the exact sum of all task estimated_hours.\n"
            )

        try:
            raw = raw_llm.invoke(prompt + feedback)
        except Exception as exc:
            logger.warning("Planner LLM call failed on attempt %d: %s", attempt, exc)
            last_error = exc
            continue

        # Support mocks that return a fully-constructed Pydantic model directly.
        if isinstance(raw, ProjectPlan):
            return raw

        if not isinstance(raw, dict):
            last_error = ValueError(f"Expected dict from LLM, got {type(raw).__name__}")
            continue

        # Fix the most common LLM mistake before validation.
        raw = _fix_total_hours(raw)

        try:
            plan = ProjectPlan.model_validate(raw)
            return plan
        except (ValidationError, ValueError) as exc:
            logger.warning(
                "ProjectPlan validation failed on attempt %d/%d: %s",
                attempt,
                max_retries,
                exc,
            )
            last_error = exc

    raise ValueError(
        f"Planner failed to produce a valid ProjectPlan after {max_retries} attempts. "
        f"Last error: {last_error}"
    )



if __name__ == "__main__":
    plan = create_project_plan(
        "Build a college issue reporting platform using React and FastAPI."
    )

    assert isinstance(plan, ProjectPlan)
    assert len(plan.tasks) > 0
    assert len({task.task_id for task in plan.tasks}) == len(plan.tasks)

    print("Planner validation passed!")
    print(f"Project: {plan.project_name}")
    print(f"Number of tasks: {len(plan.tasks)}")
    print(f"Estimated hours: {plan.total_estimated_hours}")