
from pathlib import Path

from agents.workflow import build_project_workflow


def main():
    project_description = input(
        "Describe the project you want AIPlanX to plan: "
    ).strip()

    if not project_description:
        print("Project description cannot be empty.")
        return

    try:
        workflow = build_project_workflow()

        print("\nGenerating your project plan...")
        result = workflow.invoke({
            "project_description": project_description
        })

        report = result.get("final_report")

        if report is None:
            print("Error: Workflow completed without generating a final report.")
            return

    except Exception as error:
        print("\nAIPlanX could not complete the workflow.")
        print(f"Reason: {error}")
        print("Please check your API quota, network, and configuration.")
        return

    try:
        output_path = Path("final_report.json")

        output_path.write_text(
            report.model_dump_json(indent=2),
            encoding="utf-8",
        )

        print("\n========== AIPlanX FINAL REPORT ==========\n")
        print(f"Final report saved to {output_path.resolve()}")

    except OSError as error:
        print("\nThe report was generated but could not be saved.")
        print(f"Reason: {error}")


if __name__ == "__main__":
    main()
