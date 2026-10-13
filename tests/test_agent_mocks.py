
from unittest.mock import MagicMock, patch

from agents.planner import create_project_plan
from agents.task_breakdown import break_down_task
from agents.risk_analyzer import analyze_project_risks
from agents.schedule_estimator import estimate_project_schedule
from agents.resource_allocator import allocate_resources
from agents.progress_tracker import track_project_progress
from agents.recommendation_agent import generate_recommendations

from schemas.project_plan import ProjectPlan, Task
from schemas.task_breakdown import TaskBreakdown, Subtask
from schemas.risk_analysis import RiskAnalysis, ProjectRisk
from schemas.schedule import ProjectSchedule, ScheduledTask
from schemas.resource_allocation import ResourceAllocation, ResourceAssignment
from schemas.progress_tracking import ProgressReport
from schemas.recommendations import RecommendationReport, Recommendation


def make_plan():
    return ProjectPlan(
        project_name="Demo Project",
        project_summary="A small test project.",
        total_estimated_hours=6,
        tasks=[
            Task(
                task_id=1,
                title="Design database",
                description="Design the database schema.",
                required_skills=["SQL", "Database Design"],
                estimated_hours=2,
                priority="High",
                dependencies=[],
            ),
            Task(
                task_id=2,
                title="Build API",
                description="Implement the API.",
                required_skills=["Python", "FastAPI"],
                estimated_hours=4,
                priority="High",
                dependencies=[1],
            ),
        ],
    )


def mock_structured_response(response):
    structured_llm = MagicMock()
    structured_llm.invoke.return_value = response

    llm_mock = MagicMock()
    llm_mock.with_structured_output.return_value = structured_llm

    return llm_mock


def test_planner_agent_with_mocked_llm():
    expected = make_plan()

    with patch("agents.planner.llm", mock_structured_response(expected)):
        result = create_project_plan("Build a small API.")

    assert isinstance(result, ProjectPlan)
    assert len(result.tasks) == 2
    assert len({task.task_id for task in result.tasks}) == 2


def test_task_breakdown_agent_with_mocked_llm():

    expected = TaskBreakdown(
        task_id=1,
        task_title="Placeholder",
        parent_estimated_hours=8,
        subtasks=[
            Subtask(
                subtask_id=1,
                title="Design endpoint",
                description="Define the endpoint.",
                estimated_hours=2,
            ),
            Subtask(
                subtask_id=2,
                title="Implement endpoint",
                description="Implement the endpoint.",
                estimated_hours=3,
            ),
            Subtask(
                subtask_id=3,
                title="Test endpoint",
                description="Test the endpoint.",
                estimated_hours=3,
            ),
        ],
    )

    with patch(
        "agents.task_breakdown.llm",
        mock_structured_response(expected),
    ):
        result = break_down_task(
                1,
                "Build API",
                "Create API endpoints.",
                parent_estimated_hours=8,
            )

        assert isinstance(result, TaskBreakdown)
        assert result.task_id == 1
        assert result.task_title == "Build API"
        assert result.parent_estimated_hours == 8
        assert len(result.subtasks) == 3

        total_hours = sum(
            subtask.estimated_hours for subtask in result.subtasks
        )
        assert abs(total_hours - 8) <= 0.1


def test_risk_analysis_agent_with_mocked_llm():
    plan = make_plan()
    expected = RiskAnalysis(
        project_name="Placeholder",
        overall_risk_level="Medium",
        risks=[
            ProjectRisk(
                risk_id=1,
                title="Schedule delay",
                description="A task may take longer than expected.",
                severity="Medium",
                mitigation="Review progress regularly.",
            )
        ],
        recommendations=["Review project progress weekly."],
    )

    with patch(
        "agents.risk_analyzer.llm",
        mock_structured_response(expected),
    ):
        result = analyze_project_risks(plan)

    assert isinstance(result, RiskAnalysis)
    assert result.project_name == plan.project_name
    assert len(result.risks) >= 1


def test_schedule_estimation_agent_with_mocked_llm():
    plan = make_plan()
    expected = ProjectSchedule(
        project_name="Placeholder",
        total_duration_days=1,
        critical_path=[1, 2],
        scheduled_tasks=[
            ScheduledTask(
                task_id=1,
                title="Design database",
                estimated_hours=2,
                start_day=1,
                end_day=1,
                dependencies=[],
            ),
            ScheduledTask(
                task_id=2,
                title="Build API",
                estimated_hours=4,
                start_day=1,
                end_day=1,
                dependencies=[1],
            ),
        ],
        scheduling_notes=["Tasks follow their dependencies."],
    )

    with patch(
        "agents.schedule_estimator.llm",
        mock_structured_response(expected),
    ):
        result = estimate_project_schedule(plan)

    assert isinstance(result, ProjectSchedule)
    assert result.project_name == plan.project_name
    assert {task.task_id for task in result.scheduled_tasks} == {1, 2}


def test_resource_allocation_agent_with_mocked_llm():
    plan = make_plan()
    expected = ResourceAllocation(
        project_name="Placeholder",
        assignments=[
            ResourceAssignment(
                task_id=1,
                required_skills=["SQL", "Database Design"],
                recommended_role="Database Engineer",
                estimated_effort_hours=2,
                notes="Design the database schema.",
            ),
            ResourceAssignment(
                task_id=2,
                required_skills=["Python", "FastAPI"],
                recommended_role="Backend Developer",
                estimated_effort_hours=4,
                notes="Implement the API.",
            ),
        ],
        resource_recommendations=["Distribute work by skill set."],
    )

    with patch(
        "agents.resource_allocator.llm",
        mock_structured_response(expected),
    ):
        result = allocate_resources(plan)

    assert isinstance(result, ResourceAllocation)
    assert result.project_name == plan.project_name
    assert {item.task_id for item in result.assignments} == {1, 2}


def test_recommendation_agent_with_mocked_llm():
    plan = make_plan()
    risk_analysis = RiskAnalysis(
        project_name=plan.project_name,
        overall_risk_level="Low",
        risks=[
            ProjectRisk(
                risk_id=1,
                title="Testing delay",
                description="Testing may take longer.",
                severity="Low",
                mitigation="Start testing early.",
            )
        ],
        recommendations=["Start testing early."],
    )
    progress_report = track_project_progress(
        plan=plan,
        completed_task_ids=[],
        actual_hours={},
    )

    expected = RecommendationReport(
        project_name="Placeholder",
        summary="Recommendations to improve project delivery and reduce risks.",
        recommendations=[
            Recommendation(
                recommendation_id=1,
                title="Review progress",
                description="Review progress at regular intervals.",
                priority="Medium",
                expected_benefit="Identify blockers earlier.",
            ),
            Recommendation(
                recommendation_id=2,
                title="Validate database",
                description="Validate the schema before API integration.",
                priority="High",
                expected_benefit="Reduce integration errors.",
            ),
            Recommendation(
                recommendation_id=3,
                title="Test API",
                description="Test API behavior before release.",
                priority="High",
                expected_benefit="Catch defects earlier.",
            ),
        ],
    )

    with patch(
        "agents.recommendation_agent.llm",
        mock_structured_response(expected),
    ):
        result = generate_recommendations(
            plan=plan,
            risk_analysis=risk_analysis,
            progress_report=progress_report,
        )

    assert isinstance(result, RecommendationReport)
    assert result.project_name == plan.project_name
    assert len(result.recommendations) >= 3
    assert all(
        item.priority in ["High", "Medium", "Low"]
        for item in result.recommendations
    )
