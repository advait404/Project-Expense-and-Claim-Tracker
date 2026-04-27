import pytest


@pytest.fixture
def project(client):
    """Create a test project for dashboard tests."""
    response = client.post(
        "/api/projects",
        json={"name": "Dashboard Test Project", "budget": 10000}
    )
    return response.json()


def test_project_summary_empty(client):
    """Test getting summary for empty projects."""
    response = client.get("/api/projects/summary")
    assert response.status_code == 200
    summaries = response.json()
    assert len(summaries) == 0


def test_project_summary_single_project(client, project):
    """Test getting summary for a single project."""
    # Add income
    client.post(
        "/api/income",
        json={
            "project_id": project["id"],
            "date": "2026-04-15",
            "source": "Client Payment",
            "amount": 5000.0,
            "currency": "MYR"
        }
    )

    # Add expenses
    client.post(
        "/api/expenses",
        json={
            "project_id": project["id"],
            "date": "2026-04-16",
            "vendor": "Vendor 1",
            "amount": 1000.0,
            "currency": "MYR",
            "category": "Office"
        }
    )
    client.post(
        "/api/expenses",
        json={
            "project_id": project["id"],
            "date": "2026-04-17",
            "vendor": "Vendor 2",
            "amount": 500.0,
            "currency": "MYR",
            "category": "Travel",
            "is_claimed": True
        }
    )

    response = client.get("/api/projects/summary")
    assert response.status_code == 200
    summaries = response.json()
    assert len(summaries) == 1

    summary = summaries[0]
    assert summary["project_id"] == project["id"]
    assert summary["project_name"] == "Dashboard Test Project"
    assert summary["total_income"] == 5000.0
    assert summary["total_expenses"] == 1500.0
    assert summary["net_position"] == 3500.0
    assert summary["total_claimed"] == 500.0
    assert summary["total_unclaimed"] == 1000.0


def test_project_summary_multiple_projects(client):
    """Test getting summary for multiple projects."""
    # Create two projects
    project1 = client.post(
        "/api/projects",
        json={"name": "Project 1", "budget": 5000}
    ).json()

    project2 = client.post(
        "/api/projects",
        json={"name": "Project 2", "budget": 10000}
    ).json()

    # Add data to project 1
    client.post(
        "/api/income",
        json={
            "project_id": project1["id"],
            "date": "2026-04-15",
            "source": "Payment",
            "amount": 3000.0,
            "currency": "MYR"
        }
    )
    client.post(
        "/api/expenses",
        json={
            "project_id": project1["id"],
            "date": "2026-04-16",
            "vendor": "Vendor",
            "amount": 500.0,
            "currency": "MYR",
            "category": "Office"
        }
    )

    # Add data to project 2
    client.post(
        "/api/income",
        json={
            "project_id": project2["id"],
            "date": "2026-04-15",
            "source": "Payment",
            "amount": 8000.0,
            "currency": "MYR"
        }
    )
    client.post(
        "/api/expenses",
        json={
            "project_id": project2["id"],
            "date": "2026-04-16",
            "vendor": "Vendor",
            "amount": 2000.0,
            "currency": "MYR",
            "category": "Travel"
        }
    )

    response = client.get("/api/projects/summary")
    assert response.status_code == 200
    summaries = response.json()
    assert len(summaries) == 2

    # Find summaries by project ID
    summary1 = next(s for s in summaries if s["project_id"] == project1["id"])
    summary2 = next(s for s in summaries if s["project_id"] == project2["id"])

    assert summary1["total_income"] == 3000.0
    assert summary1["total_expenses"] == 500.0
    assert summary1["net_position"] == 2500.0

    assert summary2["total_income"] == 8000.0
    assert summary2["total_expenses"] == 2000.0
    assert summary2["net_position"] == 6000.0


def test_project_summary_with_claimed_expenses(client, project):
    """Test summary correctly separates claimed and unclaimed expenses."""
    # Add expenses with different claim statuses
    client.post(
        "/api/expenses",
        json={
            "project_id": project["id"],
            "date": "2026-04-15",
            "vendor": "Claimed Vendor",
            "amount": 300.0,
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
            "date": "2026-04-15",
            "vendor": "Unclaimed Vendor",
            "amount": 700.0,
            "currency": "MYR",
            "category": "Travel",
            "is_claimed": False
        }
    )

    response = client.get("/api/projects/summary")
    assert response.status_code == 200
    summary = response.json()[0]

    assert summary["total_expenses"] == 1000.0
    assert summary["total_claimed"] == 300.0
    assert summary["total_unclaimed"] == 700.0
