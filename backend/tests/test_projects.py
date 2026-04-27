import pytest


def test_create_project(client):
    """Test creating a new project."""
    response = client.post(
        "/api/projects",
        json={
            "name": "Website Redesign",
            "description": "Redesign company website",
            "budget": 5000.0,
            "status": "active"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Website Redesign"
    assert data["budget"] == 5000.0
    assert data["status"] == "active"
    assert data["id"] is not None


def test_create_project_empty_name(client):
    """Test creating a project with empty name fails."""
    response = client.post(
        "/api/projects",
        json={
            "name": "   ",
            "description": "Test",
            "budget": 1000.0
        }
    )
    assert response.status_code == 422


def test_create_project_invalid_status(client):
    """Test creating a project with invalid status fails."""
    response = client.post(
        "/api/projects",
        json={
            "name": "Test Project",
            "status": "invalid_status"
        }
    )
    assert response.status_code == 422


def test_list_projects(client):
    """Test listing all projects."""
    # Create two projects
    client.post("/api/projects", json={"name": "Project 1", "budget": 1000})
    client.post("/api/projects", json={"name": "Project 2", "budget": 2000})

    response = client.get("/api/projects")
    assert response.status_code == 200
    projects = response.json()
    assert len(projects) == 2
    assert projects[0]["name"] == "Project 1"
    assert projects[1]["name"] == "Project 2"


def test_list_projects_empty(client):
    """Test listing projects when none exist."""
    response = client.get("/api/projects")
    assert response.status_code == 200
    projects = response.json()
    assert len(projects) == 0


def test_update_project(client):
    """Test updating an existing project."""
    # Create a project
    create_response = client.post(
        "/api/projects",
        json={"name": "Original Name", "budget": 1000}
    )
    project_id = create_response.json()["id"]

    # Update it
    response = client.put(
        f"/api/projects/{project_id}",
        json={
            "name": "Updated Name",
            "budget": 2000.0,
            "status": "on_hold"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["budget"] == 2000.0
    assert data["status"] == "on_hold"


def test_update_nonexistent_project(client):
    """Test updating a project that doesn't exist."""
    response = client.put(
        "/api/projects/999",
        json={"name": "Test", "budget": 1000}
    )
    assert response.status_code == 404


def test_delete_project(client):
    """Test deleting a project."""
    # Create a project
    create_response = client.post(
        "/api/projects",
        json={"name": "To Delete", "budget": 1000}
    )
    project_id = create_response.json()["id"]

    # Delete it
    response = client.delete(f"/api/projects/{project_id}")
    assert response.status_code == 200

    # Verify it's gone
    list_response = client.get("/api/projects")
    projects = list_response.json()
    assert len(projects) == 0


def test_delete_nonexistent_project(client):
    """Test deleting a project that doesn't exist."""
    response = client.delete("/api/projects/999")
    assert response.status_code == 404
