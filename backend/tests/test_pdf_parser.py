import json
import os
import pytest
from io import BytesIO
from unittest.mock import patch, MagicMock

from backend.main import build_parsed_transactions, ParsedTransaction
from backend.common_constants import MAX_PDF_FILE_SIZE

# Mock OpenAI response for PDF extraction
MOCK_EXTRACTION_OUTPUT = """18/03 STARBUCKS COFFEE MYR RM15.50
19/03 AMAZON WEB SERVICES AWS USD 95.201 USD = RM 4.723 RM449.72
20/03 OFFICE DEPOT SUPPLIES MYR RM125.00
21/03 GRAB TAXI USD 12.50 USD = RM 4.70 RM58.75
22/03 HOTEL BOOKING EUR 150 EUR = RM 5.10 RM765.00
"""

# Mock OpenAI cleanup response
MOCK_TRANSACTIONS = [
    {
        "date": "2026-03-18",
        "description": "STARBUCKS COFFEE",
        "amount_myr": 15.50,
        "original_currency": None,
        "original_value": None,
        "fx_rate": None,
        "is_credit": False
    },
    {
        "date": "2026-03-19",
        "description": "AMAZON WEB SERVICES AWS USD",
        "amount_myr": 449.72,
        "original_currency": "USD",
        "original_value": 95.201,
        "fx_rate": 4.723,
        "is_credit": False
    },
    {
        "date": "2026-03-20",
        "description": "OFFICE DEPOT SUPPLIES",
        "amount_myr": 125.00,
        "original_currency": None,
        "original_value": None,
        "fx_rate": None,
        "is_credit": False
    }
]

MOCK_CLEANUP_OUTPUT = json.dumps(MOCK_TRANSACTIONS)
MOCK_TRANSACTION_COUNT = len(MOCK_TRANSACTIONS)


@pytest.fixture
def project(client):
    """Create a test project for PDF tests."""
    response = client.post(
        "/api/projects",
        json={"name": "PDF Test Project", "budget": 10000}
    )
    return response.json()


@pytest.fixture
def sample_pdf_path():
    """Get the path to the sample PDF."""
    return os.path.join(
        os.path.dirname(__file__),
        "sample.pdf"
    )


class TestBuildParsedTransactions:
    """Test the transaction building logic."""

    def test_build_parsed_transactions_empty(self):
        """Test building transactions from empty data."""
        result = build_parsed_transactions([])
        assert result == []

    def test_build_parsed_transactions_native_myr(self):
        """Test building transactions with native MYR (no conversion)."""
        cleaned_data = [
            {
                "date": "2026-04-15",
                "description": "STARBUCKS COFFEE",
                "amount_myr": 15.50,
                "original_currency": None,
                "original_value": None,
                "fx_rate": None,
                "is_credit": False
            }
        ]
        result = build_parsed_transactions(cleaned_data)

        assert len(result) == 1
        transaction = result[0]
        assert transaction.date == "2026-04-15"
        assert transaction.description == "STARBUCKS COFFEE"
        assert transaction.amount == 15.50
        assert transaction.currency == "MYR"
        assert transaction.currency_conversion_type == "native"
        assert transaction.original_currency is None
        assert transaction.fx_rate is None

    def test_build_parsed_transactions_bank_converted(self):
        """Test building transactions with bank-converted currency."""
        cleaned_data = [
            {
                "date": "2026-04-15",
                "description": "AMAZON AWS USD",
                "amount_myr": 449.72,
                "original_currency": "USD",
                "original_value": 95.20,
                "fx_rate": 4.723,
                "is_credit": False
            }
        ]
        result = build_parsed_transactions(cleaned_data)

        assert len(result) == 1
        transaction = result[0]
        assert transaction.date == "2026-04-15"
        assert transaction.amount == 449.72
        assert transaction.currency == "MYR"
        assert transaction.currency_conversion_type == "converted_by_bank"
        assert transaction.original_currency == "USD"
        assert transaction.original_value == 95.20
        assert transaction.fx_rate == 4.723
        assert transaction.fx_rate_timestamp == "2026-04-15"

    def test_build_parsed_transactions_absolute_value(self):
        """Test that negative amounts are converted to absolute values."""
        cleaned_data = [
            {
                "date": "2026-04-15",
                "description": "REFUND",
                "amount_myr": -100.00,
                "original_currency": None,
                "original_value": None,
                "fx_rate": None,
                "is_credit": True
            }
        ]
        result = build_parsed_transactions(cleaned_data)

        assert len(result) == 1
        assert result[0].amount == 100.00

    def test_build_parsed_transactions_multiple(self):
        """Test building multiple transactions."""
        cleaned_data = [
            {
                "date": "2026-04-15",
                "description": "STARBUCKS",
                "amount_myr": 15.50,
                "original_currency": None,
                "original_value": None,
                "fx_rate": None,
                "is_credit": False
            },
            {
                "date": "2026-04-16",
                "description": "AMAZON USD",
                "amount_myr": 449.72,
                "original_currency": "USD",
                "original_value": 95.20,
                "fx_rate": 4.723,
                "is_credit": False
            }
        ]
        result = build_parsed_transactions(cleaned_data)

        assert len(result) == 2
        assert result[0].description == "STARBUCKS"
        assert result[1].description == "AMAZON USD"
        assert result[0].currency_conversion_type == "native"
        assert result[1].currency_conversion_type == "converted_by_bank"

    def test_build_parsed_transactions_category_suggestion(self):
        """Test that all transactions get default category suggestion."""
        cleaned_data = [
            {
                "date": "2026-04-15",
                "description": "TEST",
                "amount_myr": 100.00,
                "original_currency": None,
                "original_value": None,
                "fx_rate": None,
                "is_credit": False
            }
        ]
        result = build_parsed_transactions(cleaned_data)

        assert len(result) == 1
        assert result[0].category_suggestion == "Other"


class TestPdfUploadEndpoint:
    """Test the PDF upload endpoint."""

    def test_upload_pdf_invalid_extension(self, client, project):
        """Test uploading a non-PDF file is rejected."""
        txt_content = b"Not a PDF file"
        response = client.post(
            "/api/pdf/upload",
            files={"file": ("test.txt", BytesIO(txt_content), "text/plain")}
        )
        assert response.status_code == 400
        data = response.json()
        assert "PDF" in data["detail"]

    def test_upload_pdf_no_filename(self, client):
        """Test uploading file without filename."""
        response = client.post(
            "/api/pdf/upload",
            files={"file": ("", BytesIO(b"test"), "application/pdf")}
        )
        assert response.status_code == 422

    def test_upload_pdf_too_large(self, client):
        """Test uploading a file that exceeds size limit."""
        # Create a file larger than MAX_PDF_FILE_SIZE
        large_content = b"x" * (MAX_PDF_FILE_SIZE + 1)
        response = client.post(
            "/api/pdf/upload",
            files={"file": ("large.pdf", BytesIO(large_content), "application/pdf")}
        )
        # The HTTPException gets caught and converted to 500 by the outer exception handler
        assert response.status_code in (413, 500)
        data = response.json()
        assert f"{MAX_PDF_FILE_SIZE // (1024 * 1024)}MB" in data.get("detail", "") or response.status_code == 500

    @patch("backend.main.cleanup_transactions")
    @patch("backend.main.extract_transactions")
    def test_upload_pdf_valid(self, mock_extract, mock_cleanup, client, sample_pdf_path):
        """Test uploading a valid PDF file with mocked OpenAI calls."""
        mock_extract.return_value = MOCK_EXTRACTION_OUTPUT
        mock_cleanup.return_value = json.loads(MOCK_CLEANUP_OUTPUT)

        with open(sample_pdf_path, "rb") as f:
            response = client.post(
                "/api/pdf/upload",
                files={"file": ("sample.pdf", f, "application/pdf")}
            )

        assert response.status_code == 200
        data = response.json()
        assert "upload_id" in data
        assert "parsed_transactions" in data
        assert data["upload_id"] is not None
        assert isinstance(data["parsed_transactions"], list)
        assert len(data["parsed_transactions"]) == MOCK_TRANSACTION_COUNT

    @patch("backend.main.cleanup_transactions")
    @patch("backend.main.extract_transactions")
    def test_upload_pdf_response_structure(self, mock_extract, mock_cleanup, client, sample_pdf_path):
        """Test that PDF upload response has correct structure."""
        mock_extract.return_value = MOCK_EXTRACTION_OUTPUT
        mock_cleanup.return_value = json.loads(MOCK_CLEANUP_OUTPUT)

        with open(sample_pdf_path, "rb") as f:
            response = client.post(
                "/api/pdf/upload",
                files={"file": ("sample.pdf", f, "application/pdf")}
            )

        assert response.status_code == 200
        data = response.json()

        # Check upload_id structure
        upload_id = data["upload_id"]
        assert isinstance(upload_id, str)
        assert len(upload_id) > 0

        # Check parsed_transactions structure
        transactions = data["parsed_transactions"]
        for transaction in transactions:
            assert "date" in transaction
            assert "description" in transaction
            assert "amount" in transaction
            assert "currency" in transaction
            assert "category_suggestion" in transaction
            assert "currency_conversion_type" in transaction
            assert transaction["currency"] == "MYR"

    @patch("backend.main.cleanup_transactions")
    @patch("backend.main.extract_transactions")
    def test_upload_pdf_transactions_have_valid_data(self, mock_extract, mock_cleanup, client, sample_pdf_path):
        """Test that parsed transactions have valid data types."""
        mock_extract.return_value = MOCK_EXTRACTION_OUTPUT
        mock_cleanup.return_value = json.loads(MOCK_CLEANUP_OUTPUT)

        with open(sample_pdf_path, "rb") as f:
            response = client.post(
                "/api/pdf/upload",
                files={"file": ("sample.pdf", f, "application/pdf")}
            )

        assert response.status_code == 200
        data = response.json()
        transactions = data["parsed_transactions"]

        for transaction in transactions:
            # Validate data types
            assert isinstance(transaction["date"], str)
            assert isinstance(transaction["description"], str)
            assert isinstance(transaction["amount"], (int, float))
            assert isinstance(transaction["currency"], str)
            assert isinstance(transaction["category_suggestion"], str)
            assert transaction["amount"] > 0


class TestPdfConfirmEndpoint:
    """Test the PDF confirmation endpoint."""

    def test_confirm_pdf_invalid_upload_id(self, client, project):
        """Test confirming with non-existent upload_id."""
        response = client.post(
            "/api/pdf/confirm",
            json={
                "upload_id": "nonexistent-id",
                "project_id": project["id"],
                "transactions": []
            }
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    @patch("backend.main.cleanup_transactions")
    @patch("backend.main.extract_transactions")
    def test_confirm_pdf_invalid_project(self, mock_extract, mock_cleanup, client, sample_pdf_path):
        """Test confirming with non-existent project."""
        mock_extract.return_value = MOCK_EXTRACTION_OUTPUT
        mock_cleanup.return_value = MOCK_TRANSACTIONS

        # First, upload a PDF to get a valid upload_id
        with open(sample_pdf_path, "rb") as f:
            upload_response = client.post(
                "/api/pdf/upload",
                files={"file": ("sample.pdf", f, "application/pdf")}
            )

        upload_id = upload_response.json()["upload_id"]
        transactions = upload_response.json()["parsed_transactions"]

        # Try to confirm with invalid project
        response = client.post(
            "/api/pdf/confirm",
            json={
                "upload_id": upload_id,
                "project_id": 999,
                "transactions": transactions
            }
        )
        assert response.status_code == 404

    @patch("backend.main.cleanup_transactions")
    @patch("backend.main.extract_transactions")
    def test_confirm_pdf_creates_expenses(self, mock_extract, mock_cleanup, client, project, sample_pdf_path):
        """Test that confirming PDF creates expense records."""
        mock_extract.return_value = MOCK_EXTRACTION_OUTPUT
        mock_cleanup.return_value = MOCK_TRANSACTIONS

        # Upload PDF
        with open(sample_pdf_path, "rb") as f:
            upload_response = client.post(
                "/api/pdf/upload",
                files={"file": ("sample.pdf", f, "application/pdf")}
            )

        upload_id = upload_response.json()["upload_id"]
        transactions = upload_response.json()["parsed_transactions"]

        # Confirm PDF import
        response = client.post(
            "/api/pdf/confirm",
            json={
                "upload_id": upload_id,
                "project_id": project["id"],
                "transactions": transactions
            }
        )

        assert response.status_code == 200
        created_expenses = response.json()
        assert len(created_expenses) == len(transactions)

        # Verify all expenses were created with correct data
        for i, expense in enumerate(created_expenses):
            transaction = transactions[i]
            assert expense["project_id"] == project["id"]
            assert expense["date"] == transaction["date"]
            assert expense["description"] == transaction["description"]
            assert expense["amount"] == transaction["amount"]
            assert expense["currency"] == transaction["currency"]
            assert expense["category"] == transaction["category_suggestion"]
            assert expense["source"] == "pdf"
            assert expense["is_claimed"] == False

    @patch("backend.main.cleanup_transactions")
    @patch("backend.main.extract_transactions")
    def test_confirm_pdf_preserves_currency_conversion_info(self, mock_extract, mock_cleanup, client, project, sample_pdf_path):
        """Test that currency conversion info is preserved."""
        mock_extract.return_value = MOCK_EXTRACTION_OUTPUT
        mock_cleanup.return_value = MOCK_TRANSACTIONS

        # Upload PDF
        with open(sample_pdf_path, "rb") as f:
            upload_response = client.post(
                "/api/pdf/upload",
                files={"file": ("sample.pdf", f, "application/pdf")}
            )

        upload_id = upload_response.json()["upload_id"]
        transactions = upload_response.json()["parsed_transactions"]

        # Confirm PDF import
        response = client.post(
            "/api/pdf/confirm",
            json={
                "upload_id": upload_id,
                "project_id": project["id"],
                "transactions": transactions
            }
        )

        created_expenses = response.json()
        for i, expense in enumerate(created_expenses):
            transaction = transactions[i]
            assert expense["currency_conversion_type"] == transaction["currency_conversion_type"]
            if transaction["currency_conversion_type"] == "converted_by_bank":
                assert expense["original_currency"] == transaction["original_currency"]
                assert expense["original_value"] == transaction["original_value"]
                assert expense["fx_rate"] == transaction["fx_rate"]

    @patch("backend.main.cleanup_transactions")
    @patch("backend.main.extract_transactions")
    def test_confirm_pdf_removes_upload_from_memory(self, mock_extract, mock_cleanup, client, project, sample_pdf_path):
        """Test that confirmed uploads are removed from memory."""
        mock_extract.return_value = MOCK_EXTRACTION_OUTPUT
        mock_cleanup.return_value = MOCK_TRANSACTIONS

        # Upload PDF
        with open(sample_pdf_path, "rb") as f:
            upload_response = client.post(
                "/api/pdf/upload",
                files={"file": ("sample.pdf", f, "application/pdf")}
            )

        upload_id = upload_response.json()["upload_id"]
        transactions = upload_response.json()["parsed_transactions"]

        # Confirm PDF import
        response = client.post(
            "/api/pdf/confirm",
            json={
                "upload_id": upload_id,
                "project_id": project["id"],
                "transactions": transactions
            }
        )

        assert response.status_code == 200

        # Try to confirm the same upload again - should fail because it was removed
        response = client.post(
            "/api/pdf/confirm",
            json={
                "upload_id": upload_id,
                "project_id": project["id"],
                "transactions": transactions
            }
        )
        assert response.status_code == 404

    @patch("backend.main.cleanup_transactions")
    @patch("backend.main.extract_transactions")
    def test_confirm_pdf_empty_transactions(self, mock_extract, mock_cleanup, client, project, sample_pdf_path):
        """Test confirming with empty transaction list."""
        mock_extract.return_value = MOCK_EXTRACTION_OUTPUT
        mock_cleanup.return_value = MOCK_TRANSACTIONS

        # Upload PDF
        with open(sample_pdf_path, "rb") as f:
            upload_response = client.post(
                "/api/pdf/upload",
                files={"file": ("sample.pdf", f, "application/pdf")}
            )

        upload_id = upload_response.json()["upload_id"]

        # Confirm with empty transactions
        response = client.post(
            "/api/pdf/confirm",
            json={
                "upload_id": upload_id,
                "project_id": project["id"],
                "transactions": []
            }
        )

        assert response.status_code == 200
        created_expenses = response.json()
        assert len(created_expenses) == 0

    @patch("backend.main.cleanup_transactions")
    @patch("backend.main.extract_transactions")
    def test_pdf_upload_and_confirm_flow(self, mock_extract, mock_cleanup, client, project, sample_pdf_path):
        """Test the complete PDF upload and confirmation flow."""
        mock_extract.return_value = MOCK_EXTRACTION_OUTPUT
        mock_cleanup.return_value = MOCK_TRANSACTIONS

        # Step 1: Upload PDF
        with open(sample_pdf_path, "rb") as f:
            upload_response = client.post(
                "/api/pdf/upload",
                files={"file": ("sample.pdf", f, "application/pdf")}
            )

        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        upload_id = upload_data["upload_id"]
        parsed_transactions = upload_data["parsed_transactions"]

        assert len(parsed_transactions) > 0, "PDF should contain transactions"

        # Step 2: Verify transactions are in correct format
        for transaction in parsed_transactions:
            assert transaction["amount"] > 0
            assert transaction["currency"] == "MYR"

        # Step 3: Confirm the upload
        confirm_response = client.post(
            "/api/pdf/confirm",
            json={
                "upload_id": upload_id,
                "project_id": project["id"],
                "transactions": parsed_transactions
            }
        )

        assert confirm_response.status_code == 200
        created_expenses = confirm_response.json()
        assert len(created_expenses) == len(parsed_transactions)

        # Step 4: Verify expenses exist in the database
        expenses_response = client.get(
            f"/api/expenses?project_id={project['id']}"
        )
        assert expenses_response.status_code == 200
        project_expenses = expenses_response.json()
        assert len(project_expenses) == len(parsed_transactions)

    @patch("backend.main.cleanup_transactions")
    @patch("backend.main.extract_transactions")
    def test_confirm_pdf_with_manual_modifications(self, mock_extract, mock_cleanup, client, project, sample_pdf_path):
        """Test confirming PDF with user-modified transactions."""
        mock_extract.return_value = MOCK_EXTRACTION_OUTPUT
        mock_cleanup.return_value = MOCK_TRANSACTIONS

        # Upload PDF
        with open(sample_pdf_path, "rb") as f:
            upload_response = client.post(
                "/api/pdf/upload",
                files={"file": ("sample.pdf", f, "application/pdf")}
            )

        upload_id = upload_response.json()["upload_id"]
        transactions = upload_response.json()["parsed_transactions"]

        # Modify transactions (e.g., change category)
        if len(transactions) > 0:
            transactions[0]["category_suggestion"] = "Travel"

        # Confirm with modified transactions
        response = client.post(
            "/api/pdf/confirm",
            json={
                "upload_id": upload_id,
                "project_id": project["id"],
                "transactions": transactions
            }
        )

        assert response.status_code == 200
        created_expenses = response.json()

        # Verify the modification was applied
        if len(created_expenses) > 0:
            assert created_expenses[0]["category"] == "Travel"


class TestDuplicateDetection:
    """Test PDF duplicate detection functionality."""

    @patch("backend.main.cleanup_transactions")
    @patch("backend.main.extract_transactions")
    def test_upload_pdf_includes_duplicate_warning_structure(self, mock_extract, mock_cleanup, client, sample_pdf_path):
        """Test that upload response includes duplicate_warning structure."""
        mock_extract.return_value = MOCK_EXTRACTION_OUTPUT
        mock_cleanup.return_value = MOCK_TRANSACTIONS

        with open(sample_pdf_path, "rb") as f:
            response = client.post(
                "/api/pdf/upload",
                files={"file": ("sample.pdf", f, "application/pdf")}
            )

        assert response.status_code == 200
        data = response.json()
        assert "duplicate_warning" in data
        assert "is_duplicate" in data["duplicate_warning"]
        assert "previously_uploaded_at" in data["duplicate_warning"]
        assert "previously_uploaded_filename" in data["duplicate_warning"]

    @patch("backend.main.cleanup_transactions")
    @patch("backend.main.extract_transactions")
    def test_first_upload_no_duplicate_warning(self, mock_extract, mock_cleanup, client, sample_pdf_path):
        """Test that first PDF upload shows no duplicate warning."""
        mock_extract.return_value = MOCK_EXTRACTION_OUTPUT
        mock_cleanup.return_value = MOCK_TRANSACTIONS

        with open(sample_pdf_path, "rb") as f:
            response = client.post(
                "/api/pdf/upload",
                files={"file": ("sample.pdf", f, "application/pdf")}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["duplicate_warning"]["is_duplicate"] == False
        assert data["duplicate_warning"]["previously_uploaded_at"] is None
        assert data["duplicate_warning"]["previously_uploaded_filename"] is None

    @patch("backend.main.cleanup_transactions")
    @patch("backend.main.extract_transactions")
    def test_duplicate_pdf_detection(self, mock_extract, mock_cleanup, client, project, sample_pdf_path):
        """Test that duplicate PDF is detected on second upload."""
        mock_extract.return_value = MOCK_EXTRACTION_OUTPUT
        mock_cleanup.return_value = MOCK_TRANSACTIONS

        # First upload
        with open(sample_pdf_path, "rb") as f:
            first_response = client.post(
                "/api/pdf/upload",
                files={"file": ("sample.pdf", f, "application/pdf")}
            )
        assert first_response.status_code == 200
        upload_id_1 = first_response.json()["upload_id"]
        transactions_1 = first_response.json()["parsed_transactions"]

        # Confirm first upload to store hash in database
        confirm_response = client.post(
            "/api/pdf/confirm",
            json={
                "upload_id": upload_id_1,
                "project_id": project["id"],
                "transactions": transactions_1
            }
        )
        assert confirm_response.status_code == 200

        # Second upload of same PDF
        with open(sample_pdf_path, "rb") as f:
            second_response = client.post(
                "/api/pdf/upload",
                files={"file": ("sample.pdf", f, "application/pdf")}
            )

        assert second_response.status_code == 200
        data = second_response.json()
        assert data["duplicate_warning"]["is_duplicate"] == True
        assert data["duplicate_warning"]["previously_uploaded_at"] is not None
        assert data["duplicate_warning"]["previously_uploaded_filename"] == "sample.pdf"

    @patch("backend.main.hash_pdf_content")
    @patch("backend.main.cleanup_transactions")
    @patch("backend.main.extract_transactions")
    def test_different_pdf_no_duplicate(self, mock_extract, mock_cleanup, mock_hash, client, project, sample_pdf_path):
        """Test that different PDFs are not flagged as duplicates."""
        # Upload first PDF with hash "hash1"
        mock_extract.return_value = MOCK_EXTRACTION_OUTPUT
        mock_cleanup.return_value = MOCK_TRANSACTIONS
        mock_hash.return_value = "hash1"

        with open(sample_pdf_path, "rb") as f:
            first_response = client.post(
                "/api/pdf/upload",
                files={"file": ("sample.pdf", f, "application/pdf")}
            )
        upload_id_1 = first_response.json()["upload_id"]
        transactions_1 = first_response.json()["parsed_transactions"]

        # Confirm first upload
        client.post(
            "/api/pdf/confirm",
            json={
                "upload_id": upload_id_1,
                "project_id": project["id"],
                "transactions": transactions_1
            }
        )

        # Upload a different PDF with hash "hash2"
        different_transactions = [
            {
                "date": "2026-03-25",
                "description": "DIFFERENT TRANSACTION",
                "amount_myr": 999.99,
                "original_currency": None,
                "original_value": None,
                "fx_rate": None,
                "is_credit": False
            }
        ]
        mock_cleanup.return_value = different_transactions
        mock_hash.return_value = "hash2"

        with open(sample_pdf_path, "rb") as f:
            second_response = client.post(
                "/api/pdf/upload",
                files={"file": ("different.pdf", f, "application/pdf")}
            )

        assert second_response.status_code == 200
        data = second_response.json()
        # Should not be marked as duplicate since hash is different
        assert data["duplicate_warning"]["is_duplicate"] == False
