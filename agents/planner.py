import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

from schemas.project_plan import ProjectPlan

load_dotenv()

if not os.getenv("GROQ_API_KEY"):
    raise ValueError("GROQ_API_KEY is missing from .env")

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0,
)



def create_project_plan(project_description: str) -> ProjectPlan:
    structured_llm = llm.with_structured_output(
        ProjectPlan,
        method="json_schema",
    )

    plan = structured_llm.invoke(
        f"""
        Create a practical project plan for the following project:

        {project_description}



        Rules:
            - Generate 8 to 12 actionable tasks.
            - Give every task a unique integer task_id.
            - Include a short title and clear description.
            - Estimate positive hours for every task.
            - Set priority to High, Medium, or Low.

            - Add dependencies only when a task genuinely requires the
              output of another task before it can begin.
            - Every dependency must reference an existing task ID.
            - Do not create a single long dependency chain for convenience.
            - Allow independent tasks to run in parallel when practical.
            - Frontend development may start with mock data before the
              backend is complete.
            - Testing can begin on completed components before full integration.
            - Documentation can be developed alongside implementation.
            - Ensure the dependency graph contains no circular dependencies.

            - Identify 3 to 5 important project risks.
            - total_estimated_hours must equal the sum of all task hours.
            - Return data matching the ProjectPlan schema exactly.

            - Include a required_skills list for every task.
            - List 2 to 5 specific technical or professional skills needed
              to complete each task.
            - Use consistent skill names such as Python, FastAPI, React,
              SQL, Testing, and Machine Learning.
            - Never return an empty required_skills list.
            - Choose skills that directly match the task's work.
            - For project setup tasks, use relevant skills such as Git,
              GitHub, or Project Setup.
            - For database tasks, use SQL, PostgreSQL, or Database Design
              as appropriate.
            - For backend tasks, use Python, FastAPI, or API Design
              as appropriate.
            - For frontend tasks, use React, JavaScript, HTML, or CSS
              as appropriate.
            - For testing and deployment tasks, use Pytest, Docker,
              CI/CD, or Deployment as appropriate.

            """
    )

    return plan



if __name__ == "__main__":
    plan = create_project_plan(
        "Build a college issue reporting platform using React and FastAPI."
    )

    assert isinstance(plan, ProjectPlan)
    assert len(plan.tasks) > 0
    assert len({task.task_id for task in plan.tasks}) == len(plan.tasks)

    print("Planner validation passed!")
    print(f"Project: {plan.project_name}")
    print(f"Number of tasks: {len(plan.tasks)}")
    print(f"Estimated hours: {plan.total_estimated_hours}")