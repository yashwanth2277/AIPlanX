from threading import Lock
from typing import Any
from uuid import uuid4

JOBS: dict[str, dict[str, Any]] = {}
_LOCK = Lock()


def create_job(payload: dict[str, Any] | None = None) -> str:
    job_id = str(uuid4())
    record = {
        "id": job_id,
        "status": "queued",
        "error": None,
        "project_id": None,
        "session_name": None,
    }
    if payload:
        record.update(payload)
    with _LOCK:
        JOBS[job_id] = record
    return job_id


def update_job(job_id: str, **changes: Any) -> dict[str, Any]:
    with _LOCK:
        current = JOBS.get(job_id)
        if current is None:
            raise KeyError(job_id)
        current.update(changes)
        return dict(current)


def get_job(job_id: str) -> dict[str, Any]:
    with _LOCK:
        current = JOBS.get(job_id)
        if current is None:
            raise KeyError(job_id)
        return dict(current)
