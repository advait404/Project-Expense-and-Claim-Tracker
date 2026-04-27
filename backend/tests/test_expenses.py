import pytest


@pytest.fixture
def project(client):
    """Create a test project for expense tests."""
    response = client.post(
        "/api/projects",
        json={"name": "Test Project", "budget": 10000}
    )
    return response.json()


def test_create_expense(client, project):
    """Test creating an expense entry."""
    response = client.post(
        "/api/expenses",
        json={
            "project_id": project["id"],
            "date": "2026-04-15",
            "vendor": "Amazon",
            "description": "Office supplies",
            "amount": 250.50,
            "currency": "MYR",
            "category": "Office"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["vendor"] == "Amazon"
    assert data["amount"] == 250.50
    assert data["category"] == "Office"
    assert data["is_claimed"] == False
    assert data["source"] == "manual"


def test_create_expense_nonexistent_project(client):
    """Test creating expense for a project that doesn't exist."""
    response = client.post(
        "/api/expenses",
        json={
            "project_id": 999,
            "date": "2026-04-15",
            "vendor": "Amazon",
            "amount": 100.0,
            "currency": "MYR",
            "category": "Office"
        }
    )
    assert response.status_code == 404


def test_create_expense_invalid_amount(client, project):
    """Test creating expense with invalid amount."""
    response = client.post(
        "/api/expenses",
        json={
            "project_id": project["id"],
            "date": "2026-04-15",
            "vendor": "Amazon",
            "amount": -50.0,
            "currency": "MYR",
            "category": "Office"
        }
    )
    assert response.status_code == 422


def test_create_expense_empty_vendor(client, project):
    """Test creating expense with empty vendor."""
    response = client.post(
        "/api/expenses",
        json={
            "project_id": project["id"],
            "date": "2026-04-15",
            "vendor": "   ",
            "amount": 100.0,
            "currency": "MYR",
            "category": "Office"
        }
    )
    assert response.status_code == 422


def test_list_expenses_all(client, project):
    """Test listing all expenses."""
    # Create two expenses
    client.post(
        "/api/expenses",
        json={
            "project_id": project["id"],
            "date": "2026-04-15",
            "vendor": "Vendor 1",
            "amount": 100.0,
            "currency": "MYR",
            "category": "Office"
        }
    )
    client.post(
        "/api/expenses",
        json={
            "project_id": project["id"],
            "date": "2026-04-16",
            "vendor": "Vendor 2",
            "amount": 200.0,
            "currency": "MYR",
            "category": "Travel"
        }
    )

    response = client.get("/api/expenses")
    assert response.status_code == 200
    expenses = response.json()
    assert len(expenses) == 2


def test_list_expenses_by_project(client, project):
    """Test listing expenses filtered by project."""
    # Create another project
    other_project = client.post(
        "/api/projects",
        json={"name": "Other Project", "budget": 5000}
    ).json()

    # Add expenses to both projects
    client.post(
        "/api/expenses",
        json={
            "project_id": project["id"],
            "date": "2026-04-15",
            "vendor": "Vendor 1",
            "amount": 100.0,
            "currency": "MYR",
            "category": "Office"
        }
    )
    client.post(
        "/api/expenses",
        json={
            "project_id": other_project["id"],
            "date": "2026-04-16",
            "vendor": "Vendor 2",
            "amount": 200.0,
            "currency": "MYR",
            "category": "Travel"
        }
    )

    # Filter by first project
    response = client.get(f"/api/expenses?project_id={project['id']}")
    assert response.status_code == 200
    expenses = response.json()
    assert len(expenses) == 1
    assert expenses[0]["vendor"] == "Vendor 1"


def test_list_expenses_by_category(client, project):
    """Test listing expenses filtered by category."""
    # Create expenses in different categories
    client.post(
        "/api/expenses",
        json={
            "project_id": project["id"],
            "date": "2026-04-15",
            "vendor": "Vendor 1",
            "amount": 100.0,
            "currency": "MYR",
            "category": "Office"
        }
    )
    client.post(
        "/api/expenses",
        json={
            "project_id": project["id"],
            "date": "2026-04-16",
            "vendor": "Vendor 2",
            "amount": 200.0,
            "currency": "MYR",
            "category": "Travel"
        }
    )

    # Filter by category
    response = client.get(f"/api/expenses?category=Travel")
    assert response.status_code == 200
    expenses = response.json()
    assert len(expenses) == 1
    assert expenses[0]["category"] == "Travel"


def test_list_expenses_by_claim_status(client, project):
    """Test listing expenses filtered by claim status."""
    # Create one claimed and one unclaimed expense
    response1 = client.post(
        "/api/expenses",
        json={
            "project_id": project["id"],
            "date": "2026-04-15",
            "vendor": "Vendor 1",
            "amount": 100.0,
            "currency": "MYR",
            "category": "Office",
            "is_claimed": True,
            "claimed_date": "2026-04-16"
        }
    )
    client.post(
        "/api/expenses",
        json={
            "project_id": project["id"],
            "date": "2026-04-17",
            "vendor": "Vendor 2",
            "amount": 200.0,
            "currency": "MYR",
            "category": "Travel",
            "is_claimed": False
        }
    )

    # Filter by unclaimed
    response = client.get(f"/api/expenses?is_claimed=false")
    assert response.status_code == 200
    expenses = response.json()
    assert len(expenses) == 1
    assert expenses[0]["is_claimed"] == False


def test_update_expense(client, project):
    """Test updating an expense entry."""
    # Create expense
    create_response = client.post(
        "/api/expenses",
        json={
            "project_id": project["id"],
            "date": "2026-04-15",
            "vendor": "Original Vendor",
            "amount": 100.0,
            "currency": "MYR",
            "category": "Office"
        }
    )
    expense_id = create_response.json()["id"]

    # Update it
    response = client.put(
        f"/api/expenses/{expense_id}",
        json={
            "project_id": project["id"],
            "date": "2026-04-16",
            "vendor": "Updated Vendor",
            "amount": 250.0,
            "currency": "MYR",
            "category": "Travel"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["vendor"] == "Updated Vendor"
    assert data["amount"] == 250.0
    assert data["category"] == "Travel"


def test_delete_expense(client, project):
    """Test deleting an expense entry."""
    # Create expense
    create_response = client.post(
        "/api/expenses",
        json={
            "project_id": project["id"],
            "date": "2026-04-15",
            "vendor": "To Delete",
            "amount": 100.0,
            "currency": "MYR",
            "category": "Office"
        }
    )
    expense_id = create_response.json()["id"]

    # Delete it
    response = client.delete(f"/api/expenses/{expense_id}")
    assert response.status_code == 200

    # Verify it's gone
    list_response = client.get("/api/expenses")
    expenses = list_response.json()
    assert len(expenses) == 0


def test_bulk_claim_toggle(client, project):
    """Test bulk toggling claim status."""
    # Create three expenses
    response1 = client.post(
        "/api/expenses",
        json={
            "project_id": project["id"],
            "date": "2026-04-15",
            "vendor": "Vendor 1",
            "amount": 100.0,
            "currency": "MYR",
            "category": "Office"
        }
    )
    response2 = client.post(
        "/api/expenses",
        json={
            "project_id": project["id"],
            "date": "2026-04-16",
            "vendor": "Vendor 2",
            "amount": 200.0,
            "currency": "MYR",
            "category": "Travel"
        }
    )

    expense_id_1 = response1.json()["id"]
    expense_id_2 = response2.json()["id"]

    # Toggle both to claimed
    response = client.patch(
        "/api/expenses/bulk-claim-toggle",
        json={
            "ids": [expense_id_1, expense_id_2],
            "is_claimed": True
        }
    )
    assert response.status_code == 200
    expenses = response.json()
    assert len(expenses) == 2
    for exp in expenses:
        assert exp["is_claimed"] == True
        assert exp["claimed_date"] is not None
