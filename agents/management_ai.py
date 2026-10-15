
import json
import os

from dotenv import load_dotenv
from google import genai
from pydantic import ValidationError

from schemas.management_ai import ManagementAIInsights
from schemas.project_management import ProjectManagementState

load_dotenv()


def generate_management_insights(
    management_state: ProjectManagementState,
) -> ManagementAIInsights:
    """Generate AI insights from the current project management state."""

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY is missing from .env")

    client = genai.Client(api_key=api_key)

    project = management_state.plan

    task_progress = [
        {
            "task_id": progress.task_id,
            "status": progress.status.value,
            "progress_percent": progress.progress_percent,
            "actual_hours_spent": progress.actual_hours_spent,
            "delays": [
                {
                    "delay_hours": delay.delay_hours,
                    "reason": delay.reason,
                }
                for delay in progress.delays
            ],
        }
        for progress in management_state.task_progress
    ]

    task_data = [
        {
            "task_id": task.task_id,
            "title": task.title,
            "estimated_hours": task.estimated_hours,
            "dependencies": task.dependencies,
            "priority": task.priority,
        }
        for task in project.tasks
    ]

    prompt = f"""
    You are an expert project management analyst.

    Analyze the project data below and return a structured management
    assessment.

    Project:
    {json.dumps({
        "name": project.project_name,
        "summary": project.project_summary,
        "tasks": task_data,
        "progress": task_progress,
    }, indent=2)}

    Requirements:
    - Summarize the current project status.
    - Explain the significance of recorded delays.
    - Identify plausible risks grounded in the supplied data.
    - Recommend practical recovery actions.
    - Do not invent facts or claim a risk is certain without evidence.
    - If no delays are recorded, say so rather than inventing delay issues.
    - Return concise, actionable recommendations.
    """

    response = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": ManagementAIInsights,
        },
    )

    if not response.text:
        raise ValueError("Gemini returned an empty management assessment")

    try:
        return ManagementAIInsights.model_validate_json(response.text)
    except ValidationError as error:
        raise ValueError(
            "Gemini returned an invalid management assessment"
        ) from error
