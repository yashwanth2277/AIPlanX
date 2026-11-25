from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, delete, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from schemas.assignment import TaskAssignment
from schemas.employee import Employee
from schemas.final_report import FinalProjectReport
from schemas.project_management import ProjectManagementState
from schemas.team_workflow import TeamWorkflow
from schemas.work_schedule import WorkSchedule
from utils.employee_parser import parse_employee_csv
from utils.management_persistence import load_management_state
from utils.schedule_persistence import load_work_schedule

from api.db_models import (
    ActivityLogRow,
    Base,
    DeadlineChangeRow,
    EmployeeRow,
    InvitationRow,
    ProgressUpdateRow,
    ProjectMemberRow,
    ProjectRow,
    ReportRow,
    SessionRow,
    TaskAssigneeRow,
    TaskRow,
    TeamMemberRow,
    utcnow,
)
from api.paths import EMPLOYEE_PATH, REPORT_PATH, SESSION_DIR, TEAM_WORKFLOW_PATH
from api.records import ProjectRecord, SessionRecord, SessionSummary
from api.session_names import validate_session_name


class SqliteStore:
    """SQLite-backed store that still serializes existing Pydantic graphs."""

    def __init__(self, database_path: Path):
        self.database_path = Path(database_path)
        self.engine = create_engine(
            f"sqlite:///{self.database_path}",
            future=True,
        )
        self._session_factory = sessionmaker(
            self.engine,
            expire_on_commit=False,
            future=True,
        )

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        Base.metadata.create_all(self.engine)
        with self.engine.connect() as conn:
            try:
                conn.execute(
                    text("ALTER TABLE projects ADD COLUMN updated_at DATETIME")
                )
                conn.commit()
            except OperationalError:
                pass
            try:
                conn.execute(
                    text(
                        "UPDATE projects SET updated_at = created_at WHERE updated_at IS NULL"
                    )
                )
                conn.commit()
            except OperationalError:
                pass
            try:
                conn.execute(
                    text("ALTER TABLE team_members ADD COLUMN allocation_days INTEGER")
                )
                conn.commit()
            except OperationalError:
                pass

    def _db(self) -> Session:
        return self._session_factory()

    def import_demo_data(
        self,
        *,
        employee_path: Path = EMPLOYEE_PATH,
        report_path: Path = REPORT_PATH,
        session_dir: Path = SESSION_DIR,
        team_workflow_path: Path = TEAM_WORKFLOW_PATH,
    ) -> None:
        self.initialize()
        self._import_employees(Path(employee_path))
        project_id = self._import_report(
            Path(report_path),
            Path(team_workflow_path),
        )
        self._import_file_sessions(Path(session_dir), project_id)
        self._seed_demo_session(project_id)

    def _import_employees(self, employee_path: Path) -> None:
        if not employee_path.is_file():
            return
        with self._db() as db:
            existing = db.scalar(select(EmployeeRow.id).limit(1))
            if existing is not None:
                return
            roster = parse_employee_csv(employee_path)
            for employee in roster.employees:
                db.add(
                    EmployeeRow(
                        employee_id=employee.employee_id,
                        payload=employee.model_dump(mode="json"),
                    )
                )
            db.commit()

    def _import_report(
        self,
        report_path: Path,
        team_workflow_path: Path,
    ) -> int | None:
        with self._db() as db:
            existing = db.scalar(select(ProjectRow.id).limit(1))
            if existing is not None:
                return existing
            if not report_path.is_file():
                return None
            report = FinalProjectReport.model_validate_json(
                report_path.read_text(encoding="utf-8")
            )
            team_workflow = None
            if team_workflow_path.is_file():
                team_workflow = TeamWorkflow.model_validate_json(
                    team_workflow_path.read_text(encoding="utf-8")
                ).model_dump(mode="json")
            now = utcnow()
            row = ProjectRow(
                name=report.project_plan.project_name,
                summary=report.project_plan.project_summary,
                description="",
                created_at=now,
                updated_at=now,
                final_report=report.model_dump(mode="json"),
                team_workflow=team_workflow,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return row.id

    @staticmethod
    def _supplement_assignments(
        state: ProjectManagementState,
        schedule: WorkSchedule,
    ) -> ProjectManagementState:
        """Supplement any missing task assignments from the work schedule.

        Legacy session files serialized before the assignment-fallback logic
        was introduced may contain an empty assignments list even though the
        work schedule has a valid employee for every task.  Rather than letting
        those sessions remain unassigned, we derive assignments from the
        schedule entries that have no corresponding assignment record.
        """
        assigned_ids = {a.task_id for a in state.assignments}
        supplemental = [
            TaskAssignment(
                task_id=item.task_id,
                task_title=item.task_title,
                employee_id=item.employee_id,
                employee_name=item.employee_name,
                match_score=1.0,
                assignment_reason=item.assignment_reason,
            )
            for item in schedule.scheduled_tasks
            if item.task_id not in assigned_ids
        ]
        if not supplemental:
            return state
        return state.model_copy(
            update={"assignments": list(state.assignments) + supplemental}
        )

    def _import_file_sessions(
        self,
        session_dir: Path,
        project_id: int | None,
    ) -> None:
        if not session_dir.is_dir():
            return
        with self._db() as db:
            existing = db.scalar(select(SessionRow.id).limit(1))
            if existing is not None:
                return
            for path in sorted(session_dir.iterdir()):
                state_path = path / "management_state.json"
                schedule_path = path / "work_schedule.json"
                if not path.is_dir() or not state_path.is_file():
                    continue
                try:
                    name = validate_session_name(path.name)
                    state = load_management_state(state_path)
                    schedule = load_work_schedule(schedule_path)
                except (ValueError, FileNotFoundError):
                    continue
                # Supplement assignments that are missing from the serialized
                # state but can be inferred from the work schedule.
                state = self._supplement_assignments(state, schedule)
                db.add(
                    SessionRow(
                        name=name,
                        project_id=project_id,
                        management_state=state.model_dump(mode="json"),
                        work_schedule=schedule.model_dump(mode="json"),
                    )
                )
            db.commit()

    def _seed_demo_session(self, project_id: int | None) -> None:
        if project_id is None or self.list_sessions() or not self.list_employees():
            return
        project = self.get_project(project_id)
        if project.final_report is None:
            return
        from api.services import create_management_session

        try:
            create_management_session(
                self,
                "demo",
                project.final_report,
                project_id=project_id,
            )
        except FileExistsError:
            return

    def list_employees(self) -> list[Employee]:
        with self._db() as db:
            rows = db.scalars(select(EmployeeRow).order_by(EmployeeRow.id)).all()
            return [Employee.model_validate(row.payload) for row in rows]

    def replace_employees(self, employees: list[Employee]) -> None:
        with self._db() as db:
            db.execute(delete(EmployeeRow))
            for employee in employees:
                db.add(
                    EmployeeRow(
                        employee_id=employee.employee_id,
                        payload=employee.model_dump(mode="json"),
                    )
                )
            db.commit()

    # ------------------------------------------------------------------ #
    # Project-scoped team members (System B)                               #
    # ------------------------------------------------------------------ #

    def list_team_members(self, project_id: int) -> list[dict]:
        with self._db() as db:
            rows = db.scalars(
                select(TeamMemberRow)
                .where(TeamMemberRow.project_id == project_id)
                .order_by(TeamMemberRow.id)
            ).all()
            return [self._team_member_dict(row) for row in rows]

    def list_effective_employees(
        self, project_id: int | None = None
    ) -> list[Employee]:
        global_employees = self.list_employees()
        if project_id is None:
            return global_employees

        project_members = self.list_team_members(project_id)
        if not project_members:
            return global_employees

        effective: list[Employee] = []
        seen_names: set[str] = set()
        seen_ids: set[str] = set()

        for tm in project_members:
            mid = tm["id"]
            name = tm["name"].strip()
            skills = [
                s.strip()
                for s in tm.get("skills", [])
                if isinstance(s, str) and s.strip()
            ] or ["General"]
            emp_id = f"TM{mid}"

            emp = Employee(
                employee_id=emp_id,
                employee_name=name,
                role=tm.get("role") or "Team Member",
                skills=skills,
                experience=float(tm.get("experience") or 0.0),
                weekly_capacity_hours=float(
                    tm.get("weekly_capacity_hours") or 40.0
                ),
                current_workload_percent=float(
                    tm.get("current_workload_percent") or 0.0
                ),
            )
            effective.append(emp)
            seen_names.add(name.casefold())
            seen_ids.add(emp_id)

        for g_emp in global_employees:
            name_key = g_emp.employee_name.strip().casefold()
            if name_key not in seen_names and g_emp.employee_id not in seen_ids:
                effective.append(g_emp)
                seen_names.add(name_key)
                seen_ids.add(g_emp.employee_id)

        return effective

    def add_team_member(
        self,
        project_id: int,
        *,
        name: str,
        role: str,
        member_type: str,
        skills: list[str],
        allocation_days: int,
        email: str = "",
    ) -> dict:
        self.initialize()
        now = utcnow()
        with self._db() as db:
            # Verify project exists
            proj = db.get(ProjectRow, project_id)
            if proj is None:
                raise FileNotFoundError(f"Project {project_id} not found")
            row = TeamMemberRow(
                project_id=project_id,
                name=name,
                email=email,
                role=role,
                member_type=member_type,
                skills=skills,
                allocation_days=allocation_days,
                created_at=now,
                updated_at=now,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._team_member_dict(row)

    def get_team_member(self, member_id: int) -> dict:
        with self._db() as db:
            row = db.get(TeamMemberRow, member_id)
            if row is None:
                raise FileNotFoundError(f"Team member {member_id} not found")
            return self._team_member_dict(row)

    def delete_team_member(self, member_id: int, project_id: int) -> None:
        with self._db() as db:
            row = db.get(TeamMemberRow, member_id)
            if row is None:
                raise FileNotFoundError(f"Team member {member_id} not found")
            if row.project_id != project_id:
                raise ValueError(
                    f"Team member {member_id} does not belong to project {project_id}"
                )
            db.delete(row)
            db.commit()

    def update_team_member(
        self,
        member_id: int,
        project_id: int,
        *,
        name: str | None = None,
        role: str | None = None,
        member_type: str | None = None,
        skills: list[str] | None = None,
        allocation_days: int | None = None,
    ) -> dict:
        self.initialize()
        now = utcnow()
        with self._db() as db:
            row = db.get(TeamMemberRow, member_id)
            if row is None:
                raise FileNotFoundError(f"Team member {member_id} not found")
            if row.project_id != project_id:
                raise ValueError(
                    f"Team member {member_id} does not belong to project {project_id}"
                )
            if name is not None:
                row.name = name
            if role is not None:
                row.role = role
            if member_type is not None:
                row.member_type = member_type
            if skills is not None:
                row.skills = skills
            if allocation_days is not None:
                row.allocation_days = allocation_days
            row.updated_at = now

            if name is not None:
                sessions = db.scalars(
                    select(SessionRow).where(SessionRow.project_id == project_id)
                ).all()
                for s_row in sessions:
                    try:
                        state_dict = s_row.management_state
                        sched_dict = s_row.work_schedule
                        target_id = f"TM{member_id}"
                        changed = False
                        if state_dict and "assignments" in state_dict:
                            for a in state_dict["assignments"]:
                                if a.get("employee_id") in (target_id, str(member_id)):
                                    a["employee_name"] = name
                                    changed = True
                        if sched_dict and "scheduled_tasks" in sched_dict:
                            for st in sched_dict["scheduled_tasks"]:
                                if st.get("employee_id") in (target_id, str(member_id)):
                                    st["employee_name"] = name
                                    changed = True
                        if changed:
                            s_row.management_state = state_dict
                            s_row.work_schedule = sched_dict
                            s_row.updated_at = now
                    except Exception:
                        pass

            db.commit()
            db.refresh(row)
            return self._team_member_dict(row)

    @staticmethod
    def _team_member_dict(row: TeamMemberRow) -> dict:
        created = row.created_at
        updated = row.updated_at
        if created and created.tzinfo is None:
            from datetime import timezone as _tz
            created = created.replace(tzinfo=_tz.utc)
        if updated and updated.tzinfo is None:
            from datetime import timezone as _tz
            updated = updated.replace(tzinfo=_tz.utc)
        return {
            "id": row.id,
            "project_id": row.project_id,
            "name": row.name,
            "role": row.role,
            "member_type": row.member_type,
            "skills": row.skills or [],
            "allocation_days": row.allocation_days,
            "experience": row.experience,
            "weekly_capacity_hours": row.weekly_capacity_hours,
            "current_workload_percent": row.current_workload_percent,
            "created_at": created.isoformat() if created else None,
            "updated_at": updated.isoformat() if updated else None,
        }

    def list_projects(self) -> list[ProjectRecord]:
        with self._db() as db:
            rows = db.scalars(select(ProjectRow).order_by(ProjectRow.id)).all()
            return [self._project_record(row) for row in rows]

    def get_project(self, project_id: int) -> ProjectRecord:
        with self._db() as db:
            row = db.get(ProjectRow, project_id)
            if row is None:
                raise FileNotFoundError(f"Project {project_id} not found")
            return self._project_record(row)

    def save_project(
        self,
        *,
        name: str,
        summary: str = "",
        description: str = "",
        final_report: FinalProjectReport | None = None,
        team_workflow: dict | None = None,
        project_id: int | None = None,
    ) -> ProjectRecord:
        self.initialize()
        now = utcnow()
        with self._db() as db:
            row = db.get(ProjectRow, project_id) if project_id else None
            if row is None:
                row = ProjectRow(
                    name=name,
                    summary=summary,
                    description=description,
                    created_at=now,
                    updated_at=now,
                    final_report=(
                        final_report.model_dump(mode="json")
                        if final_report
                        else None
                    ),
                    team_workflow=team_workflow,
                )
                if project_id is not None:
                    row.id = project_id
                db.add(row)
            else:
                row.name = name
                row.summary = summary
                row.description = description
                row.updated_at = now
                if final_report is not None:
                    row.final_report = final_report.model_dump(mode="json")
                if team_workflow is not None:
                    row.team_workflow = team_workflow
            db.commit()
            db.refresh(row)
            return self._project_record(row)

    def update_project(
        self,
        project_id: int,
        *,
        name: str | None = None,
        summary: str | None = None,
        description: str | None = None,
    ) -> ProjectRecord:
        self.initialize()
        with self._db() as db:
            row = db.get(ProjectRow, project_id)
            if row is None:
                raise FileNotFoundError(f"Project {project_id} not found")
            if name is not None:
                row.name = name
            if summary is not None:
                row.summary = summary
            if description is not None:
                row.description = description
            row.updated_at = utcnow()
            db.commit()
            db.refresh(row)
            return self._project_record(row)

    def delete_project(self, project_id: int) -> None:
        self.initialize()
        with self._db() as db:
            row = db.get(ProjectRow, project_id)
            if row is None:
                raise FileNotFoundError(f"Project {project_id} not found")
            # Unlink any session that referenced this project
            sessions = db.scalars(
                select(SessionRow).where(SessionRow.project_id == project_id)
            ).all()
            for s in sessions:
                s.project_id = None
            # Clean up child rows in other tables if any exist
            for tbl in (
                TaskAssigneeRow,
                ProgressUpdateRow,
                DeadlineChangeRow,
                TaskRow,
                TeamMemberRow,
                ProjectMemberRow,
                InvitationRow,
                ReportRow,
                ActivityLogRow,
            ):
                db.execute(delete(tbl).where(tbl.project_id == project_id))
            db.delete(row)
            db.commit()

    def list_sessions(self) -> list[SessionSummary]:
        with self._db() as db:
            rows = db.scalars(
                select(SessionRow).order_by(SessionRow.updated_at.desc())
            ).all()
            summaries = []
            for row in rows:
                state = ProjectManagementState.model_validate(row.management_state)
                summaries.append(
                    SessionSummary(
                        name=row.name,
                        project_id=row.project_id,
                        project_name=state.plan.project_name,
                        task_count=len(state.plan.tasks),
                        updated_at=row.updated_at,
                    )
                )
            return summaries

    def get_session(self, name: str) -> SessionRecord:
        name = validate_session_name(name)
        with self._db() as db:
            row = db.scalar(select(SessionRow).where(SessionRow.name == name))
            if row is None:
                raise FileNotFoundError(f"Session '{name}' not found")
            return self._session_record(row)

    def save_session(
        self,
        name: str,
        management_state: ProjectManagementState,
        work_schedule: WorkSchedule,
        project_id: int | None = None,
    ) -> SessionRecord:
        name = validate_session_name(name)
        self.initialize()
        with self._db() as db:
            row = db.scalar(select(SessionRow).where(SessionRow.name == name))
            now = utcnow()
            if row is None:
                row = SessionRow(
                    name=name,
                    project_id=project_id,
                    created_at=now,
                    updated_at=now,
                    management_state=management_state.model_dump(mode="json"),
                    work_schedule=work_schedule.model_dump(mode="json"),
                )
                db.add(row)
            else:
                row.updated_at = now
                row.management_state = management_state.model_dump(mode="json")
                row.work_schedule = work_schedule.model_dump(mode="json")
                if project_id is not None:
                    row.project_id = project_id
            db.commit()
            db.refresh(row)
            return self._session_record(row)

    def _project_record(self, row: ProjectRow) -> ProjectRecord:
        created = row.created_at
        if created and created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        updated = getattr(row, "updated_at", None) or created
        if updated and updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        return ProjectRecord(
            id=row.id,
            name=row.name,
            summary=row.summary,
            description=row.description,
            created_at=created,
            updated_at=updated,
            final_report=(
                FinalProjectReport.model_validate(row.final_report)
                if row.final_report
                else None
            ),
            team_workflow=row.team_workflow,
        )

    def _session_record(self, row: SessionRow) -> SessionRecord:
        created = row.created_at
        updated = row.updated_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        return SessionRecord(
            name=row.name,
            project_id=row.project_id,
            created_at=created,
            updated_at=updated,
            management_state=ProjectManagementState.model_validate(
                row.management_state
            ),
            work_schedule=WorkSchedule.model_validate(row.work_schedule),
        )
