
import pytest

from utils.employee_parser import parse_employee_csv


def test_parses_valid_employee_csv(tmp_path):
    csv_file = tmp_path / "employees.csv"
    csv_file.write_text(
        "employee_id,employee_name,role,skills,experience,"
        "current_workload_percent,weekly_capacity_hours\n"
        "EMP001,Rahul,Developer,Python;FastAPI,3,40,40\n",
        encoding="utf-8",
    )

    roster = parse_employee_csv(csv_file)

    assert len(roster.employees) == 1
    assert roster.employees[0].employee_name == "Rahul"
    assert roster.employees[0].skills == ["Python", "FastAPI"]


def test_rejects_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        parse_employee_csv(tmp_path / "missing.csv")


def test_rejects_missing_required_columns(tmp_path):
    csv_file = tmp_path / "employees.csv"
    csv_file.write_text(
        "employee_id,employee_name\nEMP001,Rahul\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Missing required columns"):
        parse_employee_csv(csv_file)


def test_rejects_invalid_numeric_data(tmp_path):
    csv_file = tmp_path / "employees.csv"
    csv_file.write_text(
        "employee_id,employee_name,role,skills,experience,"
        "current_workload_percent,weekly_capacity_hours\n"
        "EMP001,Rahul,Developer,Python,invalid,40,40\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="CSV row 2"):
        parse_employee_csv(csv_file)


def test_rejects_empty_employee_roster(tmp_path):
    csv_file = tmp_path / "employees.csv"
    csv_file.write_text(
        "employee_id,employee_name,role,skills,experience,"
        "current_workload_percent,weekly_capacity_hours\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        parse_employee_csv(csv_file)
