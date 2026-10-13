
import json
import sys
from pathlib import Path
from collections import defaultdict, deque


REPORT_PATH = Path("final_report.json")
TOLERANCE = 0.01


class ReportValidator:
    def __init__(self, report):
        self.report = report
        self.errors = []
        self.warnings = []
        self.passed = []

    def check(self, condition, message, severity="ERROR"):
        if condition:
            self.passed.append(message)
        elif severity == "WARNING":
            self.warnings.append(message)
        else:
            self.errors.append(message)

    def validate(self):
        report = self.report

        required_sections = [
            "project_plan",
            "task_breakdowns",
            "risk_analysis",
            "schedule",
            "resource_allocation",
            "progress_report",
            "recommendations",
        ]

        for section in required_sections:
            self.check(
                section in report and isinstance(report[section], (dict, list)),
                f"Required section exists: {section}",
            )

        if any(
            section not in report
            or not isinstance(report[section], (dict, list))
            for section in required_sections
        ):
            return self

        plan = report["project_plan"]
        tasks = plan.get("tasks", [])
        breakdowns = report["task_breakdowns"]
        schedule = report["schedule"]
        allocations = report["resource_allocation"]
        progress = report["progress_report"]
        risks = report["risk_analysis"]
        recommendations = report["recommendations"]

        task_ids = [task.get("task_id") for task in tasks]
        valid_ids = set(task_ids)

        # 1. Task IDs and total effort
        self.check(
            len(task_ids) == len(set(task_ids)),
            "Project task IDs are unique",
        )

        self.check(
            all(isinstance(task_id, int) for task_id in task_ids),
            "All project tasks have integer IDs",
        )

        total_hours = sum(
            float(task.get("estimated_hours", 0)) for task in tasks
        )

        self.check(
            abs(total_hours - float(plan.get("total_estimated_hours", 0)))
            <= TOLERANCE,
            "Project total hours equal the sum of task hours",
        )

        # 2. Dependencies and cycle detection
        graph = defaultdict(list)
        indegree = {task_id: 0 for task_id in valid_ids}

        for task in tasks:
            task_id = task.get("task_id")
            dependencies = task.get("dependencies", [])

            self.check(
                len(dependencies) == len(set(dependencies)),
                f"Task {task_id} has no duplicate dependencies",
            )

            for dependency in dependencies:
                self.check(
                    dependency in valid_ids,
                    f"Task {task_id} dependency {dependency} exists",
                )

                if dependency in valid_ids:
                    graph[dependency].append(task_id)
                    indegree[task_id] += 1

                self.check(
                    dependency != task_id,
                    f"Task {task_id} does not depend on itself",
                )

        queue = deque(
            task_id
            for task_id, degree in indegree.items()
            if degree == 0
        )
        visited = 0

        while queue:
            current = queue.popleft()
            visited += 1

            for dependent in graph[current]:
                indegree[dependent] -= 1
                if indegree[dependent] == 0:
                    queue.append(dependent)

        self.check(
            visited == len(valid_ids),
            "Task dependency graph contains no cycles",
        )

        # 3. Subtask effort consistency
        breakdown_by_id = {}

        for breakdown in breakdowns:
            task_id = breakdown.get("task_id")

            self.check(
                task_id in valid_ids,
                f"Breakdown references existing task {task_id}",
            )

            self.check(
                task_id not in breakdown_by_id,
                f"Task {task_id} has at most one breakdown",
            )

            if task_id in valid_ids and task_id not in breakdown_by_id:
                breakdown_by_id[task_id] = breakdown

        for task in tasks:
            task_id = task["task_id"]
            breakdown = breakdown_by_id.get(task_id)

            if not breakdown:
                self.check(
                    False,
                    f"Task {task_id} has a breakdown",
                    "WARNING",
                )
                continue

            subtasks = breakdown.get("subtasks", [])

            self.check(
                len(subtasks) > 0,
                f"Task {task_id} has at least one subtask",
            )

            subtask_hours = sum(
                float(subtask.get("estimated_hours", 0))
                for subtask in subtasks
            )

            parent_hours = float(task.get("estimated_hours", 0))

            self.check(
                abs(subtask_hours - parent_hours) <= TOLERANCE,
                (
                    f"Task {task_id} subtask hours ({subtask_hours:g}) "
                    f"match parent hours ({parent_hours:g})"
                ),
            )

        # 4. Schedule consistency
        scheduled_tasks = schedule.get("scheduled_tasks", [])
        scheduled_by_id = {
            task.get("task_id"): task for task in scheduled_tasks
        }

        self.check(
            len(scheduled_by_id) == len(scheduled_tasks),
            "Scheduled task IDs are unique",
        )

        self.check(
            set(scheduled_by_id) == valid_ids,
            "Schedule contains exactly the project task IDs",
        )

        self.check(
            schedule.get("project_name") == plan.get("project_name"),
            "Schedule project name matches the project plan",
        )

        for task in tasks:
            task_id = task["task_id"]
            scheduled = scheduled_by_id.get(task_id)

            if not scheduled:
                continue

            self.check(
                abs(
                    float(scheduled.get("estimated_hours", 0))
                    - float(task.get("estimated_hours", 0))
                ) <= TOLERANCE,
                f"Task {task_id} hours match between plan and schedule",
            )

            start = scheduled.get("start_day", 0)
            end = scheduled.get("end_day", 0)

            self.check(
                start >= 1 and end >= start,
                f"Task {task_id} has a valid scheduled day range",
            )

            for dependency in task.get("dependencies", []):
                prerequisite = scheduled_by_id.get(dependency)

                if prerequisite:
                    self.check(
                        start > prerequisite.get("end_day", 0),
                        (
                            f"Task {task_id} starts after prerequisite "
                            f"{dependency} finishes"
                        ),
                    )

        if scheduled_tasks:
            latest_end = max(
                task.get("end_day", 0) for task in scheduled_tasks
            )
            self.check(
                schedule.get("total_duration_days") == latest_end,
                "Schedule duration matches the latest task finish day",
            )

        critical_path = schedule.get("critical_path", [])

        self.check(
            bool(critical_path)
            and all(task_id in valid_ids for task_id in critical_path),
            "Critical path contains valid project task IDs",
        )

        # 5. Resource allocation consistency
        assignments = allocations.get("assignments", [])
        assignment_ids = [
            assignment.get("task_id") for assignment in assignments
        ]

        self.check(
            len(assignment_ids) == len(set(assignment_ids)),
            "Resource assignment task IDs are unique",
        )

        self.check(
            set(assignment_ids) == valid_ids,
            "Resource allocation covers exactly the project task IDs",
        )

        task_by_id = {task["task_id"]: task for task in tasks}

        for assignment in assignments:
            task_id = assignment.get("task_id")
            task = task_by_id.get(task_id)

            if not task:
                continue

            self.check(
                abs(
                    float(assignment.get("estimated_effort_hours", 0))
                    - float(task.get("estimated_hours", 0))
                ) <= TOLERANCE,
                f"Task {task_id} allocation effort matches plan hours",
            )

        # 6. Progress report consistency
        progress_tasks = progress.get("task_progress", [])
        progress_ids = [
            item.get("task_id") for item in progress_tasks
        ]

        self.check(
            len(progress_ids) == len(set(progress_ids)),
            "Progress report task IDs are unique",
        )

        self.check(
            set(progress_ids) == valid_ids,
            "Progress report covers exactly the project task IDs",
        )

        self.check(
            progress.get("project_name") == plan.get("project_name"),
            "Progress report project name matches the plan",
        )

        self.check(
            progress.get("pending_tasks", 0)
            + progress.get("completed_tasks", 0)
            <= len(valid_ids),
            "Progress task counts do not exceed total tasks",
        )

        # 7. Cross-section project names
        for name, section in [
            ("Risk analysis", risks),
            ("Resource allocation", allocations),
            ("Recommendations", recommendations),
        ]:
            self.check(
                section.get("project_name") == plan.get("project_name"),
                f"{name} project name matches the plan",
            )

        return self

    def print_results(self):
        print("\n========== AIPlanX REPORT VALIDATION ==========\n")

        print(f"Checks passed: {len(self.passed)}")
        print(f"Errors:        {len(self.errors)}")
        print(f"Warnings:      {len(self.warnings)}")

        if self.errors:
            print("\n--- ERRORS ---")
            for error in self.errors:
                print(f"[FAIL] {error}")

        if self.warnings:
            print("\n--- WARNINGS ---")
            for warning in self.warnings:
                print(f"[WARN] {warning}")

        if not self.errors and not self.warnings:
            print("\nAll implemented validation checks passed!")

        print("\n===============================================\n")


def main():
    if not REPORT_PATH.exists():
        print(f"ERROR: Report not found: {REPORT_PATH}")
        return 2

    try:
        with REPORT_PATH.open("r", encoding="utf-8") as file:
            report = json.load(file)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: Could not read report: {exc}")
        return 2

    if not isinstance(report, dict):
        print("ERROR: The report root must be a JSON object.")
        return 2

    validator = ReportValidator(report).validate()
    validator.print_results()

    return 1 if validator.errors else 0


if __name__ == "__main__":
    sys.exit(main())
