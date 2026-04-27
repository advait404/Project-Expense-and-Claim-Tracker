from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.common_constants import (
    API_ROUTER_PREFIX,
    PROJECT_DESCRIPTION_MAX_LENGTH,
    PROJECT_NAME_MAX_LENGTH,
    VALID_PROJECT_STATUSES,
)
from backend.database import get_db
from backend.models import Expense, Income, Project


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    budget: float | None = None
    status: str = "active"

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("name must not be empty")
        if len(v) > PROJECT_NAME_MAX_LENGTH:
            raise ValueError(f"name must be {PROJECT_NAME_MAX_LENGTH} characters or less")
        return v.strip()

    @field_validator("description")
    @classmethod
    def description_max_length(cls, v: str | None) -> str | None:
        if v is not None and len(v) > PROJECT_DESCRIPTION_MAX_LENGTH:
            raise ValueError(f"description must be {PROJECT_DESCRIPTION_MAX_LENGTH} characters or less")
        return v

    @field_validator("budget")
    @classmethod
    def budget_positive(cls, v: float | None) -> float | None:
        if v is not None and v < 0:
            raise ValueError("budget must be non-negative")
        return v

    @field_validator("status")
    @classmethod
    def status_valid(cls, v: str) -> str:
        if v not in VALID_PROJECT_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(sorted(VALID_PROJECT_STATUSES))}")
        return v

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def validate_date_format(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            datetime.fromisoformat(v)
            return v
        except (ValueError, TypeError) as e:
            raise ValueError("dates must be in ISO format (YYYY-MM-DD)") from e


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    start_date: str | None
    end_date: str | None
    budget: float | None
    status: str


class ProjectSummary(BaseModel):
    project_id: int
    project_name: str
    total_income: float
    total_expenses: float
    net_position: float
    total_claimed: float
    total_unclaimed: float


router = APIRouter(prefix=API_ROUTER_PREFIX)


@router.get("/projects/summary", response_model=list[ProjectSummary])
def get_projects_summary(db: Session = Depends(get_db)):
    logger.debug("Fetching project summary")
    projects = db.query(Project).all()
    logger.info(f"Retrieved {len(projects)} projects for summary computation")
    summaries = []

    for project in projects:
        income_total = db.query(func.sum(Income.amount)).filter(Income.project_id == project.id).scalar() or 0

        expense_total = db.query(func.sum(Expense.amount)).filter(Expense.project_id == project.id).scalar() or 0

        claimed_total = db.query(func.sum(Expense.amount)).filter(Expense.project_id == project.id, Expense.is_claimed == True).scalar() or 0

        unclaimed_total = db.query(func.sum(Expense.amount)).filter(Expense.project_id == project.id, Expense.is_claimed == False).scalar() or 0

        summaries.append(
            ProjectSummary(
                project_id=project.id,
                project_name=project.name,
                total_income=income_total,
                total_expenses=expense_total,
                net_position=income_total - expense_total,
                total_claimed=claimed_total,
                total_unclaimed=unclaimed_total,
            )
        )

    if len(summaries) == 0:
        logger.warning("No projects found in summary query")

    return summaries


@router.post("/projects", response_model=ProjectResponse)
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    logger.info(f"Creating new project: {project.name}")
    db_project = Project(
        name=project.name,
        description=project.description,
        start_date=project.start_date,
        end_date=project.end_date,
        budget=project.budget,
        status=project.status,
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    logger.info(f"Project created successfully: id={db_project.id}, name={db_project.name}")
    return db_project


@router.get("/projects", response_model=list[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).all()
    logger.debug(f"Retrieved {len(projects)} projects")
    return projects


@router.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        logger.warning(f"Project not found: id={project_id}")
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/projects/{project_id}", response_model=ProjectResponse)
def update_project(project_id: int, project: ProjectCreate, db: Session = Depends(get_db)):
    logger.info(f"Updating project: id={project_id}")
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        logger.warning(f"Project not found for update: id={project_id}")
        raise HTTPException(status_code=404, detail="Project not found")
    db_project.name = project.name
    db_project.description = project.description
    db_project.start_date = project.start_date
    db_project.end_date = project.end_date
    db_project.budget = project.budget
    db_project.status = project.status
    db.commit()
    db.refresh(db_project)
    logger.info(f"Project updated successfully: id={project_id}, name={db_project.name}")
    return db_project


@router.delete("/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        logger.warning(f"Project not found for deletion: id={project_id}")
        raise HTTPException(status_code=404, detail="Project not found")
    project_name = project.name

    expenses = db.query(Expense).filter(Expense.project_id == project_id).all()
    expense_count = len(expenses)
    for expense in expenses:
        db.delete(expense)
    logger.info(f"Deleted {expense_count} expenses for project {project_id}")

    income_records = db.query(Income).filter(Income.project_id == project_id).all()
    income_count = len(income_records)
    for income in income_records:
        db.delete(income)
    logger.info(f"Deleted {income_count} income records for project {project_id}")

    db.delete(project)
    db.commit()
    logger.info(f"Project deleted: id={project_id}, name={project_name}, expenses_deleted={expense_count}, income_deleted={income_count}")
    return {"message": "Project deleted"}
