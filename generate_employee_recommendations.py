import json
from pathlib import Path

from schemas.final_report import FinalProjectReport
from utils.employee_parser import parse_employee_csv
from utils.missing_skill_analyzer import analyze_missing_skills


def main():
    report_path = Path("final_report.json")
    employee_path = Path("employees.csv")
    assignment_path = Path("assignment_report.json")
    output_path = Path("employee_recommendations.json")

    for path in (report_path, employee_path, assignment_path):
        if not path.is_file():
            print(f"Error: {path} not found.")
            return

    try:
        report_data = json.loads(report_path.read_text(encoding="utf-8"))
        report = FinalProjectReport.model_validate(report_data)
        roster = parse_employee_csv(employee_path)
        assignment_data = json.loads(
            assignment_path.read_text(encoding="utf-8")
        )

        schedule = assignment_data["work_schedule"]
        scheduled_ids = {
            task["task_id"] for task in schedule["scheduled_tasks"]
        }

        result = analyze_missing_skills(
            plan=report.project_plan,
            employees=roster.employees,
            scheduled_task_ids=scheduled_ids,
            unscheduled_tasks=schedule["unscheduled_tasks"],
        )

        output_path.write_text(
            json.dumps(result, indent=2),
            encoding="utf-8",
        )

        print("\n========== EMPLOYEE RECOMMENDATIONS ==========")
        print(f"Project: {result['project_name']}")

        for item in result["recommendations"]:
            print(f"\nTask {item['task_id']}: {item['task_title']}")
            print(f"Status: {item['status']}")
            print(f"Reason: {item['reason']}")

            if item["recommended_role"]:
                print(f"Recommended role: {item['recommended_role']}")
                print("Required skills: " + ", ".join(item["required_skills"]))
                print(f"Estimated hours: {item['estimated_hours']}")

        print(f"\nReport saved to: {output_path.resolve()}")

    except (OSError, ValueError, KeyError) as error:
        print(f"Recommendation generation failed: {error}")


if __name__ == "__main__":
    main()
