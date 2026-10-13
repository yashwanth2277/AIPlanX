from pathlib import Path

from agents.workflow import build_project_workflow
from agents.team_workflow_builder import build_team_workflow
from utils.workflow_graph import render_mermaid


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
        plan = result.get("project_plan")
        resource_allocation = result.get("resource_allocation")

        if report is None:
            print("Error: Workflow completed without generating a final report.")
            return

        if plan is None or resource_allocation is None:
            print(
                "Error: Project plan or resource allocation "
                "is missing from the workflow result."
            )
            return

        print("\nBuilding the team workflow...")
        team_workflow = build_team_workflow(
            plan=plan,
            resource_allocation=resource_allocation,
        )
        mermaid_diagram = render_mermaid(team_workflow)

    except Exception as error:
        print("\nAIPlanX could not complete the workflow.")
        print(f"Reason: {error}")
        print("Please check your API quota, network, and configuration.")
        return

    try:
        report_path = Path("final_report.json")
        report_path.write_text(
            report.model_dump_json(indent=2),
            encoding="utf-8",
        )
        print(f"\nFinal report saved to {report_path.resolve()}")

    except OSError as error:
        print("\nThe report could not be saved.")
        print(f"Reason: {error}")
        return

    try:
        workflow_json_path = Path("team_workflow.json")
        workflow_json_path.write_text(
            team_workflow.model_dump_json(indent=2),
            encoding="utf-8",
        )

        workflow_diagram_path = Path("team_workflow.mmd")
        workflow_diagram_path.write_text(
            mermaid_diagram,
            encoding="utf-8",
        )

        print("\n========== TEAM WORKFLOW ==========")
        print(f"Mode: {team_workflow.mode}")
        print(f"Nodes: {len(team_workflow.nodes)}")
        print(f"Connections: {len(team_workflow.edges)}")
        print(f"Workflow JSON: {workflow_json_path.resolve()}")
        print(f"Workflow diagram: {workflow_diagram_path.resolve()}")

    except OSError as error:
        print("\nThe final report was saved, but a workflow file could not be saved.")
        print(f"Reason: {error}")
        return

    print("\n========== AIPlanX COMPLETE ==========")
    print("Project planning and team workflow generation completed.")


if __name__ == "__main__":
    main()