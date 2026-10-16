from datetime import datetime, timezone

from schemas.assignment import TaskAssignment
from schemas.final_report import FinalProjectReport
from schemas.project_management import TaskStatus
from schemas.work_schedule import WorkSchedule
from utils.assignment_engine import assign_tasks
from utils.management_initializer import initialize_management_state
from utils.work_scheduler import build_work_schedule

from api.records import SessionRecord
from api.session_names import validate_session_name


def create_management_session(
    store,
    name: str,
    report: FinalProjectReport,
    project_id: int | None = None,
) -> SessionRecord:
    name = validate_session_name(name)
    try:
        store.get_session(name)
    except FileNotFoundError:
        pass
    else:
        raise FileExistsError(
            f"Session '{name}' already exists. Resume it instead of overwriting it."
        )

    employees = store.list_employees()
    if not employees:
        raise ValueError("No employees are available to assign work.")

    assignment_report = assign_tasks(
        plan=report.project_plan,
        employees=employees,
    )
    work_schedule = build_work_schedule(
        plan=report.project_plan,
        employees=employees,
        assignments=assignment_report.assignments,
    )
    # assign_tasks() only assigns tasks that fit a single employee's remaining
    # weekly capacity.  build_work_schedule() spreads work across multiple weeks
    # so it can schedule every task.  Supplement the assignment list with any
    # scheduled task that assign_tasks() could not place, so every task always
    # has exactly one assignment record.
    assigned_ids = {a.task_id for a in assignment_report.assignments}
    supplemental = [
        TaskAssignment(
            task_id=item.task_id,
            task_title=item.task_title,
            employee_id=item.employee_id,
            employee_name=item.employee_name,
            match_score=1.0,
            assignment_reason=item.assignment_reason,
        )
        for item in work_schedule.scheduled_tasks
        if item.task_id not in assigned_ids
    ]
    assignments = list(assignment_report.assignments) + supplemental
    management_state = initialize_management_state(
        plan=report.project_plan,
        assignments=assignments,
    )
    return store.save_session(
        name,
        management_state,
        work_schedule,
        project_id=project_id,
    )


def resolve_project_report(store, project_id: int | None) -> tuple[int, FinalProjectReport]:
    if project_id is not None:
        project = store.get_project(project_id)
        if project.final_report is None:
            raise ValueError(f"Project {project_id} has no planning report yet.")
        return project.id, project.final_report

    projects = store.list_projects()
    for project in reversed(projects):
        if project.final_report is not None:
            return project.id, project.final_report
    raise FileNotFoundError(
        "No planned project is available. Run AI Planning Studio first."
    )


def session_report(store, session: SessionRecord) -> FinalProjectReport | None:
    if session.project_id is not None:
        try:
            project = store.get_project(session.project_id)
        except FileNotFoundError:
            project = None
        if project and project.final_report is not None:
            return project.final_report

    projects = store.list_projects()
    for project in projects:
        if (
            project.final_report
            and project.final_report.project_plan.project_name
            == session.management_state.plan.project_name
        ):
            return project.final_report
    return None


def build_overview(session: SessionRecord, employee_count: int) -> dict:
    state = session.management_state
    schedule = session.work_schedule
    progress_records = state.task_progress
    total = len(progress_records)
    counts = {
        status.value: sum(item.status == status for item in progress_records)
        for status in TaskStatus
    }
    overall = (
        round(
            sum(item.progress_percent for item in progress_records) / total,
            1,
        )
        if total
        else 0.0
    )
    delayed_tasks = [
        item for item in progress_records if item.delays
    ]
    at_risk = counts[TaskStatus.BLOCKED.value] + len(delayed_tasks)
    assigned = {
        item.task_id: item for item in state.assignments
    }
    plan_by_id = {task.task_id: task for task in state.plan.tasks}

    status_rank = {
        TaskStatus.BLOCKED: 0,
        TaskStatus.IN_PROGRESS: 1,
        TaskStatus.PENDING: 2,
        TaskStatus.COMPLETED: 3,
    }
    priority_tasks = sorted(
        progress_records,
        key=lambda item: (
            status_rank.get(item.status, 9),
            -plan_by_id[item.task_id].estimated_hours,
        ),
    )[:6]

    colors = ["violet", "blue", "green", "orange"]
    tasks = []
    for index, item in enumerate(priority_tasks):
        task = plan_by_id[item.task_id]
        assignment = assigned.get(item.task_id)
        owner = assignment.employee_name if assignment else "Unassigned"
        initials = "".join(part[0] for part in owner.split()[:2]).upper() or "?"
        due = _due_label(schedule, item.task_id)
        tasks.append({
            "id": f"{task.task_id:02d}",
            "task_id": task.task_id,
            "title": task.title,
            "owner": owner,
            "initials": initials,
            "color": colors[index % len(colors)],
            "status": _status_label(item.status),
            "progress": item.progress_percent,
            "due": due,
            "priority": task.priority,
        })

    delay_hours = sum(
        delay.delay_hours
        for item in progress_records
        for delay in item.delays
    )
    assigned_ratio = (len(assigned) / total * 100) if total else 0
    schedule_score = max(40.0, 100.0 - min(50.0, delay_hours * 2))
    resource_score = max(40.0, min(100.0, assigned_ratio))
    health_score = round((schedule_score + overall + resource_score) / 3)
    if counts[TaskStatus.BLOCKED.value]:
        status_label = "Needs attention"
        health_label = "Watch closely"
    elif delay_hours:
        status_label = "Delayed"
        health_label = "Recovery needed"
    elif overall >= 70:
        status_label = "On track"
        health_label = "Looking good"
    else:
        status_label = "In progress"
        health_label = "Looking good"

    activities = []
    for item in progress_records:
        for delay in item.delays[-2:]:
            activities.append({
                "title": f"Delay recorded on task {item.task_id}",
                "detail": delay.reason,
                "time": _relative_time(delay.recorded_at),
                "color": "orange",
            })
    for change in state.assignment_changes[-3:]:
        activities.append({
            "title": f"Task {change.task_id} reassigned",
            "detail": change.reason,
            "time": _relative_time(change.changed_at),
            "color": "violet",
        })
    for item in progress_records:
        if item.status != TaskStatus.PENDING:
            activities.append({
                "title": f"Task {item.task_id} is {_status_label(item.status).lower()}",
                "detail": f"{plan_by_id[item.task_id].title} · {item.progress_percent:.0f}% complete",
                "time": _relative_time(item.updated_at),
                "color": "blue",
            })
    activities = activities[:6]

    return {
        "session_name": session.name,
        "project": {
            "name": state.plan.project_name,
            "summary": state.plan.project_summary,
            "total_estimated_hours": state.plan.total_estimated_hours,
            "status_label": status_label,
            "risks": state.plan.risks,
        },
        "progress": {
            "overall_percent": overall,
            "total_tasks": total,
            "completed": counts[TaskStatus.COMPLETED.value],
            "in_progress": counts[TaskStatus.IN_PROGRESS.value],
            "pending": counts[TaskStatus.PENDING.value],
            "blocked": counts[TaskStatus.BLOCKED.value],
            "at_risk": at_risk,
        },
        "health": {
            "score": health_score,
            "label": health_label,
            "schedule": round(schedule_score),
            "delivery": round(overall),
            "resources": round(resource_score),
        },
        "chart": _progress_chart(state, schedule),
        "priority_tasks": tasks,
        "activities": activities,
        "team_size": employee_count,
        "completion_week": _max_week(schedule),
    }


def serialize_tasks(session: SessionRecord) -> list[dict]:
    state = session.management_state
    schedule = session.work_schedule
    assigned = {item.task_id: item for item in state.assignments}
    progress_by_id = {item.task_id: item for item in state.task_progress}
    scheduled = {item.task_id: item for item in schedule.scheduled_tasks}
    colors = ["violet", "blue", "green", "orange"]
    rows = []
    for index, task in enumerate(state.plan.tasks):
        progress = progress_by_id[task.task_id]
        assignment = assigned.get(task.task_id)
        scheduled_task = scheduled.get(task.task_id)
        owner = assignment.employee_name if assignment else "Unassigned"
        initials = "".join(part[0] for part in owner.split()[:2]).upper() or "?"
        rows.append({
            "task_id": task.task_id,
            "title": task.title,
            "description": task.description,
            "required_skills": task.required_skills,
            "estimated_hours": task.estimated_hours,
            "priority": task.priority,
            "dependencies": task.dependencies,
            "status": progress.status.value,
            "status_label": _status_label(progress.status),
            "progress_percent": progress.progress_percent,
            "actual_hours_spent": progress.actual_hours_spent,
            "owner": owner,
            "employee_id": assignment.employee_id if assignment else None,
            "initials": initials,
            "color": colors[index % len(colors)],
            "start_week": scheduled_task.start_week if scheduled_task else None,
            "completion_week": (
                scheduled_task.completion_week if scheduled_task else None
            ),
            "due": _due_label(schedule, task.task_id),
            "delays": [
                delay.model_dump(mode="json") for delay in progress.delays
            ],
        })
    return rows


def _status_label(status: TaskStatus) -> str:
    return {
        TaskStatus.PENDING: "Pending",
        TaskStatus.IN_PROGRESS: "In progress",
        TaskStatus.BLOCKED: "Blocked",
        TaskStatus.COMPLETED: "Completed",
    }[status]


def _max_week(schedule: WorkSchedule) -> int | None:
    if not schedule.scheduled_tasks:
        return None
    return max(task.completion_week for task in schedule.scheduled_tasks)


def _due_label(schedule: WorkSchedule, task_id: int) -> str:
    for task in schedule.scheduled_tasks:
        if task.task_id == task_id:
            return f"Week {task.completion_week}"
    return "Unscheduled"


def _relative_time(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    seconds = max(0, int((datetime.now(timezone.utc) - value).total_seconds()))
    if seconds < 60:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} min ago"
    hours = minutes // 60
    if hours < 48:
        return f"{hours} hour ago" if hours == 1 else f"{hours} hours ago"
    days = hours // 24
    return f"{days} days ago"


def _progress_chart(state, schedule: WorkSchedule) -> list[dict]:
    tasks = {task.task_id: task for task in state.plan.tasks}
    progress = {item.task_id: item for item in state.task_progress}
    total_hours = state.plan.total_estimated_hours or 1
    max_week = _max_week(schedule) or 1
    weeks = max(max_week, 1)
    points = []
    for week in range(1, weeks + 1):
        planned_hours = 0.0
        actual_hours = 0.0
        for scheduled in schedule.scheduled_tasks:
            task = tasks.get(scheduled.task_id)
            if task is None:
                continue
            if scheduled.completion_week <= week:
                planned_hours += task.estimated_hours
            if scheduled.start_week <= week:
                item = progress[scheduled.task_id]
                actual_hours += (
                    task.estimated_hours * item.progress_percent / 100
                )
        points.append({
            "week": f"W{week}",
            "planned": round(planned_hours / total_hours * 100, 1),
            "actual": round(actual_hours / total_hours * 100, 1),
        })
    return points
