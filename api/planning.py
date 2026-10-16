import re
from threading import Thread

from agents.team_workflow_builder import build_team_workflow
from agents.workflow import build_project_workflow
from api.jobs import create_job, get_job, update_job
from api.services import create_management_session


def slug_session_name(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-_")[:40]
    return slug or "session"


def unique_session_name(store, preferred: str) -> str:
    name = slug_session_name(preferred)
    try:
        store.get_session(name)
    except FileNotFoundError:
        return name
    index = 2
    while True:
        candidate = f"{name}-{index}"[:64]
        try:
            store.get_session(candidate)
        except FileNotFoundError:
            return candidate
        index += 1


def start_planning_job(
    store,
    description: str,
    session_name: str | None,
    create_session: bool,
) -> str:
    job_id = create_job({"status": "running"})
    thread = Thread(
        target=run_planning_job,
        args=(store, job_id, description, session_name, create_session),
        daemon=True,
    )
    thread.start()
    return job_id


def run_planning_job(
    store,
    job_id: str,
    description: str,
    session_name: str | None,
    create_session: bool,
) -> None:
    try:
        update_job(job_id, status="running")
        workflow = build_project_workflow()
        result = workflow.invoke({"project_description": description})
        report = result.get("final_report")
        plan = result.get("project_plan")
        resource_allocation = result.get("resource_allocation")
        if report is None or plan is None or resource_allocation is None:
            raise ValueError("Planning workflow completed without a full report.")

        team_workflow = build_team_workflow(
            plan=plan,
            resource_allocation=resource_allocation,
        )
        project = store.save_project(
            name=plan.project_name,
            summary=plan.project_summary,
            description=description,
            final_report=report,
            team_workflow=team_workflow.model_dump(mode="json"),
        )

        created_session = None
        if create_session:
            preferred = session_name or slug_session_name(plan.project_name)
            created_session = unique_session_name(store, preferred)
            create_management_session(
                store,
                created_session,
                report,
                project_id=project.id,
            )

        update_job(
            job_id,
            status="completed",
            project_id=project.id,
            session_name=created_session,
        )
    except Exception as error:
        update_job(
            job_id,
            status="failed",
            error=f"{type(error).__name__}: {error}",
        )


def read_job(job_id: str) -> dict:
    return get_job(job_id)
