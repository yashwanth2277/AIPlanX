from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from agents.management_workflow import build_management_workflow
from agents.project_assistant import ask_project_assistant
from api.planning import read_job, start_planning_job
from api.schemas import (
    AnalyzeDelayRequest,
    AssistantAskRequest,
    CreateProjectRequest,
    CreateSessionRequest,
    CreateTeamMemberRequest,
    UpdateTeamMemberRequest,
    DelayRequest,
    PlanRequest,
    ProgressUpdateRequest,
    ReassignRequest,
    AddCollaboratorRequest,
    RemoveCollaboratorRequest,
    UpdateProjectRequest,
)
from api.services import (
    build_overview,
    create_management_session,
    resolve_project_report,
    serialize_tasks,
    session_report,
)
from api.store import create_store
from utils.assistant_context import build_assistant_context_from_state
from utils.management_report_generator import generate_management_report


@asynccontextmanager
async def lifespan(app: FastAPI):
    store = create_store()
    store.initialize()
    store.import_demo_data()
    app.state.store = store
    app.state.management_workflow = build_management_workflow()
    yield


def create_app(store=None) -> FastAPI:
    app = FastAPI(title="AIPlanX API", lifespan=lifespan if store is None else None)

    if store is not None:
        store.initialize()
        store.import_demo_data()
        app.state.store = store
        app.state.management_workflow = build_management_workflow()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(ValueError)
    async def value_error_handler(_request: Request, exc: ValueError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(FileNotFoundError)
    async def missing_handler(_request: Request, exc: FileNotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(FileExistsError)
    async def exists_handler(_request: Request, exc: FileExistsError):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.get("/api/health")
    def health(request: Request):
        return {"status": "ok", "store": type(request.app.state.store).__name__}

    @app.get("/api/employees")
    def list_employees(request: Request, project_id: int | None = None):
        store = request.app.state.store
        if hasattr(store, "list_effective_employees"):
            employees = store.list_effective_employees(project_id=project_id)
        else:
            employees = store.list_employees()
        return {
            "employees": [
                employee.model_dump(mode="json")
                for employee in employees
            ]
        }

    @app.get("/api/projects")
    def list_projects(request: Request):
        return {
            "projects": [
                {
                    "id": project.id,
                    "name": project.name,
                    "summary": project.summary,
                    "description": project.description,
                    "created_at": project.created_at,
                    "updated_at": project.updated_at or project.created_at,
                    "has_report": project.final_report is not None,
                }
                for project in request.app.state.store.list_projects()
            ]
        }

    @app.post("/api/projects", status_code=201)
    def create_project(body: CreateProjectRequest, request: Request):
        store = request.app.state.store
        record = store.save_project(
            name=body.name,
            summary=body.summary,
            description=body.description,
        )
        response = record.model_dump(mode="json")
        response["has_report"] = record.final_report is not None
        return response

    @app.post("/api/projects/plan", status_code=202)
    def plan_project(body: PlanRequest, request: Request):
        job_id = start_planning_job(
            request.app.state.store,
            body.description,
            body.session_name,
            body.create_session,
        )
        return {"job_id": job_id, "status": "queued"}

    @app.get("/api/projects/jobs/{job_id}")
    def plan_job_status(job_id: str):
        try:
            return read_job(job_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="Planning job not found")

    @app.get("/api/projects/{project_id}")
    def get_project(project_id: int, request: Request):
        project = request.app.state.store.get_project(project_id)
        response = project.model_dump(mode="json")
        response["has_report"] = project.final_report is not None
        return response

    @app.patch("/api/projects/{project_id}")
    def update_project(
        project_id: int,
        body: UpdateProjectRequest,
        request: Request,
    ):
        store = request.app.state.store
        record = store.update_project(
            project_id,
            name=body.name,
            summary=body.summary,
            description=body.description,
        )
        response = record.model_dump(mode="json")
        response["has_report"] = record.final_report is not None
        return response

    @app.delete("/api/projects/{project_id}", status_code=204)
    def delete_project(project_id: int, request: Request):
        store = request.app.state.store
        store.delete_project(project_id)
        return None

    # ----------------------------------------------------------------------- #
    # Project-scoped team members (System B)
    # ----------------------------------------------------------------------- #

    @app.get("/api/projects/{project_id}/members")
    def list_team_members(project_id: int, request: Request):
        store = request.app.state.store
        # Validate project exists
        store.get_project(project_id)
        members = store.list_team_members(project_id)
        return {"members": members}

    @app.post("/api/projects/{project_id}/members", status_code=201)
    def add_team_member(
        project_id: int,
        body: CreateTeamMemberRequest,
        request: Request,
    ):
        store = request.app.state.store
        member = store.add_team_member(
            project_id,
            name=body.name,
            role=body.role,
            member_type=body.member_type,
            skills=body.skills,
            allocation_days=body.allocation_days,
            email="",
        )
        return member

    @app.delete("/api/projects/{project_id}/members/{member_id}", status_code=204)
    def delete_team_member(project_id: int, member_id: int, request: Request):
        store = request.app.state.store
        # Validate project exists first
        store.get_project(project_id)
        store.delete_team_member(member_id, project_id)
        return None

    @app.put("/api/projects/{project_id}/members/{member_id}")
    @app.patch("/api/projects/{project_id}/members/{member_id}")
    def update_team_member(
        project_id: int,
        member_id: int,
        body: UpdateTeamMemberRequest,
        request: Request,
    ):
        store = request.app.state.store
        store.get_project(project_id)
        return store.update_team_member(
            member_id,
            project_id,
            name=body.name,
            role=body.role,
            member_type=body.member_type,
            skills=body.skills,
            allocation_days=body.allocation_days,
        )

    @app.get("/api/projects/{project_id}/report")
    def get_project_report(project_id: int, request: Request):
        project = request.app.state.store.get_project(project_id)
        if project.final_report is None:
            raise HTTPException(status_code=404, detail="Project report not found")
        return project.final_report.model_dump(mode="json")

    @app.get("/api/projects/{project_id}/team-workflow")
    def get_team_workflow(project_id: int, request: Request):
        project = request.app.state.store.get_project(project_id)
        if project.team_workflow is None:
            raise HTTPException(status_code=404, detail="Team workflow not found")
        return project.team_workflow

    @app.get("/api/sessions")
    def list_sessions(request: Request):
        return {
            "sessions": [
                item.model_dump(mode="json")
                for item in request.app.state.store.list_sessions()
            ]
        }

    @app.post("/api/sessions", status_code=201)
    def create_session(body: CreateSessionRequest, request: Request):
        store = request.app.state.store
        project_id, report = resolve_project_report(store, body.project_id)
        record = create_management_session(
            store,
            body.name,
            report,
            project_id=project_id,
        )
        return record.model_dump(mode="json")

    @app.get("/api/sessions/{name}")
    def get_session(name: str, request: Request):
        return request.app.state.store.get_session(name).model_dump(mode="json")

    @app.get("/api/sessions/{name}/overview")
    def session_overview(name: str, request: Request):
        store = request.app.state.store
        session = store.get_session(name)
        if hasattr(store, "list_effective_employees"):
            employees = store.list_effective_employees(project_id=session.project_id)
        else:
            employees = store.list_employees()
        return build_overview(session, len(employees))

    @app.get("/api/sessions/{name}/tasks")
    def session_tasks(name: str, request: Request):
        session = request.app.state.store.get_session(name)
        return {"tasks": serialize_tasks(session)}

    @app.get("/api/sessions/{name}/tasks/{task_id}/activity")
    def task_activity(name: str, task_id: int, request: Request):
        session = request.app.state.store.get_session(name)

        if not any(
            task.task_id == task_id
            for task in session.management_state.plan.tasks
        ):
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found",
            )

        activities = [
            activity.model_dump(mode="json")
            for activity in session.management_state.activity_history
            if activity.task_id == task_id
        ]

        return {
            "task_id": task_id,
            "activities": activities,
        }
    @app.patch("/api/sessions/{name}/tasks/{task_id}/progress")
    def update_progress(
        name: str,
        task_id: int,
        body: ProgressUpdateRequest,
        request: Request,
    ):
        return _invoke_management(
            request,
            name,
            {
                "action": "update_progress",
                "update_task_id": task_id,
                "update_task_status": body.status,
                "update_progress_percent": body.progress_percent,
                "update_actual_hours_spent": body.actual_hours_spent,
                "update_completed_work": body.completed_work,
                "update_remaining_work": body.remaining_work,
                "update_blockers": body.blockers,
                "update_comment": body.comment,
                "update_by": body.updated_by,
                "update_role": body.updater_role,
            },
        )

    @app.post("/api/sessions/{name}/tasks/{task_id}/delays")
    def record_delay(
        name: str,
        task_id: int,
        body: DelayRequest,
        request: Request,
    ):
        return _invoke_management(
            request,
            name,
            {
                "action": "record_delay",
                "delay_task_id": task_id,
                "delay_hours": body.delay_hours,
                "delay_reason": body.reason,
            },
        )

    @app.post("/api/sessions/{name}/tasks/{task_id}/analyze-delay")
    def analyze_delay(
        name: str,
        task_id: int,
        body: AnalyzeDelayRequest,
        request: Request,
    ):
        return _invoke_management(
            request,
            name,
            {
                "action": "analyze_delay",
                "delayed_task_id": task_id,
                "delay_weeks": body.delay_weeks,
                "delay_hours": body.delay_hours,
                "delay_reason": body.delay_reason,
            },
        )

    @app.post("/api/sessions/{name}/tasks/{task_id}/reassign")
    def reassign_task(
        name: str,
        task_id: int,
        body: ReassignRequest,
        request: Request,
    ):
        return _invoke_management(
            request,
            name,
            {
                "action": "reassign_task",
                "reassign_task_id": task_id,
                "new_employee_id": body.employee_id,
                "reassignment_reason": body.reason,
            },
        )

    @app.post("/api/sessions/{name}/tasks/{task_id}/collaborators")
    def add_task_collaborator(
        name: str,
        task_id: int,
        body: AddCollaboratorRequest,
        request: Request,
    ):
        return _invoke_management(
            request,
            name,
            {
                "action": "add_collaborator",
                "task_id": task_id,
                "new_employee_id": body.employee_id,
                "reason": body.reason,
            },
        )

    @app.delete("/api/sessions/{name}/tasks/{task_id}/collaborators/{employee_id}")
    def remove_task_collaborator(
        name: str,
        task_id: int,
        employee_id: str,
        request: Request,
    ):
        return _invoke_management(
            request,
            name,
            {
                "action": "remove_collaborator",
                "task_id": task_id,
                "employee_id": employee_id,
                "reason": "Collaborator removed",
            },
        )

    @app.get("/api/sessions/{name}/schedule")
    def session_schedule(name: str, request: Request):
        session = request.app.state.store.get_session(name)
        return session.work_schedule.model_dump(mode="json")

    @app.get("/api/sessions/{name}/report")
    def management_report(name: str, request: Request):
        store = request.app.state.store
        session = store.get_session(name)
        report = generate_management_report(
            management_state=session.management_state,
            work_schedule=session.work_schedule,
        )
        try:
            from agents.management_ai import generate_management_insights

            insights = generate_management_insights(
                session.management_state
            ).model_dump(mode="json")
        except Exception as error:
            insights = {
                "unavailable": True,
                "reason": f"{type(error).__name__}: {error}",
            }
        planning = session_report(store, session)
        return {
            "management_report": report.model_dump(mode="json"),
            "insights": insights,
            "planning_report": (
                planning.model_dump(mode="json") if planning else None
            ),
        }

    @app.post("/api/assistant/ask")
    def assistant_ask(body: AssistantAskRequest, request: Request):
        store = request.app.state.store
        session = store.get_session(body.session_name)
        report = session_report(store, session)
        if report is None:
            raise HTTPException(
                status_code=400,
                detail="A planning report is required before using the assistant.",
            )
        if hasattr(store, "list_effective_employees"):
            employees = store.list_effective_employees(project_id=session.project_id)
        else:
            employees = store.list_employees()
        context = build_assistant_context_from_state(
            body.session_name,
            report=report,
            management_state=session.management_state,
            work_schedule=session.work_schedule,
            employees=employees,
        )
        try:
            answer = ask_project_assistant(
                body.question,
                session_name=body.session_name,
                context=context,
            )
        except ValueError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        return {"answer": answer}

    def _invoke_management(request: Request, name: str, payload: dict):
        store = request.app.state.store
        session = store.get_session(name)
        if hasattr(store, "list_effective_employees"):
            employees = store.list_effective_employees(project_id=session.project_id)
        else:
            employees = store.list_employees()

        if payload.get("action") in ("reassign_task", "add_collaborator"):
            raw_id = str(payload.get("new_employee_id", ""))
            if raw_id and not any(e.employee_id == raw_id for e in employees):
                if any(e.employee_id == f"TM{raw_id}" for e in employees):
                    payload["new_employee_id"] = f"TM{raw_id}"
        elif payload.get("action") == "remove_collaborator":
            raw_id = str(payload.get("employee_id", ""))
            if raw_id and not any(e.employee_id == raw_id for e in employees):
                if any(e.employee_id == f"TM{raw_id}" for e in employees):
                    payload["employee_id"] = f"TM{raw_id}"

        result = request.app.state.management_workflow.invoke(
            {
                "management_state": session.management_state,
                "work_schedule": session.work_schedule,
                "employees": employees,
                **payload,
            }
        )
        updated_state = result.get("management_state", session.management_state)
        updated_schedule = result.get("work_schedule", session.work_schedule)
        saved = store.save_session(
            name,
            updated_state,
            updated_schedule,
            project_id=session.project_id,
        )
        response = saved.model_dump(mode="json")
        if "schedule_impact_report" in result:
            impact = result["schedule_impact_report"]
            response["schedule_impact_report"] = (
                impact.model_dump(mode="json")
                if hasattr(impact, "model_dump")
                else impact
            )
        if "management_report" in result:
            response["management_report"] = result["management_report"]
        return response

    return app


app = create_app()
