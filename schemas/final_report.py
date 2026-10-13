
from pydantic import BaseModel

from schemas.project_plan import ProjectPlan
from schemas.task_breakdown import TaskBreakdown
from schemas.risk_analysis import RiskAnalysis
from schemas.schedule import ProjectSchedule
from schemas.resource_allocation import ResourceAllocation
from schemas.progress_tracking import ProgressReport
from schemas.recommendations import RecommendationReport


class FinalProjectReport(BaseModel):
    project_plan: ProjectPlan
    task_breakdowns: list[TaskBreakdown]
    risk_analysis: RiskAnalysis
    schedule: ProjectSchedule
    resource_allocation: ResourceAllocation
    progress_report: ProgressReport
    recommendations: RecommendationReport
