from datetime import datetime, timezone
from pathlib import Path

from schemas.employee import Employee
from schemas.final_report import FinalProjectReport
from schemas.team_workflow import TeamWorkflow
from utils.employee_parser import parse_employee_csv
from utils.management_persistence import (
    load_management_state,
    save_management_state,
)
from utils.schedule_persistence import load_work_schedule, save_work_schedule

from api.paths import (
    EMPLOYEE_PATH,
    JSON_PROJECTS_DIR,
    REPORT_PATH,
    SESSION_DIR,
    TEAM_WORKFLOW_PATH,
)
from api.records import ProjectRecord, SessionRecord, SessionSummary
from api.session_names import validate_session_name


class JsonFileStore:
    """File-backed store used by the CLI-compatible JSON path."""

    def __init__(
        self,
        *,
        employee_path: Path = EMPLOYEE_PATH,
        report_path: Path = REPORT_PATH,
        session_dir: Path = SESSION_DIR,
        projects_dir: Path = JSON_PROJECTS_DIR,
        team_workflow_path: Path = TEAM_WORKFLOW_PATH,
    ):
        self.employee_path = Path(employee_path)
        self.report_path = Path(report_path)
        self.session_dir = Path(session_dir)
        self.projects_dir = Path(projects_dir)
        self.team_workflow_path = Path(team_workflow_path)

    def initialize(self) -> None:
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.projects_dir.mkdir(parents=True, exist_ok=True)

    def import_demo_data(self) -> None:
        self.initialize()
        if self.list_projects() or not self.report_path.is_file():
            return
        report = FinalProjectReport.model_validate_json(
            self.report_path.read_text(encoding="utf-8")
        )
        team_workflow = None
        if self.team_workflow_path.is_file():
            team_workflow = TeamWorkflow.model_validate_json(
                self.team_workflow_path.read_text(encoding="utf-8")
            ).model_dump(mode="json")
        self.save_project(
            name=report.project_plan.project_name,
            summary=report.project_plan.project_summary,
            description="",
            final_report=report,
            team_workflow=team_workflow,
            project_id=1,
        )

    def list_employees(self) -> list[Employee]:
        if not self.employee_path.is_file():
            return []
        return parse_employee_csv(self.employee_path).employees

    def replace_employees(self, employees: list[Employee]) -> None:
        raise NotImplementedError(
            "JSON store keeps employees in CSV; update employees.csv instead."
        )

    def _project_path(self, project_id: int) -> Path:
        return self.projects_dir / f"{project_id}.json"

    def _next_project_id(self) -> int:
        ids = [
            int(path.stem)
            for path in self.projects_dir.glob("*.json")
            if path.stem.isdigit()
        ]
        return max(ids, default=0) + 1

    def list_projects(self) -> list[ProjectRecord]:
        records = []
        for path in sorted(self.projects_dir.glob("*.json")):
            if path.stem.isdigit():
                records.append(
                    ProjectRecord.model_validate_json(
                        path.read_text(encoding="utf-8")
                    )
                )
        return records

    def get_project(self, project_id: int) -> ProjectRecord:
        path = self._project_path(project_id)
        if not path.is_file():
            raise FileNotFoundError(f"Project {project_id} not found")
        return ProjectRecord.model_validate_json(
            path.read_text(encoding="utf-8")
        )

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
        if project_id is None:
            project_id = self._next_project_id()
        now = datetime.now(timezone.utc)
        existing = None
        path = self._project_path(project_id)
        if path.is_file():
            existing = ProjectRecord.model_validate_json(
                path.read_text(encoding="utf-8")
            )
        record = ProjectRecord(
            id=project_id,
            name=name,
            summary=summary,
            description=description,
            created_at=existing.created_at if existing else now,
            final_report=final_report,
            team_workflow=team_workflow,
        )
        path.write_text(record.model_dump_json(indent=2), encoding="utf-8")
        if final_report is not None and project_id == 1:
            self.report_path.write_text(
                final_report.model_dump_json(indent=2),
                encoding="utf-8",
            )
        return record

    def list_sessions(self) -> list[SessionSummary]:
        summaries = []
        if not self.session_dir.is_dir():
            return summaries
        for path in sorted(self.session_dir.iterdir()):
            state_path = path / "management_state.json"
            if not path.is_dir() or not state_path.is_file():
                continue
            try:
                record = self.get_session(path.name)
            except (ValueError, FileNotFoundError):
                continue
            summaries.append(
                SessionSummary(
                    name=record.name,
                    project_id=record.project_id,
                    project_name=record.management_state.plan.project_name,
                    task_count=len(record.management_state.plan.tasks),
                    updated_at=record.updated_at,
                )
            )
        return summaries

    def get_session(self, name: str) -> SessionRecord:
        name = validate_session_name(name)
        session_path = self.session_dir / name
        state = load_management_state(session_path / "management_state.json")
        schedule = load_work_schedule(session_path / "work_schedule.json")
        stamp = datetime.fromtimestamp(
            (session_path / "management_state.json").stat().st_mtime,
            tz=timezone.utc,
        )
        project_id = None
        meta_path = session_path / "meta.json"
        if meta_path.is_file():
            import json

            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            project_id = meta.get("project_id")
        return SessionRecord(
            name=name,
            project_id=project_id,
            created_at=stamp,
            updated_at=stamp,
            management_state=state,
            work_schedule=schedule,
        )

    def save_session(
        self,
        name: str,
        management_state,
        work_schedule,
        project_id: int | None = None,
    ) -> SessionRecord:
        name = validate_session_name(name)
        self.initialize()
        session_path = self.session_dir / name
        save_management_state(
            management_state,
            session_path / "management_state.json",
        )
        save_work_schedule(
            work_schedule,
            session_path / "work_schedule.json",
        )
        if project_id is not None:
            import json

            (session_path / "meta.json").write_text(
                json.dumps({"project_id": project_id}),
                encoding="utf-8",
            )
        now = datetime.now(timezone.utc)
        return SessionRecord(
            name=name,
            project_id=project_id,
            created_at=now,
            updated_at=now,
            management_state=management_state,
            work_schedule=work_schedule,
        )
