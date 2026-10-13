
from pydantic import BaseModel, Field, model_validator


class Employee(BaseModel):
    employee_id: str = Field(min_length=1)
    employee_name: str = Field(min_length=1)
    role: str = Field(min_length=1)
    skills: list[str] = Field(min_length=1)
    experience: float = Field(ge=0)
    current_workload_percent: float = Field(ge=0, le=100)
    weekly_capacity_hours: float = Field(gt=0)

    @model_validator(mode="after")
    def validate_skills(self):
        self.skills = [
            skill.strip()
            for skill in self.skills
            if skill.strip()
        ]

        if not self.skills:
            raise ValueError("Employee must have at least one skill")

        return self


class EmployeeRoster(BaseModel):
    employees: list[Employee] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_employee_ids(self):
        employee_ids = [
            employee.employee_id for employee in self.employees
        ]

        if len(employee_ids) != len(set(employee_ids)):
            raise ValueError("Employee IDs must be unique")

        return self
