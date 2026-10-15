
import pytest

from schemas.work_schedule import (
    WorkSchedule,
    ScheduledTask,
    WeeklyAllocation,
)
from utils.schedule_persistence import (
    save_work_schedule,
    load_work_schedule,
)


def make_schedule():
    return WorkSchedule(
        scheduled_tasks=[
            ScheduledTask(
                task_id=1,
                task_title="Build API",
                employee_id="EMP001",
                employee_name="Rahul",
                total_estimated_hours=8,
                weekly_allocations=[
                    WeeklyAllocation(
                        week=1,
                        allocated_hours=8,
                    )
                ],
                start_week=1,
                completion_week=1,
                assignment_reason="Python skill match",
            )
        ],
        unscheduled_tasks=[],
    )


def test_save_and_load_schedule(tmp_path):
    original = make_schedule()
    path = tmp_path / "sessions" / "schedule.json"

    save_work_schedule(original, path)
    restored = load_work_schedule(path)

    assert restored == original


def test_load_missing_schedule_raises_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_work_schedule(tmp_path / "missing.json")


def test_load_invalid_json_raises_error(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text("{invalid", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid work schedule JSON"):
        load_work_schedule(path)


def test_load_invalid_schedule_data_raises_error(tmp_path):
    path = tmp_path / "invalid_schedule.json"
    path.write_text('{"unexpected": "data"}', encoding="utf-8")

    with pytest.raises(ValueError, match="Work schedule data is invalid"):
        load_work_schedule(path)
