
from langgraph.graph import StateGraph, START, END

from schemas.workflow_state import ProjectWorkflowState
from agents.planner import create_project_plan
from agents.task_breakdown import break_down_task
from agents.risk_analyzer import analyze_project_risks
from agents.schedule_estimator import estimate_project_schedule
from agents.resource_allocator import allocate_resources
from agents.progress_tracker import track_project_progress
from agents.recommendation_agent import generate_recommendations
from agents.report_generator import generate_final_report


def planner_node(state: ProjectWorkflowState) -> dict:
    """Generate the initial project plan."""
    plan = create_project_plan(state["project_description"])

    return {"project_plan": plan}


def task_breakdown_node(state: ProjectWorkflowState) -> dict:
    """Break every planned task into actionable subtasks."""
    plan = state["project_plan"]

    breakdowns = [
        break_down_task(
            task_id=task.task_id,
            task_title=task.title,
            task_description=task.description,
            parent_estimated_hours=task.estimated_hours,
        )
        for task in plan.tasks
    ]

    return {"task_breakdowns": breakdowns}


def risk_analysis_node(state: ProjectWorkflowState) -> dict:
    """Analyze risks in the generated project plan."""
    plan = state["project_plan"]

    risk_analysis = analyze_project_risks(plan)

    return {"risk_analysis": risk_analysis}

def schedule_estimation_node(state: ProjectWorkflowState) -> dict:
    """Estimate the project schedule."""
    plan = state["project_plan"]

    schedule = estimate_project_schedule(plan)

    return {"schedule": schedule}

def resource_allocation_node(state: ProjectWorkflowState) -> dict:
    """Recommend roles and skills for project tasks."""
    plan = state["project_plan"]

    allocation = allocate_resources(plan)

    return {"resource_allocation": allocation}

def progress_tracking_node(state: ProjectWorkflowState) -> dict:
    """Track the project's initial progress."""
    plan = state["project_plan"]

    report = track_project_progress(
        plan=plan,
        completed_task_ids=[],
        actual_hours={},
    )

    return {"progress_report": report}

def recommendation_node(state: ProjectWorkflowState) -> dict:
    """Generate recommendations using project analysis."""
    plan = state["project_plan"]
    risks = state["risk_analysis"]
    progress = state["progress_report"]

    recommendations = generate_recommendations(
        plan=plan,
        risk_analysis=risks,
        progress_report=progress,
    )

    return {"recommendations": recommendations}

def final_report_node(state: ProjectWorkflowState) -> dict:
    """Assemble the outputs into one final project report."""
    report = generate_final_report(state)

    return {"final_report": report}


def build_project_workflow():
    graph = StateGraph(ProjectWorkflowState)

    graph.add_node("planner", planner_node)
    graph.add_node("task_breakdown", task_breakdown_node)
    graph.add_node("risk_analysis", risk_analysis_node)
    graph.add_node("schedule_estimation", schedule_estimation_node)
    graph.add_node("resource_allocation", resource_allocation_node)
    graph.add_node("progress_tracking", progress_tracking_node)
    graph.add_node("recommendations", recommendation_node)
    graph.add_node("final_report", final_report_node)

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "task_breakdown")
    graph.add_edge("task_breakdown", "risk_analysis")
    graph.add_edge("risk_analysis", "schedule_estimation")
    graph.add_edge("schedule_estimation", "resource_allocation")
    graph.add_edge("resource_allocation", "progress_tracking")
    graph.add_edge("progress_tracking", "recommendations")
    graph.add_edge("recommendations", "final_report")
    graph.add_edge("final_report", END)

    return graph.compile()



def validate_workflow_structure():
    workflow = build_project_workflow()
    graph = workflow.get_graph()

    expected_nodes = {
        "planner",
        "task_breakdown",
        "risk_analysis",
        "schedule_estimation",
        "resource_allocation",
        "progress_tracking",
        "recommendations",
        "final_report",
    }

    actual_nodes = set(graph.nodes.keys())
    missing_nodes = expected_nodes - actual_nodes

    if missing_nodes:
        raise AssertionError(
            f"Missing workflow nodes: {missing_nodes}"
        )

    expected_edges = [
        ("__start__", "planner"),
        ("planner", "task_breakdown"),
        ("task_breakdown", "risk_analysis"),
        ("risk_analysis", "schedule_estimation"),
        ("schedule_estimation", "resource_allocation"),
        ("resource_allocation", "progress_tracking"),
        ("progress_tracking", "recommendations"),
        ("recommendations", "final_report"),
        ("final_report", "__end__"),
    ]

    actual_edges = {
        (edge.source, edge.target)
        for edge in graph.edges
    }

    missing_edges = set(expected_edges) - actual_edges

    if missing_edges:
        raise AssertionError(
            f"Missing workflow edges: {missing_edges}"
        )

    print("Workflow structure validation passed!")
    print("Workflow connections validation passed!")
    print(f"Registered nodes: {len(expected_nodes)}")


if __name__ == "__main__":
    validate_workflow_structure()
