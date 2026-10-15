
import json
from pathlib import Path

from schemas.work_schedule import WorkSchedule


def save_work_schedule(
    schedule: WorkSchedule,
    file_path: str | Path,
) -> None:
    """Save the current work schedule as JSON."""

    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(
        schedule.model_dump_json(indent=2),
        encoding="utf-8",
    )


def load_work_schedule(
    file_path: str | Path,
) -> WorkSchedule:
    """Load and validate a saved work schedule."""

    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(
            f"Work schedule file not found: {path}"
        )

    try:
        data = json.loads(
            path.read_text(encoding="utf-8")
        )
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError(
            f"Invalid work schedule JSON in {path}: {error}"
        ) from error

    if not isinstance(data, dict) or not {
        "scheduled_tasks",
        "unscheduled_tasks",
    }.issubset(data):
        raise ValueError(
            f"Work schedule data is invalid in {path}: "
            "expected scheduled_tasks and unscheduled_tasks"
        )

    try:
        return WorkSchedule.model_validate(data)
    except Exception as error:
        raise ValueError(
            f"Work schedule data is invalid in {path}: {error}"
        ) from error
