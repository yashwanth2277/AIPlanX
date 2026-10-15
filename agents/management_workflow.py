
from langgraph.graph import StateGraph, START, END

from schemas.management_workflow_state import ManagementWorkflowState
from schemas.employee import EmployeeRoster

from utils.management_initializer import initialize_management_state
from utils.project_management_engine import (
    update_task_progress,
    record_task_delay,
)
from utils.schedule_impact_engine import calculate_schedule_impact
from utils.resource_rescheduler import reschedule_work_schedule
from utils.management_report_generator import generate_management_report
from utils.reassignment_engine import reassign_task
from agents.management_ai import generate_management_insights

def initialize_management_node(
    state: ManagementWorkflowState,
) -> dict:
    """Initialize live management state for a new session."""

    current_state = state["management_state"]

    management_state = initialize_management_state(
        plan=current_state.plan,
        assignments=current_state.assignments,
    )

    return {"management_state": management_state}


def update_progress_node(
    state: ManagementWorkflowState,
) -> dict:
    """Update task progress without resetting other task records."""

    updated_state = update_task_progress(
        state=state["management_state"],
        task_id=state["update_task_id"],
        status=state["update_task_status"],
        progress_percent=state["update_progress_percent"],
        actual_hours_spent=state.get("update_actual_hours_spent"),
    )

    return {"management_state": updated_state}


def record_delay_node(
    state: ManagementWorkflowState,
) -> dict:
    """Record a delay without modifying the original state."""

    updated_state = record_task_delay(
        state=state["management_state"],
        task_id=state["delay_task_id"],
        delay_hours=state["delay_hours"],
        reason=state["delay_reason"],
    )

    return {"management_state": updated_state}





def analyze_delay_node(
    state: ManagementWorkflowState,
) -> dict:
    """Analyze a recorded delay without applying it twice."""

    management_state = state["management_state"]
    delayed_task_id = state["delayed_task_id"]
    delay_weeks = state["delay_weeks"]

    plan = management_state.plan
    schedule = state["work_schedule"]
    employees = state["employees"]

    plan_task_ids = {task.task_id for task in plan.tasks}

    if delayed_task_id not in plan_task_ids:
        raise ValueError(f"Unknown task ID: {delayed_task_id}")

    if not any(
        task.task_id == delayed_task_id
        for task in schedule.scheduled_tasks
    ):
        raise ValueError(
            f"Task {delayed_task_id} is not present in the work schedule"
        )

    delay_hours = state.get("delay_hours")
    delay_reason = state.get("delay_reason")

    # Record a new delay only when details are supplied.
    if delay_hours is not None or delay_reason is not None:
        if delay_hours is None or not delay_reason:
            raise ValueError(
                "Both delay_hours and delay_reason are required "
                "when recording a delay during analysis."
            )

        management_state = record_task_delay(
            state=management_state,
            task_id=delayed_task_id,
            delay_hours=delay_hours,
            reason=delay_reason,
        )

    progress = next(
        (
            item
            for item in management_state.task_progress
            if item.task_id == delayed_task_id
        ),
        None,
    )

    if progress is None or not progress.delays:
        raise ValueError(
            f"Task {delayed_task_id} has no recorded delays to analyze."
        )

    # Identify the most recent delay for this task.
    latest_delay = progress.delays[-1]
    delay_id = (
        f"{latest_delay.task_id}:"
        f"{latest_delay.recorded_at.isoformat()}:"
        f"{latest_delay.delay_hours}:"
        f"{latest_delay.reason}"
    )

    # If this exact delay was already applied, do not reschedule again.
    already_applied = delay_id in management_state.applied_delay_ids

    impact_report = calculate_schedule_impact(
        plan=plan,
        schedule=schedule,
        delayed_task_id=delayed_task_id,
        delay_weeks=delay_weeks,
    )

    if already_applied:
        revised_schedule = schedule
    else:
        revised_schedule = reschedule_work_schedule(
            plan=plan,
            employees=employees,
            schedule=schedule,
            delayed_task_id=delayed_task_id,
            delay_weeks=delay_weeks,
        )

        management_state = management_state.model_copy(
            update={
                "applied_delay_ids": [
                    *management_state.applied_delay_ids,
                    delay_id,
                ]
            }
        )

    return {
        "management_state": management_state,
        "schedule_impact_report": impact_report,
        "work_schedule": revised_schedule,
    }



def reassign_task_node(
    state: ManagementWorkflowState,
) -> dict:
    """Reassign a task and keep its scheduled employee consistent."""

    management_state = state["management_state"]
    employees = state["employees"]
    task_id = state["reassign_task_id"]
    new_employee_id = state["new_employee_id"]

    roster = EmployeeRoster(employees=employees)

    # Validate the assignment and preserve its history.
    updated_state = reassign_task(
        state=management_state,
        roster=roster,
        task_id=task_id,
        new_employee_id=new_employee_id,
        reason=state["reassignment_reason"],
    )

    schedule = state.get("work_schedule")

    # A task may be assigned but not scheduled.
    if schedule is None:
        return {"management_state": updated_state}

    scheduled_task = next(
        (
            task
            for task in schedule.scheduled_tasks
            if task.task_id == task_id
        ),
        None,
    )

    # Keep the management assignment even if this task has no schedule entry.
    # There is no scheduled employee to synchronize in this case.
    if scheduled_task is None:
        return {"management_state": updated_state}

    employee_by_id = {
        employee.employee_id: employee
        for employee in employees
    }

    replacement = employee_by_id.get(new_employee_id)

    if replacement is None:
        raise ValueError(
            f"Unknown employee ID: {new_employee_id}"
        )

    # Calculate the replacement's existing scheduled workload by week.
    weekly_hours = {}

    for scheduled in schedule.scheduled_tasks:
        if scheduled.task_id == task_id:
            continue

        for allocation in scheduled.weekly_allocations:
            key = (scheduled.employee_id, allocation.week)
            weekly_hours[key] = (
                weekly_hours.get(key, 0.0)
                + allocation.allocated_hours
            )

    # Preserve the task's current allocation only if the replacement
    # has enough capacity in every affected week.
    for allocation in scheduled_task.weekly_allocations:
        week = allocation.week
        already_allocated = weekly_hours.get(
            (new_employee_id, week),
            0.0,
        )

        available_capacity = replacement.weekly_capacity_hours

        # Account for the employee's existing workload in week one.
        if week == 1:
            available_capacity *= (
                1 - replacement.current_workload_percent / 100
            )

        proposed_total = (
            already_allocated + allocation.allocated_hours
        )

        if proposed_total > available_capacity + 1e-6:
            raise ValueError(
                f"Cannot reassign task {task_id} to "
                f"{replacement.employee_name}: insufficient capacity "
                f"in week {week}. Required scheduled hours: "
                f"{proposed_total:.2f}; available capacity: "
                f"{available_capacity:.2f}."
            )

    # Change the scheduled employee while preserving the existing
    # allocation, task dates, and assignment reason.
    updated_scheduled_task = scheduled_task.model_copy(
        update={
            "employee_id": replacement.employee_id,
            "employee_name": replacement.employee_name,
            "assignment_reason": state["reassignment_reason"],
        }
    )

    updated_schedule = schedule.model_copy(
        update={
            "scheduled_tasks": [
                updated_scheduled_task
                if task.task_id == task_id
                else task
                for task in schedule.scheduled_tasks
            ]
        }
    )

    return {
        "management_state": updated_state,
        "work_schedule": updated_schedule,
    }



def generate_management_report_node(
    state: ManagementWorkflowState,
) -> dict:
    """Generate a deterministic report and optional Gemini insights."""

    report = generate_management_report(
        management_state=state["management_state"],
        work_schedule=state.get("work_schedule"),
        schedule_impact=state.get("schedule_impact_report"),
    )

    result = {
        "management_report": report.model_dump(mode="json"),
        "management_ai_insights": None,
    }

    try:
        insights = generate_management_insights(
            management_state=state["management_state"],
        )
        result["management_ai_insights"] = insights
    except Exception as error:
        # AI failure must not prevent deterministic reporting.
        print(
            "Warning: Gemini management insights unavailable: "
            f"{type(error).__name__}: {error}"
        )

    return result



def route_management_request(
    state: ManagementWorkflowState,
) -> str:
    """Route requests to the appropriate management action."""

    action = state.get("action")

    routes = {
        "initialize": "initialize_management",
        "update_progress": "update_progress",
        "record_delay": "record_delay",
        "analyze_delay": "analyze_delay",
        "generate_report": "generate_management_report",
        "reassign_task": "reassign_task",
    }

    if action not in routes:
        raise ValueError(
            f"Unsupported management action: {action!r}. "
            f"Supported actions: {', '.join(routes)}"
        )

    return routes[action]


def build_management_workflow():
    """Build and compile the live project management workflow."""

    graph = StateGraph(ManagementWorkflowState)

    graph.add_node(
        "initialize_management",
        initialize_management_node,
    )
    graph.add_node(
        "update_progress",
        update_progress_node,
    )
    graph.add_node(
        "record_delay",
        record_delay_node,
    )
    graph.add_node(
        "analyze_delay",
        analyze_delay_node,
    )
    graph.add_node(
        "generate_management_report",
        generate_management_report_node,
    )
    graph.add_node(
        "reassign_task",
        reassign_task_node,
    )

    graph.add_conditional_edges(
        START,
        route_management_request,
        {
            "initialize_management": "initialize_management",
            "update_progress": "update_progress",
            "record_delay": "record_delay",
            "analyze_delay": "analyze_delay",
            "generate_management_report": "generate_management_report",
            "reassign_task": "reassign_task",
        },
    )

    graph.add_edge("initialize_management", END)
    graph.add_edge("update_progress", END)
    graph.add_edge("record_delay", END)
    graph.add_edge("analyze_delay", END)
    graph.add_edge("generate_management_report", END)
    graph.add_edge("reassign_task", END)

    return graph.compile()
