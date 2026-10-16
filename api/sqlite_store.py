from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, delete, select
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

from api.db_models import Base, EmployeeRow, ProjectRow, SessionRow, utcnow
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
            row = ProjectRow(
                name=report.project_plan.project_name,
                summary=report.project_plan.project_summary,
                description="",
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
        with self._db() as db:
            row = db.get(ProjectRow, project_id) if project_id else None
            if row is None:
                row = ProjectRow(
                    name=name,
                    summary=summary,
                    description=description,
                    final_report=(
                        final_report.model_dump(mode="json")
                        if final_report
                        else None
                    ),
                    team_workflow=team_workflow,
                )
                db.add(row)
            else:
                row.name = name
                row.summary = summary
                row.description = description
                if final_report is not None:
                    row.final_report = final_report.model_dump(mode="json")
                if team_workflow is not None:
                    row.team_workflow = team_workflow
            db.commit()
            db.refresh(row)
            return self._project_record(row)

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
        return ProjectRecord(
            id=row.id,
            name=row.name,
            summary=row.summary,
            description=row.description,
            created_at=row.created_at,
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
