
import json
from pathlib import Path

from schemas.final_report import FinalProjectReport
from schemas.assignment import AssignmentReport, TaskAssignment, UnassignedTask
from utils.employee_parser import parse_employee_csv
from utils.skill_matcher import calculate_skill_match
from utils.work_scheduler import build_work_schedule


def main():
    report_path = Path("final_report.json")
    employee_path = Path("employees.csv")
    output_path = Path("assignment_report.json")

    if not report_path.is_file():
        print("Error: final_report.json not found.")
        return

    if not employee_path.is_file():
        print("Error: employees.csv not found.")
        return

    try:
        report_data = json.loads(
            report_path.read_text(encoding="utf-8")
        )
        report = FinalProjectReport.model_validate(report_data)
        roster = parse_employee_csv(employee_path)

        plan = report.project_plan
        employees = roster.employees

        # The multi-week scheduler is the source of truth.
        schedule = build_work_schedule(plan, employees)

        tasks_by_id = {
            task.task_id: task for task in plan.tasks
        }
        employees_by_id = {
            employee.employee_id: employee
            for employee in employees
        }

        assignment_report = AssignmentReport()
        scheduled_ids = set()

        for scheduled in schedule.scheduled_tasks:
            task = tasks_by_id[scheduled.task_id]
            employee = employees_by_id[scheduled.employee_id]

            skill_match = calculate_skill_match(task, employee)

            # Keep the same scoring formula as the assignment engine.
            score = (
                0.65 * skill_match
                + 0.25 * (
                    1 - employee.current_workload_percent / 100
                )
                + 0.10 * min(employee.experience, 7) / 35
            )

            required_skills = {
                skill.strip().casefold()
                for skill in task.required_skills
                if skill.strip()
            }
            employee_skills = {
                skill.strip().casefold()
                for skill in employee.skills
                if skill.strip()
            }

            matched_skills = sorted(
                required_skills & employee_skills
            )
            missing_skills = sorted(
                required_skills - employee_skills
            )

            assignment_report.assignments.append(
                TaskAssignment(
                    task_id=task.task_id,
                    task_title=task.title,
                    employee_id=employee.employee_id,
                    employee_name=employee.employee_name,
                    match_score=round(score, 3),
                    assignment_reason=(
                        f"Matched skills: "
                        f"{', '.join(matched_skills) or 'None'}. "
                        f"Missing skills: "
                        f"{', '.join(missing_skills) or 'None'}. "
                        f"Skill match: {skill_match:.0%}. "
                        f"Allocated {task.estimated_hours} hours "
                        f"across weeks "
                        f"{scheduled.start_week}-"
                        f"{scheduled.completion_week}."
                    ),
                )
            )
            scheduled_ids.add(task.task_id)

        # Report each unscheduled task once, using the scheduler's reason.
        for item in schedule.unscheduled_tasks:
            task_id = item["task_id"]
            task = tasks_by_id[task_id]

            assignment_report.unassigned_tasks.append(
                UnassignedTask(
                    task_id=task_id,
                    task_title=task.title,
                    reason=item["reason"],
                )
            )

        result = {
            "project_name": plan.project_name,
            "assignments": [
                item.model_dump()
                for item in assignment_report.assignments
            ],
            "unassigned_tasks": [
                item.model_dump()
                for item in assignment_report.unassigned_tasks
            ],
            "work_schedule": schedule.model_dump(),
        }

        output_path.write_text(
            json.dumps(result, indent=2),
            encoding="utf-8",
        )

        print("\n========== AIPlanX WORKFORCE ALLOCATION ==========")
        print(f"Project: {plan.project_name}")
        print(f"Employees loaded: {len(employees)}")
        print(f"Tasks assigned: {len(assignment_report.assignments)}")
        print(
            f"Tasks unassigned: "
            f"{len(assignment_report.unassigned_tasks)}"
        )
        print(f"Tasks scheduled: {len(schedule.scheduled_tasks)}")
        print(f"Tasks unscheduled: {len(schedule.unscheduled_tasks)}")
        print(f"Report saved to: {output_path.resolve()}")

        print("\nWeekly schedule:")
        for task in schedule.scheduled_tasks:
            print(
                f"- Task {task.task_id}: {task.task_title} "
                f"-> {task.employee_name} "
                f"(Weeks {task.start_week}-{task.completion_week})"
            )

        if schedule.unscheduled_tasks:
            print("\nUnscheduled tasks:")
            for task in schedule.unscheduled_tasks:
                print(
                    f"- Task {task['task_id']}: {task['reason']}"
                )

        # Verify both report sections describe the same tasks.
        assigned_ids = {
            item.task_id
            for item in assignment_report.assignments
        }
        scheduled_ids = {
            item.task_id
            for item in schedule.scheduled_tasks
        }
        assert assigned_ids == scheduled_ids

    except (OSError, ValueError, KeyError) as error:
        print(f"\nAllocation failed: {error}")


if __name__ == "__main__":
    main()
