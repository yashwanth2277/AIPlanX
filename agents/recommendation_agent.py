
import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

from schemas.project_plan import ProjectPlan
from schemas.risk_analysis import RiskAnalysis
from schemas.progress_tracking import ProgressReport
from schemas.recommendations import RecommendationReport

load_dotenv()

if not os.getenv("GROQ_API_KEY"):
    raise ValueError("GROQ_API_KEY is missing from .env")

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0,
)


def generate_recommendations(
    plan: ProjectPlan,
    risk_analysis: RiskAnalysis,
    progress_report: ProgressReport,
) -> RecommendationReport:
    structured_llm = llm.with_structured_output(RecommendationReport)

    result = structured_llm.invoke(
        f"""
        You are an experienced project improvement advisor.

        Analyze the following project information.

        PROJECT PLAN:
        {plan.model_dump_json(indent=2)}

        RISK ANALYSIS:
        {risk_analysis.model_dump_json(indent=2)}

        PROGRESS REPORT:
        {progress_report.model_dump_json(indent=2)}

        Requirements:
        - Provide at least 3 specific, actionable recommendations.
        - Assign unique integer recommendation IDs starting from 1.
        - Set priority to High, Medium, or Low.
        - Explain the expected benefit of each recommendation.
        - Address significant risks, delays, blockers, and workload issues.
        - Avoid generic advice when a specific action can be recommended.
        - Include a concise summary.
        """
    )

    result.project_name = plan.project_name
    return result