
import pytest

from schemas.project_plan import Task, ProjectPlan
from agents.planner import create_project_plan
from agents.task_breakdown import break_down_task
from schemas.task_breakdown import TaskBreakdown
from agents.risk_analyzer import analyze_project_risks
from schemas.risk_analysis import RiskAnalysis
from schemas.schedule import ScheduledTask, ProjectSchedule
from agents.schedule_estimator import estimate_project_schedule
from agents.resource_allocator import allocate_resources
from schemas.resource_allocation import ResourceAllocation
from agents.progress_tracker import track_project_progress
from schemas.progress_tracking import ProgressReport
from agents.recommendation_agent import generate_recommendations
from schemas.recommendations import RecommendationReport


def test_project_plan_rejects_empty_tasks():
    with pytest.raises(ValueError):
        ProjectPlan(
            project_name="Demo",
            project_summary="Test project",
            total_estimated_hours=10,
            tasks=[],
        )


def test_project_plan_rejects_duplicate_task_ids():
    task1 = Task(
        task_id=1,
        title="Setup",
        description="Set up the project",
        required_skills=["Project Setup"],
        estimated_hours=2,
        priority="High",
    )
    task2 = Task(
        task_id=1,
        title="Database Setup",
        description="Set up the database",
        required_skills=["SQL"],
        estimated_hours=2,
        priority="High",
    )

    with pytest.raises(ValueError, match="Task IDs must be unique"):
        ProjectPlan(
            project_name="Demo",
            project_summary="Test project",
            total_estimated_hours=4,
            tasks=[task1, task2],
        )


def test_project_plan_rejects_nonexistent_dependencies():
    task = Task(
        task_id=1,
        title="Setup",
        description="Set up the project",
        required_skills=["Project Setup"],
        estimated_hours=2,
        priority="High",
        dependencies=[99],
    )

    with pytest.raises(ValueError, match="non-existent task 99"):
        ProjectPlan(
            project_name="Demo",
            project_summary="Test project",
            total_estimated_hours=2,
            tasks=[task],
        )


def test_project_plan_rejects_self_dependency():
    task = Task(
        task_id=1,
        title="Setup",
        description="Set up the project",
        required_skills=["Project Setup"],
        estimated_hours=2,
        priority="High",
        dependencies=[1],
    )

    with pytest.raises(ValueError, match="cannot depend on itself"):
        ProjectPlan(
            project_name="Demo",
            project_summary="Test project",
            total_estimated_hours=2,
            tasks=[task],
        )


def test_task_rejects_nonpositive_estimated_hours():
    with pytest.raises(ValueError):
        Task(
            task_id=1,
            title="Setup",
            description="Set up the project",
            required_skills=["Project Setup"],
            estimated_hours=0,
            priority="High",
        )


def test_task_rejects_negative_estimated_hours():
    with pytest.raises(ValueError):
        Task(
            task_id=1,
            title="Setup",
            description="Set up the project",
            required_skills=["Project Setup"],
            estimated_hours=-5,
            priority="High",
        )


def test_project_plan_rejects_incorrect_total_hours():
    task = Task(
        task_id=1,
        title="Setup",
        description="Set up the project",
        required_skills=["Project Setup"],
        estimated_hours=5,
        priority="High",
    )

    with pytest.raises(
        ValueError,
        match="Total estimated hours must equal the sum of task hours",
    ):
        ProjectPlan(
            project_name="Demo",
            project_summary="Test project",
            total_estimated_hours=10,
            tasks=[task],
        )


def test_project_plan_accepts_valid_plan():
    task = Task(
        task_id=1,
        title="Setup",
        description="Set up the project",
        required_skills=["Project Setup"],
        estimated_hours=5,
        priority="High",
    )

    plan = ProjectPlan(
        project_name="Demo",
        project_summary="Test project",
        total_estimated_hours=5,
        tasks=[task],
    )

    assert plan.project_name == "Demo"
    assert len(plan.tasks) == 1
    assert plan.total_estimated_hours == 5


def test_planner_agent_returns_valid_plan():
    plan = create_project_plan(
        "Build a simple student task management app using Python."
    )

    assert isinstance(plan, ProjectPlan)
    assert len(plan.tasks) > 0
    assert len({task.task_id for task in plan.tasks}) == len(plan.tasks)



def test_task_breakdown_agent_returns_valid_subtasks():
    parent_hours = 8

    result = break_down_task(
        task_id=1,
        task_title="Implement user authentication",
        task_description=(
            "Build secure registration and login functionality."
        ),
        parent_estimated_hours=parent_hours,
    )

    assert isinstance(result, TaskBreakdown)
    assert result.task_id == 1
    assert result.parent_estimated_hours == parent_hours
    assert len(result.subtasks) >= 3

    subtask_ids = [subtask.subtask_id for subtask in result.subtasks]

    assert len(subtask_ids) == len(set(subtask_ids))
    assert all(
        subtask.estimated_hours > 0
        for subtask in result.subtasks
    )

    total_subtask_hours = sum(
        subtask.estimated_hours for subtask in result.subtasks
    )
    assert abs(total_subtask_hours - parent_hours) <= 0.1


def test_risk_analysis_agent_returns_valid_result():
    plan = ProjectPlan(
        project_name="Demo Project",
        project_summary="A small test project.",
        total_estimated_hours=8,
        tasks=[
            Task(
                task_id=1,
                title="Build API",
                description="Implement the API.",
                required_skills=["Python", "FastAPI"],
                estimated_hours=8,
                priority="High",
            )
        ],
    )

    result = analyze_project_risks(plan)

    assert isinstance(result, RiskAnalysis)
    assert result.project_name == plan.project_name
    assert len(result.risks) > 0
    assert len(result.recommendations) > 0


def test_scheduled_task_rejects_end_day_before_start_day():
    with pytest.raises(
        ValueError,
        match="end_day cannot be before start_day",
    ):
        ScheduledTask(
            task_id=1,
            title="Build API",
            estimated_hours=4,
            start_day=3,
            end_day=2,
        )


def test_schedule_estimation_agent_returns_valid_schedule():
    plan = ProjectPlan(
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

    result = estimate_project_schedule(plan)

    assert isinstance(result, ProjectSchedule)
    assert result.project_name == plan.project_name
    assert len(result.scheduled_tasks) == len(plan.tasks)

    scheduled_ids = {
        task.task_id for task in result.scheduled_tasks
    }

    assert scheduled_ids == {1, 2}
    assert result.total_duration_days > 0


def test_resource_allocation_agent_returns_valid_result():
    plan = ProjectPlan(
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

    result = allocate_resources(plan)

    assert isinstance(result, ResourceAllocation)
    assert result.project_name == plan.project_name
    assert len(result.assignments) == len(plan.tasks)

    assigned_task_ids = {
        assignment.task_id for assignment in result.assignments
    }

    assert assigned_task_ids == {1, 2}
    assert all(
        assignment.estimated_effort_hours > 0
        for assignment in result.assignments
    )


def test_progress_tracker_returns_valid_report():
    plan = ProjectPlan(
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

    result = track_project_progress(
        plan=plan,
        completed_task_ids=[1],
        actual_hours={1: 2, 2: 1},
    )

    assert isinstance(result, ProgressReport)
    assert result.project_name == plan.project_name
    assert result.completed_tasks == 1
    assert result.pending_tasks == 1
    assert len(result.task_progress) == 2
    assert result.task_progress[0].status == "Completed"
    assert result.task_progress[1].status == "In Progress"



def test_recommendation_agent():
    from schemas.risk_analysis import ProjectRisk

    # Prepare test data without calling the planner LLM.
    plan = ProjectPlan(
        project_name="College Issue Reporting System",
        project_summary="A system for reporting and tracking college issues.",
        total_estimated_hours=8,
        tasks=[
            Task(
                task_id=1,
                title="Build issue reporting API",
                description="Create endpoints for reporting issues.",
                required_skills=["Python", "FastAPI"],
                estimated_hours=8,
                priority="High",
                dependencies=[],
            )
        ],
    )

    # Prepare risk data without calling the risk-analysis LLM.
    risk_analysis = RiskAnalysis(
        project_name=plan.project_name,
        overall_risk_level="Medium",
        risks=[
            ProjectRisk(
                risk_id=1,
                title="API development delay",
                description="API implementation may take longer than expected.",
                severity="Medium",
                mitigation="Review progress regularly.",
            )
        ],
        recommendations=["Test API endpoints early."],
    )

    # Progress tracking is local; it doesn't require an LLM.
    progress_report = track_project_progress(
        plan=plan,
        completed_task_ids=[],
        actual_hours={},
    )

    # This is the only live LLM call in this test.
    result = generate_recommendations(
        plan=plan,
        risk_analysis=risk_analysis,
        progress_report=progress_report,
    )

    assert isinstance(result, RecommendationReport)
    assert result.project_name == plan.project_name
    assert len(result.recommendations) >= 3
    assert all(
        recommendation.priority in ["High", "Medium", "Low"]
        for recommendation in result.recommendations
    )
