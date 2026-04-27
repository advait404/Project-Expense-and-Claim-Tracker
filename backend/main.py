import asyncio
import base64
import hashlib
import json
import os
import re
import tempfile
import time
import unicodedata
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from openai import OpenAI
from pdf2image import convert_from_path
from pdfminer.high_level import extract_text
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.common_constants import (
    API_ROUTER_PREFIX,
    BANK_CONVERSION_TYPE,
    CORS_ALLOW_CREDENTIALS,
    CORS_ALLOW_HEADERS,
    CORS_ALLOW_METHODS,
    CORS_ALLOW_ORIGINS,
    DEFAULT_CATEGORY_SUGGESTION,
    DEFAULT_CURRENCY,
    DEFAULT_CURRENCY_CONVERSION_TYPE,
    MAX_PDF_FILE_SIZE,
    OPENAI_API_KEY_ENV_VAR,
    OPENAI_MAX_OUTPUT_TOKENS,
    OPENAI_MODEL,
    PDF_TEXT_EXTRACTION_HASH_ALGORITHM,
    PDF_UNICODE_NORMALIZATION_FORM,
    PDF_VENDOR_TRUNCATION_LENGTH,
    PDF_WHITESPACE_PATTERN,
    THREAD_POOL_MAX_WORKERS,
)
from backend.database import Base, engine, get_db
from backend.income_expenses import ExpenseResponse
from backend.income_expenses import router as income_expenses_router
from backend.models import Expense, PdfHash, Project
from backend.projects import router as projects_router

load_dotenv()

# Initialize database schema
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize database schema: {e!r}")
    raise

app = FastAPI()
executor = ThreadPoolExecutor(max_workers=THREAD_POOL_MAX_WORKERS)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        field = ".".join(str(x) for x in error["loc"][1:]) if len(error["loc"]) > 1 else error["loc"][0]
        message = error["msg"]
        errors.append({"field": field, "message": message})
    logger.warning(f"Validation error: {errors}")
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error", "errors": errors},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=CORS_ALLOW_CREDENTIALS,
    allow_methods=CORS_ALLOW_METHODS,
    allow_headers=CORS_ALLOW_HEADERS,
)


openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set. Please add it to .env file.")
openai_client = OpenAI(api_key=openai_api_key)
logger.info("OpenAI client initialized")


def hash_pdf_content(pdf_path: str) -> str:
    """Hash PDF content (text) for duplicate detection, ignoring metadata.

    Extracts text from PDF, normalizes it (Unicode normalization, whitespace),
    and returns SHA256 hash. This approach is robust to metadata changes
    (download date, access time) and focuses on actual content.

    Args:
        pdf_path: Path to the PDF file on disk.

    Returns:
        SHA256 hex digest of normalized PDF text content.

    Raises:
        Exception: If pdfminer text extraction fails.
    """
    logger.debug(f"Hashing PDF content: {pdf_path}")
    raw = extract_text(pdf_path)
    normalized = unicodedata.normalize(PDF_UNICODE_NORMALIZATION_FORM, raw)
    normalized = re.sub(PDF_WHITESPACE_PATTERN, " ", normalized).strip()
    content_hash = hashlib.new(PDF_TEXT_EXTRACTION_HASH_ALGORITHM, normalized.encode("utf-8")).hexdigest()
    logger.debug(f"PDF content hash computed: {content_hash}")
    return content_hash


def pdf_to_images(pdf_path: str) -> list[str]:
    """Convert PDF pages to base64-encoded PNG images using poppler.

    Uses pdf2image.convert_from_path to render each PDF page as a PIL Image,
    then encodes to base64 for API transmission. Temporary PNG files are cleaned up
    immediately after encoding.

    Args:
        pdf_path: Path to the PDF file on disk.

    Returns:
        List of base64-encoded PNG image strings, one per page.

    Raises:
        Exception: If pdf2image conversion fails (e.g. poppler not installed, corrupt PDF).
    """
    logger.debug(f"Converting PDF to images: {pdf_path}")
    images = convert_from_path(pdf_path)
    logger.info(f"Converted {len(images)} pages from PDF")
    encoded_images = []

    for idx, img in enumerate(images):
        with tempfile.NamedTemporaryFile(delete=True, suffix=".png") as buffered:
            img.save(buffered.name, format="PNG")
            buffered.flush()
            logger.debug(f"Saved page {idx + 1} to temporary file: {buffered.name}")

            with open(buffered.name, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
                encoded_images.append(b64)

    if len(encoded_images) == 0:
        logger.warning("PDF conversion produced 0 images")

    return encoded_images


def extract_transactions(images_b64: list[str]) -> str:
    """Extract transaction data from PDF page images using OpenAI vision model.

    Sends a multimodal prompt with all page images to the OpenAI API and requests
    structured extraction of transaction details (date, description, amount, credit flag).
    This is the first of two OpenAI calls in the PDF import pipeline.

    Args:
        images_b64: List of base64-encoded PNG image strings.

    Returns:
        Raw text output from the OpenAI API (may be semi-structured or plain text).

    Raises:
        Exception: If OpenAI API call fails (auth, rate limit, network, etc.).
    """
    logger.debug(f"Starting OpenAI vision extraction for {len(images_b64)} images")
    start_time = time.time()

    content = []

    content.append(
        {
            "type": "input_text",
            "text": "Extract all transactions from this bank credit card statement. " "There are multiple images and they all belong to the same statement. " "For each transaction return: date, description, amount_myr (the final MYR amount charged), " "original_currency (if shown, e.g. 'USD'; null if native MYR), original_value (amount in original currency, or null), " "fx_rate (exchange rate if shown, or null), and is_credit (true if marked CR). " "Example: '18/03 AMAZON WEB SERVICES AWS USD 95.201 USD = RM 4.723 RM449.72' " "→ amount_myr=449.72, original_currency='USD', original_value=95.201, fx_rate=4.723. " "Ignore summaries, totals, and non-transaction rows.",
        }
    )

    for img in images_b64:
        content.append({"type": "input_image", "image_url": f"data:image/png;base64,{img}"})

    response = openai_client.responses.create(model=OPENAI_MODEL, input=[{"role": "user", "content": content}], max_output_tokens=OPENAI_MAX_OUTPUT_TOKENS)

    output_text = response.output_text
    elapsed = time.time() - start_time
    logger.info(f"OpenAI vision extraction completed in {elapsed:.2f}s, output length: {len(output_text)} chars")

    if not output_text or len(output_text) == 0:
        logger.warning("OpenAI vision extraction returned empty result")

    return output_text


def cleanup_transactions(raw_text: str) -> list[dict]:
    """Clean and normalize raw extracted transaction text into structured JSON.

    Sends the raw OCR/vision output to OpenAI for JSON normalization. This is the second
    of two OpenAI calls in the PDF import pipeline. Attempts to parse the response as JSON.

    IMPORTANT: If JSON parsing fails, this function silently returns an empty list with no
    warning logged. This is a silent failure point — if OpenAI returns malformed JSON
    (e.g. wrapped in markdown fences, incomplete, syntax errors), the caller gets an empty
    list and may not realize the pipeline failed. Always check transaction count at the
    route level and log a warning if it's unexpectedly low.

    Args:
        raw_text: Raw text output from extract_transactions (semi-structured or plain text).

    Returns:
        List of transaction dicts matching the schema {date, description, amount, currency, is_credit},
        or empty list if JSON parsing fails or OpenAI returns non-list JSON.
    """
    logger.debug(f"Starting transaction cleanup and normalization, input length: {len(raw_text)} chars")
    start_time = time.time()

    prompt = f"""
Clean and normalize the following extracted bank statement data.

Rules:
- Output ONLY valid JSON (no explanation, no markdown)
- Structure:
[
  {{
    "date": "YYYY-MM-DD",
    "description": "string",
    "amount_myr": float,
    "original_currency": "USD or EUR or null",
    "original_value": float_or_null,
    "fx_rate": float_or_null,
    "is_credit": boolean
  }}
]
- Remove summaries, totals, and non-transaction rows
- Ignore zero-value rows
- Normalize date format
- amount_myr is always the final amount in MYR charged/credited

DATA:
{raw_text}
"""

    response = openai_client.responses.create(model=OPENAI_MODEL, input=prompt, max_output_tokens=OPENAI_MAX_OUTPUT_TOKENS)

    cleaned_text = response.output_text.strip()
    elapsed = time.time() - start_time
    logger.debug(f"OpenAI normalization completed in {elapsed:.2f}s, output length: {len(cleaned_text)} chars")

    try:
        data = json.loads(cleaned_text)
        if isinstance(data, list):
            logger.info(f"Successfully parsed {len(data)} transactions from cleaned JSON")
            return data
        logger.warning(f"OpenAI returned valid JSON but not a list (type: {type(data).__name__}), returning empty list")
        return []
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse OpenAI normalization output as JSON. " f"Error: {e.msg} at line {e.lineno}, col {e.colno}. " f"First 500 chars of output: {cleaned_text[:500]!r}")
        return []


class ParsedTransaction(BaseModel):
    date: str
    description: str
    amount: float
    currency: str
    category_suggestion: str = DEFAULT_CATEGORY_SUGGESTION
    currency_conversion_type: str = DEFAULT_CURRENCY_CONVERSION_TYPE
    original_value: float | None = None
    original_currency: str | None = None
    fx_rate: float | None = None
    fx_rate_timestamp: str | None = None


class DuplicateWarning(BaseModel):
    is_duplicate: bool
    previously_uploaded_at: str | None = None
    previously_uploaded_filename: str | None = None


class PdfUploadResponse(BaseModel):
    upload_id: str
    parsed_transactions: list[ParsedTransaction]
    duplicate_warning: DuplicateWarning


class PdfJobStatusResponse(BaseModel):
    status: str
    result: PdfUploadResponse | None = None
    detail: str | None = None


class PdfConfirmRequest(BaseModel):
    upload_id: str
    project_id: int
    transactions: list[ParsedTransaction]


def build_parsed_transactions(cleaned_data: list[dict]) -> list[ParsedTransaction]:
    """Convert cleaned transaction data into ParsedTransaction objects with currency conversion type.

    Determines currency_conversion_type based on original_currency:
    - 'native': no currency conversion (MYR transaction or null original_currency)
    - 'converted_by_bank': bank converted to MYR (has original_currency and fx_rate)

    Args:
        cleaned_data: List of dicts from cleanup_transactions, with amount_myr, original_currency, etc.

    Returns:
        List of ParsedTransaction objects ready for PDF confirmation.
    """
    transactions = []
    for t in cleaned_data:
        amount_myr = abs(float(t.get("amount_myr", 0)))
        original_currency = t.get("original_currency")
        original_value = t.get("original_value")
        fx_rate = t.get("fx_rate")
        transaction_date = t.get("date", "")

        if original_currency and original_currency.upper() not in ("MYR", "RM"):
            currency_conversion_type = BANK_CONVERSION_TYPE
            fx_rate_timestamp = transaction_date
        else:
            currency_conversion_type = DEFAULT_CURRENCY_CONVERSION_TYPE
            fx_rate_timestamp = None

        transactions.append(
            ParsedTransaction(
                date=transaction_date,
                description=t.get("description", ""),
                amount=amount_myr,
                currency=DEFAULT_CURRENCY,
                category_suggestion=DEFAULT_CATEGORY_SUGGESTION,
                currency_conversion_type=currency_conversion_type,
                original_value=original_value,
                original_currency=original_currency,
                fx_rate=fx_rate,
                fx_rate_timestamp=fx_rate_timestamp,
            )
        )
    return transactions


pdf_uploads = {}
pdf_jobs: dict[str, dict] = {}


async def _run_pdf_pipeline(upload_id: str, file_content: bytes, filename: str) -> None:
    pdf_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file_content)
            pdf_path = tmp.name
        logger.debug(f"PDF saved to temporary file: {pdf_path}, size={len(file_content)} bytes")

        content_hash = await asyncio.get_event_loop().run_in_executor(executor, hash_pdf_content, pdf_path)
        logger.info(f"PDF content hash computed: {content_hash}")

        db = next(get_db())
        try:
            existing_hash = db.query(PdfHash).filter(PdfHash.content_hash == content_hash).first()
            duplicate_warning = DuplicateWarning(is_duplicate=False)
            if existing_hash:
                logger.warning(f"Duplicate PDF detected: hash={content_hash}, previously_uploaded_at={existing_hash.uploaded_at}")
                duplicate_warning = DuplicateWarning(
                    is_duplicate=True,
                    previously_uploaded_at=existing_hash.uploaded_at,
                    previously_uploaded_filename=existing_hash.filename,
                )

            images_b64 = await asyncio.get_event_loop().run_in_executor(executor, pdf_to_images, pdf_path)
            logger.info(f"PDF conversion stage complete: {len(images_b64)} page images")

            raw_output = await asyncio.get_event_loop().run_in_executor(executor, extract_transactions, images_b64)
            logger.info(f"Transaction extraction stage complete: {len(raw_output)} chars of raw output")

            cleaned_data = await asyncio.get_event_loop().run_in_executor(executor, cleanup_transactions, raw_output)
            logger.info(f"Transaction cleanup stage complete: {len(cleaned_data)} transactions parsed")

            if len(cleaned_data) == 0:
                logger.warning("PDF upload completed with 0 parsed transactions — user should check the PDF")

            transactions = build_parsed_transactions(cleaned_data)

            pdf_uploads[upload_id] = {
                "transactions": transactions,
                "content_hash": content_hash,
                "filename": filename,
            }
            logger.debug(f"Stored transactions in memory: upload_id={upload_id}, count={len(transactions)}, total_uploads_in_memory={len(pdf_uploads)}")

            result = PdfUploadResponse(upload_id=upload_id, parsed_transactions=transactions, duplicate_warning=duplicate_warning)
            pdf_jobs[upload_id] = {"status": "done", "result": result}
            logger.info(f"PDF upload successful: upload_id={upload_id}, transactions={len(transactions)}, duplicate={duplicate_warning.is_duplicate}")
        finally:
            db.close()

    except Exception as e:
        logger.error(f"PDF processing failed: {type(e).__name__}: {e!r}")
        pdf_jobs[upload_id] = {"status": "error", "detail": str(e)}
    finally:
        if pdf_path:
            try:
                os.unlink(pdf_path)
                logger.debug(f"Temporary PDF file deleted: {pdf_path}")
            except Exception as e:
                logger.warning(f"Failed to delete temporary PDF file: {pdf_path}, error: {e!r}")


@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI backend!"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


api_router = APIRouter(prefix=API_ROUTER_PREFIX)


@api_router.post("/pdf/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".pdf"):
        logger.warning(f"PDF upload rejected: invalid filename {file.filename}")
        raise HTTPException(status_code=400, detail="File must be a PDF")

    file_content = await file.read()
    if len(file_content) > MAX_PDF_FILE_SIZE:
        logger.warning(f"PDF upload rejected: file too large: {len(file_content)} bytes")
        raise HTTPException(status_code=413, detail=f"File size must not exceed {MAX_PDF_FILE_SIZE // (1024 * 1024)}MB")

    upload_id = str(uuid.uuid4())
    pdf_jobs[upload_id] = {"status": "processing"}
    logger.info(f"Started PDF upload job: upload_id={upload_id}, filename={file.filename}")

    asyncio.create_task(_run_pdf_pipeline(upload_id, file_content, file.filename))

    return {"upload_id": upload_id, "status": "processing"}


@api_router.get("/pdf/status/{upload_id}", response_model=PdfJobStatusResponse)
def get_pdf_status(upload_id: str):
    job = pdf_jobs.get(upload_id)
    if not job:
        raise HTTPException(status_code=404, detail="Upload ID not found")
    return job


# Confirm PDF import and create expense records from previously uploaded and parsed transactions.
# Requires upload_id from /pdf/upload and the user's project_id.
@api_router.post("/pdf/confirm", response_model=list[ExpenseResponse])
def confirm_pdf_import(request: PdfConfirmRequest, db: Session = Depends(get_db)):
    logger.info(f"PDF import confirmation requested: upload_id={request.upload_id}, project_id={request.project_id}, transaction_count={len(request.transactions)}")

    project = db.query(Project).filter(Project.id == request.project_id).first()
    if not project:
        logger.warning(f"PDF confirm: project not found: project_id={request.project_id}")
        raise HTTPException(status_code=404, detail="Project not found")

    if request.upload_id not in pdf_uploads:
        logger.warning(f"PDF confirm: upload_id not found: upload_id={request.upload_id}")
        raise HTTPException(status_code=404, detail="Upload ID not found")

    upload_data = pdf_uploads[request.upload_id]
    content_hash = upload_data.get("content_hash")
    filename = upload_data.get("filename")

    created_expenses = []
    total_amount = 0.0
    for transaction in request.transactions:
        expense = Expense(
            project_id=request.project_id,
            date=transaction.date,
            vendor=transaction.description[:PDF_VENDOR_TRUNCATION_LENGTH],
            description=transaction.description,
            amount=abs(transaction.amount),
            currency=transaction.currency,
            category=transaction.category_suggestion,
            is_claimed=False,
            source="pdf",
            currency_conversion_type=transaction.currency_conversion_type,
            original_value=transaction.original_value,
            original_currency=transaction.original_currency,
            fx_rate=transaction.fx_rate,
            fx_rate_timestamp=transaction.fx_rate_timestamp,
        )
        db.add(expense)
        db.flush()
        created_expenses.append(expense)
        total_amount += abs(transaction.amount)

    if content_hash:
        existing_hash = db.query(PdfHash).filter(PdfHash.content_hash == content_hash).first()
        if not existing_hash:
            pdf_hash_record = PdfHash(
                content_hash=content_hash,
                uploaded_at=datetime.now().isoformat(),
                filename=filename,
            )
            db.add(pdf_hash_record)
            logger.info(f"Stored PDF hash for duplicate detection: hash={content_hash}, filename={filename}")
        else:
            logger.debug(f"Hash already exists in database, skipping duplicate entry: hash={content_hash}")

    db.commit()

    for expense in created_expenses:
        db.refresh(expense)

    del pdf_uploads[request.upload_id]
    logger.debug(f"Removed upload from memory: upload_id={request.upload_id}")

    logger.info(f"PDF import confirmed: {len(created_expenses)} expenses created for project_id={request.project_id}, total_amount={total_amount:.2f}")
    return created_expenses


app.include_router(projects_router)
app.include_router(income_expenses_router)
app.include_router(api_router)
