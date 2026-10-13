
import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

from schemas.project_plan import ProjectPlan
from schemas.risk_analysis import RiskAnalysis

load_dotenv()

if not os.getenv("GROQ_API_KEY"):
    raise ValueError("GROQ_API_KEY is missing from .env")

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0,
)


def analyze_project_risks(plan: ProjectPlan) -> RiskAnalysis:
    structured_llm = llm.with_structured_output(RiskAnalysis)

    result = structured_llm.invoke(
        f"""
        You are an experienced project risk analyst.

        Analyze this project plan and identify realistic risks.

        Project plan:
        {plan.model_dump_json(indent=2)}

        Requirements:
        - Identify at least 3 relevant project risks.
        - Assign each risk a unique integer risk_id, starting from 1.
        - Set severity to High, Medium, or Low.
        - Explain each risk clearly.
        - Provide a practical mitigation for every risk.
        - Assess the overall risk level as High, Medium, or Low.
        - Provide actionable project recommendations.
        - Consider dependencies, task estimates, schedule, and technical complexity.
        """
    )

    result.project_name = plan.project_name
    return result


if __name__ == "__main__":
    sample_plan = ProjectPlan(
        project_name="Student Task Manager",
        project_summary="A simple task management application built with Python.",
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

    analysis = analyze_project_risks(sample_plan)
    print(analysis.model_dump_json(indent=2))
