
import csv
from pathlib import Path

from schemas.employee import Employee, EmployeeRoster


REQUIRED_COLUMNS = {
    "employee_id",
    "employee_name",
    "role",
    "skills",
    "experience",
    "current_workload_percent",
    "weekly_capacity_hours",
}


def parse_employee_csv(file_path: str | Path) -> EmployeeRoster:
    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(f"Employee file not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError("CSV file is empty or has no header row")

        reader.fieldnames = [
            name.strip().lower() for name in reader.fieldnames
        ]

        missing_columns = REQUIRED_COLUMNS - set(reader.fieldnames)

        if missing_columns:
            raise ValueError(
                "Missing required columns: "
                + ", ".join(sorted(missing_columns))
            )

        employees = []

        for row_number, row in enumerate(reader, start=2):
            try:
                skills = [
                    skill.strip()
                    for skill in row["skills"].split(";")
                    if skill.strip()
                ]


                employee = Employee(
                    employee_id=row["employee_id"].strip(),
                    employee_name=row["employee_name"].strip(),
                    role=row["role"].strip(),
                    skills=skills,
                    experience=float(row["experience"]),
                    current_workload_percent=float(
                        row["current_workload_percent"]
                    ),
                    weekly_capacity_hours=float(
                        row["weekly_capacity_hours"]
                    ),
                )



                employees.append(employee)

            except (ValueError, AttributeError) as error:
                raise ValueError(
                    f"Invalid employee data on CSV row {row_number}: {error}"
                ) from error

    return EmployeeRoster(employees=employees)
