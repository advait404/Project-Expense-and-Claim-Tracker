"""SQLAlchemy ORM models for the expense tracking system.

Defines three main entities: Project (enclosing context), Income (manually entered),
and Expense (from manual entry or PDF import). All date fields are stored as ISO 8601
strings (YYYY-MM-DD) for portability. Note: is_claimed is stored as a String column
('true'/'false') for SQLite compatibility, but is treated as a boolean in route logic.
"""

from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime

from .database import Base
from datetime import datetime


class Project(Base):
    """Project entity: a top-level container for expenses and income.

    Attributes:
        id: Auto-incrementing primary key.
        name: Unique project identifier (indexed for fast lookup). Must be unique across all projects.
        description: Optional text describing the project.
        start_date: ISO 8601 date string (YYYY-MM-DD), optional.
        end_date: ISO 8601 date string (YYYY-MM-DD), optional.
        budget: Optional floating-point budget amount in MYR.
        status: One of 'active', 'on_hold', 'closed'. Defaults to 'active'.
    """

    __tablename__ = "projects"

    id: int = Column(Integer, primary_key=True, index=True)
    name: str = Column(String, unique=True, index=True)
    description: str | None = Column(String, nullable=True)
    start_date: str | None = Column(String, nullable=True)
    end_date: str | None = Column(String, nullable=True)
    budget: float | None = Column(Float, nullable=True)
    status: str = Column(String, default="active")


class Income(Base):
    """Income entity: always manually entered, never derived from PDF.

    Attributes:
        id: Auto-incrementing primary key.
        project_id: Foreign key to projects.id (indexed for lookup by project).
        date: ISO 8601 date string (YYYY-MM-DD).
        source: Description of income source (e.g., 'Client Payment', 'Grant').
        amount: Positive floating-point value in the specified currency.
        currency: Currency code (e.g., 'MYR', 'USD').
        notes: Optional text annotation.
    """

    __tablename__ = "income"

    id: int = Column(Integer, primary_key=True, index=True)
    project_id: int = Column(Integer, ForeignKey("projects.id"), index=True)
    date: str = Column(String)
    source: str = Column(String)
    amount: float = Column(Float)
    currency: str = Column(String)
    notes: str | None = Column(String, nullable=True)


class Expense(Base):
    """Expense entity: from manual entry or PDF import, can be claimed or unclaimed.

    Attributes:
        id: Auto-incrementing primary key.
        project_id: Foreign key to projects.id (indexed for lookup by project).
        date: ISO 8601 date string (YYYY-MM-DD).
        vendor: Merchant or vendor name, truncated to 100 chars on PDF import.
        description: Optional full transaction description.
        amount: Absolute value of the transaction in the specified currency.
        currency: Currency code (e.g., 'MYR', 'USD').
        category: Expense category (e.g., 'Travel', 'Meals', 'Equipment').
        is_claimed: IMPORTANT - stored as String column with values 'true' or 'false' for SQLite
                   compatibility, but treated as a boolean in route logic. Default is 'false'.
        claimed_date: ISO 8601 date string when the expense was marked as claimed (optional).
        notes: Optional text annotation.
        source: One of 'manual' (user-entered) or 'pdf' (extracted from bank statement). Defaults to 'manual'.
        currency_conversion_type: One of 'native' (MYR, no conversion), 'converted_by_bank' (bank converted),
                                  or 'converted_by_system' (future use for system-driven conversion).
        original_value: Amount in the original currency before conversion (nullable, only for converted transactions).
        original_currency: The original currency code before conversion (nullable).
        fx_rate: Exchange rate used for conversion (nullable).
        fx_rate_timestamp: ISO 8601 date string when the FX rate was obtained (nullable, typically transaction date).
    """

    __tablename__ = "expenses"

    id: int = Column(Integer, primary_key=True, index=True)
    project_id: int = Column(Integer, ForeignKey("projects.id"), index=True)
    date: str = Column(String)
    vendor: str = Column(String)
    description: str | None = Column(String, nullable=True)
    amount: float = Column(Float)
    currency: str = Column(String)
    category: str = Column(String)
    is_claimed: bool = Column(String, default="false")
    claimed_date: str | None = Column(String, nullable=True)
    notes: str | None = Column(String, nullable=True)
    source: str = Column(String, default="manual")
    currency_conversion_type: str | None = Column(String, nullable=True)
    original_value: float | None = Column(Float, nullable=True)
    original_currency: str | None = Column(String, nullable=True)
    fx_rate: float | None = Column(Float, nullable=True)
    fx_rate_timestamp: str | None = Column(String, nullable=True)


class PdfHash(Base):
    """PDF hash storage for duplicate detection based on content.

    Attributes:
        id: Auto-incrementing primary key.
        content_hash: SHA256 hash of normalized PDF text content (unique).
        uploaded_at: ISO 8601 timestamp when the PDF was first uploaded.
        filename: Original filename of the uploaded PDF.
    """

    __tablename__ = "pdf_hashes"

    id: int = Column(Integer, primary_key=True, index=True)
    content_hash: str = Column(String, unique=True, index=True)
    uploaded_at: str = Column(String)
    filename: str | None = Column(String, nullable=True)
