# Create a temporary file: scripts/inspect_task_split.py

import json
from pathlib import Path

data = json.loads(Path("final_report.json").read_text(encoding="utf-8"))

sections = {
    "PLAN": data["project_plan"]["tasks"],
    "BREAKDOWNS": data["task_breakdowns"],
    "SCHEDULE": data["schedule"]["scheduled_tasks"],
    "RESOURCES": data["resource_allocation"]["assignments"],
    "PROGRESS": data["progress_report"]["task_progress"],
}

for section_name, items in sections.items():
    print(f"\n{'=' * 15} {section_name} {'=' * 15}")

    for item in items:
        if isinstance(item, dict) and item.get("task_id") in (5, 6, 7, 11):
            print(json.dumps(item, indent=2))