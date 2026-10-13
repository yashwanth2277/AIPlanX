
from agents.report_generator import generate_final_report


def test_generate_final_report_requires_complete_state():
    state = {}

    try:
        generate_final_report(state)
        assert False, "Expected KeyError for missing state fields"
    except KeyError as exc:
        assert exc.args[0] == "project_plan"


from agents.report_generator import generate_final_report

from schemas.project_plan import ProjectPlan, Task
from schemas.task_breakdown import TaskBreakdown, Subtask
from schemas.risk_analysis import RiskAnalysis, ProjectRisk
from schemas.schedule import ProjectSchedule, ScheduledTask
from schemas.resource_allocation import ResourceAllocation, ResourceAssignment
from schemas.progress_tracking import ProgressReport, TaskProgress
from schemas.recommendations import RecommendationReport, Recommendation


def test_generate_final_report_requires_complete_state():
    state = {}

    try:
        generate_final_report(state)
        assert False, "Expected KeyError for missing state fields"
    except KeyError as exc:
        assert exc.args[0] == "project_plan"


def test_generate_final_report_combines_all_outputs():
    plan = ProjectPlan(
        project_name="Demo Project",
        project_summary="A test project",
        total_estimated_hours=4,
        tasks=[
            Task(
                task_id=1,
                title="Build API",
                description="Create an API",
                required_skills=["Python"],
                estimated_hours=4,
                priority="High",
                dependencies=[],

            )
        ],
    )

    state = {
        "project_plan": plan,

        "task_breakdowns": [
            TaskBreakdown(
                task_id=1,
                task_title="Build API",
                parent_estimated_hours=4,
                subtasks=[
                    Subtask(
                        subtask_id=1,
                        title="Create endpoint",
                        description="Implement the endpoint",
                        estimated_hours=4,
                    )
                ],
            )
        ],

        "risk_analysis": RiskAnalysis(
            project_name="Demo Project",
            overall_risk_level="Low",
            risks=[
                ProjectRisk(
                    risk_id=1,
                    title="Testing delay",
                    description="Testing may take longer",
                    severity="Low",
                    mitigation="Test early",
                )
            ],
            recommendations=["Start testing early"],
        ),
        "schedule": ProjectSchedule(
            project_name="Demo Project",
            total_duration_days=2,
            critical_path=[1],
            scheduled_tasks=[
                ScheduledTask(
                    task_id=1,
                    title="Build API",
                    estimated_hours=4,
                    start_day=1,
                    end_day=2,
                )
            ],
        ),
        "resource_allocation": ResourceAllocation(
            project_name="Demo Project",
            assignments=[
                ResourceAssignment(
                    task_id=1,
                    required_skills=["Python"],
                    recommended_role="Backend Developer",
                    estimated_effort_hours=4,
                    notes="One developer",
                )
            ],
            resource_recommendations=["Assign one backend developer"],
        ),
        "progress_report": ProgressReport(
            project_name="Demo Project",
            overall_progress_percentage=0,
            completed_tasks=0,
            pending_tasks=1,
            task_progress=[
                TaskProgress(
                    task_id=1,
                    task_title="Build API",
                    planned_hours=4,
                    actual_hours=0,
                    status="Pending",
                    progress_percentage=0,
                )
            ],
        ),
        "recommendations": RecommendationReport(
            project_name="Demo Project",
            recommendations=[
                Recommendation(
                    recommendation_id=1,
                    title="Test early",
                    description="Begin testing during development",
                    priority="High",
                    expected_benefit="Fewer late-stage bugs",
                )
            ],
            summary="Start testing early.",
        ),
    }

    report = generate_final_report(state)

    assert report.project_plan.project_name == "Demo Project"
    assert len(report.task_breakdowns) == 1
    assert report.risk_analysis.overall_risk_level == "Low"
    assert report.schedule.total_duration_days == 2
    assert len(report.resource_allocation.assignments) == 1
    assert report.progress_report.overall_progress_percentage == 0
    assert len(report.recommendations.recommendations) == 1
