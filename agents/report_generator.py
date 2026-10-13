
from schemas.final_report import FinalProjectReport


def generate_final_report(state: dict) -> FinalProjectReport:
    """Combine all agent outputs into one project report."""
    return FinalProjectReport(
        project_plan=state["project_plan"],
        task_breakdowns=state["task_breakdowns"],
        risk_analysis=state["risk_analysis"],
        schedule=state["schedule"],
        resource_allocation=state["resource_allocation"],
        progress_report=state["progress_report"],
        recommendations=state["recommendations"],
    )
