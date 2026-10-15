
import json
from pathlib import Path

from schemas.project_management import ProjectManagementState


def save_management_state(
    state: ProjectManagementState,
    file_path: str | Path,
) -> None:
    """Save management state to a JSON file."""

    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    serialized_state = state.model_dump_json(indent=2)

    path.write_text(
        serialized_state,
        encoding="utf-8",
    )


def load_management_state(
    file_path: str | Path,
) -> ProjectManagementState:
    """Load and validate management state from a JSON file."""

    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(
            f"Management state file not found: {path}"
        )

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError(
            f"Invalid management state JSON in {path}: {error}"
        ) from error

    try:
        return ProjectManagementState.model_validate(data)
    except Exception as error:
        raise ValueError(
            f"Management state data is invalid in {path}: {error}"
        ) from error
