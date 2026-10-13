
from pydantic import BaseModel, Field, model_validator


class Task(BaseModel):
    task_id: int
    title: str
    description: str
    required_skills: list[str] = Field(default_factory=list)
    estimated_hours: float = Field(gt=0)
    priority: str
    dependencies: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_required_skills(self):
        self.required_skills = [
            skill.strip()
            for skill in self.required_skills
            if skill.strip()
        ]

        if not self.required_skills:
            raise ValueError(
                f"Task {self.task_id} must have at least one required skill"
            )

        return self


class ProjectPlan(BaseModel):
    project_name: str
    project_summary: str
    total_estimated_hours: float
    tasks: list[Task] = Field(min_length=1)
    risks: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_task_ids(self):
        task_ids = [task.task_id for task in self.tasks]

        if len(task_ids) != len(set(task_ids)):
            raise ValueError("Task IDs must be unique")

        return self

    @model_validator(mode="after")
    def validate_task_dependencies(self):
        task_ids = {task.task_id for task in self.tasks}

        for task in self.tasks:
            for dependency_id in task.dependencies:
                if dependency_id == task.task_id:
                    raise ValueError(
                        f"Task {task.task_id} cannot depend on itself"
                    )

                if dependency_id not in task_ids:
                    raise ValueError(
                        f"Task {task.task_id} depends on "
                        f"non-existent task {dependency_id}"
                    )

        return self

    @model_validator(mode="after")
    def validate_no_circular_dependencies(self):
        dependencies = {
            task.task_id: task.dependencies
            for task in self.tasks
        }

        visited = set()
        visiting = set()

        def has_cycle(task_id):
            if task_id in visiting:
                return True

            if task_id in visited:
                return False

            visiting.add(task_id)

            for dependency_id in dependencies[task_id]:
                if has_cycle(dependency_id):
                    return True

            visiting.remove(task_id)
            visited.add(task_id)
            return False

        for task_id in dependencies:
            if has_cycle(task_id):
                raise ValueError(
                    "Task dependencies must not contain a cycle"
                )

        return self

    @model_validator(mode="after")
    def validate_total_estimated_hours(self):
        actual_total = sum(
            task.estimated_hours for task in self.tasks
        )

        if abs(actual_total - self.total_estimated_hours) > 0.01:
            raise ValueError(
                "Total estimated hours must equal the sum of task hours"
            )

        return self
