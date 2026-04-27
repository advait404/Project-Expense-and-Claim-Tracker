import pytest


@pytest.fixture
def project(client):
    """Create a test project for income tests."""
    response = client.post(
        "/api/projects",
        json={"name": "Test Project", "budget": 10000}
    )
    return response.json()


def test_create_income(client, project):
    """Test creating an income entry."""
    response = client.post(
        "/api/income",
        json={
            "project_id": project["id"],
            "date": "2026-04-15",
            "source": "Client Payment",
            "amount": 1500.0,
            "currency": "MYR"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "Client Payment"
    assert data["amount"] == 1500.0
    assert data["currency"] == "MYR"
    assert data["project_id"] == project["id"]


def test_create_income_nonexistent_project(client):
    """Test creating income for a project that doesn't exist."""
    response = client.post(
        "/api/income",
        json={
            "project_id": 999,
            "date": "2026-04-15",
            "source": "Client Payment",
            "amount": 1500.0,
            "currency": "MYR"
        }
    )
    assert response.status_code == 404


def test_create_income_invalid_amount(client, project):
    """Test creating income with invalid amount."""
    response = client.post(
        "/api/income",
        json={
            "project_id": project["id"],
            "date": "2026-04-15",
            "source": "Client Payment",
            "amount": -500.0,
            "currency": "MYR"
        }
    )
    assert response.status_code == 422


def test_create_income_empty_source(client, project):
    """Test creating income with empty source."""
    response = client.post(
        "/api/income",
        json={
            "project_id": project["id"],
            "date": "2026-04-15",
            "source": "   ",
            "amount": 1500.0,
            "currency": "MYR"
        }
    )
    assert response.status_code == 422


def test_list_income_all(client, project):
    """Test listing all income entries."""
    # Create two income entries
    client.post(
        "/api/income",
        json={
            "project_id": project["id"],
            "date": "2026-04-15",
            "source": "Payment 1",
            "amount": 1000.0,
            "currency": "MYR"
        }
    )
    client.post(
        "/api/income",
        json={
            "project_id": project["id"],
            "date": "2026-04-16",
            "source": "Payment 2",
            "amount": 2000.0,
            "currency": "MYR"
        }
    )

    response = client.get("/api/income")
    assert response.status_code == 200
    income_list = response.json()
    assert len(income_list) == 2


def test_list_income_by_project(client, project):
    """Test listing income filtered by project."""
    # Create another project
    other_project = client.post(
        "/api/projects",
        json={"name": "Other Project", "budget": 5000}
    ).json()

    # Add income to both projects
    client.post(
        "/api/income",
        json={
            "project_id": project["id"],
            "date": "2026-04-15",
            "source": "Payment 1",
            "amount": 1000.0,
            "currency": "MYR"
        }
    )
    client.post(
        "/api/income",
        json={
            "project_id": other_project["id"],
            "date": "2026-04-16",
            "source": "Payment 2",
            "amount": 2000.0,
            "currency": "MYR"
        }
    )

    # Filter by first project
    response = client.get(f"/api/income?project_id={project['id']}")
    assert response.status_code == 200
    income_list = response.json()
    assert len(income_list) == 1
    assert income_list[0]["amount"] == 1000.0


def test_update_income(client, project):
    """Test updating an income entry."""
    # Create income
    create_response = client.post(
        "/api/income",
        json={
            "project_id": project["id"],
            "date": "2026-04-15",
            "source": "Original Source",
            "amount": 1000.0,
            "currency": "MYR"
        }
    )
    income_id = create_response.json()["id"]

    # Update it
    response = client.put(
        f"/api/income/{income_id}",
        json={
            "project_id": project["id"],
            "date": "2026-04-16",
            "source": "Updated Source",
            "amount": 2000.0,
            "currency": "MYR"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "Updated Source"
    assert data["amount"] == 2000.0


def test_delete_income(client, project):
    """Test deleting an income entry."""
    # Create income
    create_response = client.post(
        "/api/income",
        json={
            "project_id": project["id"],
            "date": "2026-04-15",
            "source": "To Delete",
            "amount": 1000.0,
            "currency": "MYR"
        }
    )
    income_id = create_response.json()["id"]

    # Delete it
    response = client.delete(f"/api/income/{income_id}")
    assert response.status_code == 200

    # Verify it's gone
    list_response = client.get("/api/income")
    income_list = list_response.json()
    assert len(income_list) == 0
