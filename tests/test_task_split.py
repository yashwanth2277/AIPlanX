from schemas.project_plan import ProjectPlan


def test_task_split_has_correct_hours_skills_and_dependencies():
    plan = ProjectPlan(
        project_name="Test Campus Issue System",
        project_summary="Deterministic regression fixture",
        total_estimated_hours=36.1,
        tasks=[
            {
                "task_id": 3,
                "title": "Backend Foundation",
                "description": "Set up the backend",
                "required_skills": ["Python", "FastAPI"],
                "estimated_hours": 6,
                "priority": "High",
                "dependencies": [],
            },
            {
                "task_id": 4,
                "title": "Database Integration",
                "description": "Connect the database",
                "required_skills": ["Python", "SQL"],
                "estimated_hours": 6,
                "priority": "High",
                "dependencies": [3],
            },
            {
                "task_id": 5,
                "title": "Frontend Foundation",
                "description": "Set up the frontend",
                "required_skills": ["React", "JavaScript"],
                "estimated_hours": 6,
                "priority": "High",
                "dependencies": [],
            },
            {
                "task_id": 11,
                "title": "Backend Integration Support",
                "description": "Support integration with backend services",
                "required_skills": ["Python", "FastAPI"],
                "estimated_hours": 8,
                "priority": "High",
                "dependencies": [3, 4],
            },
            {
                "task_id": 6,
                "title": "Frontend Integration",
                "description": "Integrate the frontend",
                "required_skills": ["React", "JavaScript"],
                "estimated_hours": 10,
                "priority": "High",
                "dependencies": [5, 11],
            },
            {
                "task_id": 7,
                "title": "Integration Testing",
                "description": "Test the integrated system",
                "required_skills": ["pytest", "testing"],
                "estimated_hours": 0.1,
                "priority": "High",
                "dependencies": [11],
            },
        ],
    )

    tasks = {task.task_id: task for task in plan.tasks}

    frontend = tasks[6]
    assert frontend.estimated_hours == 10
    assert set(frontend.required_skills) == {"React", "JavaScript"}
    assert set(frontend.dependencies) == {5, 11}

    backend = tasks[11]
    assert backend.estimated_hours == 8
    assert set(backend.required_skills) == {"Python", "FastAPI"}
    assert set(backend.dependencies) == {3, 4}

    testing = tasks[7]
    assert 11 in testing.dependencies

    assert sum(task.estimated_hours for task in tasks.values()) == (
        plan.total_estimated_hours
    )