from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.orm import Session

from backend.common_constants import (
    API_ROUTER_PREFIX,
    CURRENCY_CODE_MAX_LENGTH,
    EXPENSE_CATEGORY_MAX_LENGTH,
    EXPENSE_DESCRIPTION_MAX_LENGTH,
    EXPENSE_NOTES_MAX_LENGTH,
    EXPENSE_VENDOR_MAX_LENGTH,
    INCOME_SOURCE_MAX_LENGTH,
    VALID_EXPENSE_SOURCES,
)
from backend.database import get_db
from backend.models import Expense, Income, Project


class IncomeCreate(BaseModel):
    project_id: int
    date: str
    source: str
    amount: float
    currency: str
    notes: str | None = None

    @field_validator("source")
    @classmethod
    def source_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("source must not be empty")
        if len(v) > INCOME_SOURCE_MAX_LENGTH:
            raise ValueError(f"source must be {INCOME_SOURCE_MAX_LENGTH} characters or less")
        return v.strip()

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("amount must be greater than 0")
        return v

    @field_validator("currency")
    @classmethod
    def currency_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("currency must not be empty")
        if len(v) > CURRENCY_CODE_MAX_LENGTH:
            raise ValueError(f"currency must be {CURRENCY_CODE_MAX_LENGTH} characters or less")
        return v.strip().upper()

    @field_validator("date", mode="before")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        try:
            datetime.fromisoformat(v)
            return v
        except (ValueError, TypeError) as e:
            raise ValueError("date must be in ISO format (YYYY-MM-DD)") from e

    @field_validator("notes")
    @classmethod
    def notes_max_length(cls, v: str | None) -> str | None:
        if v is not None and len(v) > EXPENSE_NOTES_MAX_LENGTH:
            raise ValueError(f"notes must be {EXPENSE_NOTES_MAX_LENGTH} characters or less")
        return v


class IncomeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    date: str
    source: str
    amount: float
    currency: str
    notes: str | None


class ExpenseCreate(BaseModel):
    project_id: int
    date: str
    vendor: str
    description: str | None = None
    amount: float
    currency: str
    category: str
    is_claimed: bool = False
    claimed_date: str | None = None
    notes: str | None = None
    source: str = "manual"
    currency_conversion_type: str | None = None
    original_value: float | None = None
    original_currency: str | None = None
    fx_rate: float | None = None
    fx_rate_timestamp: str | None = None

    @field_validator("vendor")
    @classmethod
    def vendor_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("vendor must not be empty")
        if len(v) > EXPENSE_VENDOR_MAX_LENGTH:
            raise ValueError(f"vendor must be {EXPENSE_VENDOR_MAX_LENGTH} characters or less")
        return v.strip()

    @field_validator("description")
    @classmethod
    def description_max_length(cls, v: str | None) -> str | None:
        if v is not None and len(v) > EXPENSE_DESCRIPTION_MAX_LENGTH:
            raise ValueError(f"description must be {EXPENSE_DESCRIPTION_MAX_LENGTH} characters or less")
        return v

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("amount must be greater than 0")
        return v

    @field_validator("currency")
    @classmethod
    def currency_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("currency must not be empty")
        if len(v) > CURRENCY_CODE_MAX_LENGTH:
            raise ValueError(f"currency must be {CURRENCY_CODE_MAX_LENGTH} characters or less")
        return v.strip().upper()

    @field_validator("category")
    @classmethod
    def category_not_empty(cls, v: str) -> str:
        if v is not None and not v.strip():
            raise ValueError("category must not be empty")
        if v is not None and len(v) > EXPENSE_CATEGORY_MAX_LENGTH:
            raise ValueError(f"category must be {EXPENSE_CATEGORY_MAX_LENGTH} characters or less")
        return v.strip() if v else v

    @field_validator("date", mode="before")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        try:
            datetime.fromisoformat(v)
            return v
        except (ValueError, TypeError) as e:
            raise ValueError("date must be in ISO format (YYYY-MM-DD)") from e

    @field_validator("claimed_date", mode="before")
    @classmethod
    def validate_claimed_date_format(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            datetime.fromisoformat(v)
            return v
        except (ValueError, TypeError) as e:
            raise ValueError("claimed_date must be in ISO format (YYYY-MM-DD)") from e

    @field_validator("source")
    @classmethod
    def source_valid(cls, v: str) -> str:
        if v not in VALID_EXPENSE_SOURCES:
            raise ValueError(f"source must be one of: {', '.join(sorted(VALID_EXPENSE_SOURCES))}")
        return v

    @field_validator("notes")
    @classmethod
    def notes_max_length(cls, v: str | None) -> str | None:
        if v is not None and len(v) > EXPENSE_NOTES_MAX_LENGTH:
            raise ValueError(f"notes must be {EXPENSE_NOTES_MAX_LENGTH} characters or less")
        return v

    @field_validator("original_value", "fx_rate")
    @classmethod
    def optional_numeric_positive(cls, v: float | None) -> float | None:
        if v is not None and v < 0:
            raise ValueError("numeric values must be non-negative")
        return v


class ExpenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    date: str
    vendor: str
    description: str | None
    amount: float
    currency: str
    category: str
    is_claimed: bool
    claimed_date: str | None
    notes: str | None
    source: str
    currency_conversion_type: str | None
    original_value: float | None
    original_currency: str | None
    fx_rate: float | None
    fx_rate_timestamp: str | None


class BulkClaimToggleRequest(BaseModel):
    ids: list[int]
    is_claimed: bool

    @field_validator("ids")
    @classmethod
    def ids_not_empty(cls, v: list[int]) -> list[int]:
        if not v:
            raise ValueError("ids must not be empty")
        return v


router = APIRouter(prefix=API_ROUTER_PREFIX)


@router.post("/income", response_model=IncomeResponse)
def create_income(income: IncomeCreate, db: Session = Depends(get_db)):
    logger.info(f"Creating income entry: project_id={income.project_id}, amount={income.amount} {income.currency}, source={income.source}")
    project = db.query(Project).filter(Project.id == income.project_id).first()
    if not project:
        logger.warning(f"Income creation failed: project not found: project_id={income.project_id}")
        raise HTTPException(status_code=404, detail="Project not found")
    db_income = Income(
        project_id=income.project_id,
        date=income.date,
        source=income.source,
        amount=income.amount,
        currency=income.currency,
        notes=income.notes,
    )
    db.add(db_income)
    db.commit()
    db.refresh(db_income)
    logger.info(f"Income entry created: id={db_income.id}, project_id={db_income.project_id}")
    return db_income


@router.get("/income", response_model=list[IncomeResponse])
def list_income(project_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(Income)
    if project_id is not None:
        query = query.filter(Income.project_id == project_id)
    results = query.all()
    logger.debug(f"Retrieved {len(results)} income entries" + (f" for project {project_id}" if project_id else ""))
    return results


@router.put("/income/{income_id}", response_model=IncomeResponse)
def update_income(income_id: int, income: IncomeCreate, db: Session = Depends(get_db)):
    logger.info(f"Updating income entry: id={income_id}")
    db_income = db.query(Income).filter(Income.id == income_id).first()
    if not db_income:
        logger.warning(f"Income entry not found for update: id={income_id}")
        raise HTTPException(status_code=404, detail="Income not found")
    project = db.query(Project).filter(Project.id == income.project_id).first()
    if not project:
        logger.warning(f"Income update failed: project not found: project_id={income.project_id}")
        raise HTTPException(status_code=404, detail="Project not found")
    db_income.project_id = income.project_id
    db_income.date = income.date
    db_income.source = income.source
    db_income.amount = income.amount
    db_income.currency = income.currency
    db_income.notes = income.notes
    db.commit()
    db.refresh(db_income)
    logger.info(f"Income entry updated: id={income_id}, new_amount={db_income.amount}")
    return db_income


@router.delete("/income/{income_id}")
def delete_income(income_id: int, db: Session = Depends(get_db)):
    income = db.query(Income).filter(Income.id == income_id).first()
    if not income:
        logger.warning(f"Income entry not found for deletion: id={income_id}")
        raise HTTPException(status_code=404, detail="Income not found")
    amount = income.amount
    currency = income.currency
    db.delete(income)
    db.commit()
    logger.info(f"Income entry deleted: id={income_id}, amount={amount} {currency}")
    return {"message": "Income deleted"}


@router.post("/expenses", response_model=ExpenseResponse)
def create_expense(expense: ExpenseCreate, db: Session = Depends(get_db)):
    logger.info(f"Creating expense: vendor={expense.vendor}, amount={expense.amount} {expense.currency}, project_id={expense.project_id}, source={expense.source}")
    project = db.query(Project).filter(Project.id == expense.project_id).first()
    if not project:
        logger.warning(f"Expense creation failed: project not found: project_id={expense.project_id}")
        raise HTTPException(status_code=404, detail="Project not found")
    db_expense = Expense(
        project_id=expense.project_id,
        date=expense.date,
        vendor=expense.vendor,
        description=expense.description,
        amount=expense.amount,
        currency=expense.currency,
        category=expense.category,
        is_claimed=expense.is_claimed,
        claimed_date=expense.claimed_date,
        notes=expense.notes,
        source=expense.source,
        currency_conversion_type=expense.currency_conversion_type,
        original_value=expense.original_value,
        original_currency=expense.original_currency,
        fx_rate=expense.fx_rate,
        fx_rate_timestamp=expense.fx_rate_timestamp,
    )
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    logger.info(f"Expense created: id={db_expense.id}, vendor={db_expense.vendor}")
    return db_expense


@router.get("/expenses", response_model=list[ExpenseResponse])
def list_expenses(
    project_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    category: str | None = None,
    is_claimed: bool | None = None,
    db: Session = Depends(get_db),
):
    if date_from is not None:
        try:
            datetime.fromisoformat(date_from)
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid date_from parameter: {date_from}")
            raise HTTPException(status_code=400, detail="date_from must be in ISO format (YYYY-MM-DD)") from e
    if date_to is not None:
        try:
            datetime.fromisoformat(date_to)
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid date_to parameter: {date_to}")
            raise HTTPException(status_code=400, detail="date_to must be in ISO format (YYYY-MM-DD)") from e

    query = db.query(Expense)
    filters_applied = []
    if project_id is not None:
        query = query.filter(Expense.project_id == project_id)
        filters_applied.append(f"project_id={project_id}")
    if date_from is not None:
        query = query.filter(Expense.date >= date_from)
        filters_applied.append(f"date>={date_from}")
    if date_to is not None:
        query = query.filter(Expense.date <= date_to)
        filters_applied.append(f"date<={date_to}")
    if category is not None:
        query = query.filter(Expense.category == category)
        filters_applied.append(f"category={category}")
    if is_claimed is not None:
        query = query.filter(Expense.is_claimed == is_claimed)
        filters_applied.append(f"is_claimed={is_claimed}")
    results = query.all()
    filter_str = ", ".join(filters_applied) if filters_applied else "none"
    logger.debug(f"Retrieved {len(results)} expenses with filters: {filter_str}")
    return results


@router.put("/expenses/{expense_id}", response_model=ExpenseResponse)
def update_expense(expense_id: int, expense: ExpenseCreate, db: Session = Depends(get_db)):
    logger.info(f"Updating expense: id={expense_id}")
    db_expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not db_expense:
        logger.warning(f"Expense not found for update: id={expense_id}")
        raise HTTPException(status_code=404, detail="Expense not found")
    project = db.query(Project).filter(Project.id == expense.project_id).first()
    if not project:
        logger.warning(f"Expense update failed: project not found: project_id={expense.project_id}")
        raise HTTPException(status_code=404, detail="Project not found")
    old_claimed_state = db_expense.is_claimed
    db_expense.project_id = expense.project_id
    db_expense.date = expense.date
    db_expense.vendor = expense.vendor
    db_expense.description = expense.description
    db_expense.amount = expense.amount
    db_expense.currency = expense.currency
    db_expense.category = expense.category
    db_expense.is_claimed = expense.is_claimed
    db_expense.claimed_date = expense.claimed_date
    db_expense.notes = expense.notes
    db_expense.source = expense.source
    db_expense.currency_conversion_type = expense.currency_conversion_type
    db_expense.original_value = expense.original_value
    db_expense.original_currency = expense.original_currency
    db_expense.fx_rate = expense.fx_rate
    db_expense.fx_rate_timestamp = expense.fx_rate_timestamp
    db.commit()
    db.refresh(db_expense)
    if old_claimed_state != expense.is_claimed:
        logger.info(f"Expense claim status changed: id={expense_id}, {old_claimed_state} -> {expense.is_claimed}")
    return db_expense


@router.patch("/expenses/bulk-claim-toggle", response_model=list[ExpenseResponse])
def bulk_claim_toggle(payload: BulkClaimToggleRequest, db: Session = Depends(get_db)):
    logger.info(f"Bulk claim toggle requested: {len(payload.ids)} IDs, target state: is_claimed={payload.is_claimed}")
    if not payload.ids:
        raise HTTPException(status_code=422, detail="ids must not be empty")
    expenses = db.query(Expense).filter(Expense.id.in_(payload.ids)).all()
    if len(expenses) != len(payload.ids):
        logger.warning(f"Bulk toggle: requested {len(payload.ids)} expenses but found {len(expenses)} in database")
    claimed_date = date.today().isoformat() if payload.is_claimed else None
    for exp in expenses:
        exp.is_claimed = payload.is_claimed
        exp.claimed_date = claimed_date
    db.commit()
    for exp in expenses:
        db.refresh(exp)
    logger.info(f"Bulk toggle completed: {len(expenses)} expenses updated to is_claimed={payload.is_claimed}")
    return expenses


@router.delete("/expenses/{expense_id}")
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        logger.warning(f"Expense not found for deletion: id={expense_id}")
        raise HTTPException(status_code=404, detail="Expense not found")
    vendor = expense.vendor
    amount = expense.amount
    db.delete(expense)
    db.commit()
    logger.info(f"Expense deleted: id={expense_id}, vendor={vendor}, amount={amount}")
    return {"message": "Expense deleted"}
