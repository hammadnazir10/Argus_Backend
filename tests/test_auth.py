import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    """Test user registration."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "testpassword123",
            "full_name": "Test User",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """Test registration with duplicate email."""
    user_data = {
        "email": "duplicate@example.com",
        "password": "testpassword123",
    }
    await client.post("/api/v1/auth/register", json=user_data)
    
    response = await client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_login(client: AsyncClient):
    """Test user login."""
    # Register user first
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "login@example.com",
            "password": "testpassword123",
        },
    )
    
    # Login
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "email": "login@example.com",
            "password": "testpassword123",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    """Test login with invalid credentials."""
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "email": "nonexistent@example.com",
            "password": "wrongpassword",
        },
    )
    assert response.status_code == 401
