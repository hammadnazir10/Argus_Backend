import pytest
from httpx import AsyncClient


async def get_auth_token(client: AsyncClient, email: str, password: str) -> str:
    """Helper function to get auth token."""
    response = await client.post(
        "/api/v1/auth/login",
        data={"email": email, "password": password},
    )
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient):
    """Test getting current user info."""
    # Register user
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "me@example.com",
            "password": "testpassword123",
            "full_name": "Me User",
        },
    )
    
    # Get token
    token = await get_auth_token(client, "me@example.com", "testpassword123")
    
    # Get current user
    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"


@pytest.mark.asyncio
async def test_update_current_user(client: AsyncClient):
    """Test updating current user."""
    # Register user
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "update@example.com",
            "password": "testpassword123",
        },
    )
    
    # Get token
    token = await get_auth_token(client, "update@example.com", "testpassword123")
    
    # Update user
    response = await client.put(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"full_name": "Updated Name"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Updated Name"


@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient):
    """Test unauthorized access to protected endpoint."""
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401
