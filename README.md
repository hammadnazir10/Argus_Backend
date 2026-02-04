# Argus Backend

A modern FastAPI backend application with best practices and clean architecture.

## Project Structure

```
Argus_Backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Application entry point
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py             # Dependency injection
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py       # API router
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           ├── auth.py     # Authentication endpoints
│   │           └── users.py    # User endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           # Application settings
│   │   └── security.py         # Security utilities (JWT, hashing)
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py             # Base model class
│   │   └── session.py          # Database session
│   ├── exceptions/
│   │   ├── __init__.py
│   │   └── handlers.py         # Custom exceptions
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py             # User database model
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── common.py           # Common response schemas
│   │   ├── token.py            # Token schemas
│   │   └── user.py             # User schemas
│   ├── services/
│   │   ├── __init__.py
│   │   └── user_service.py     # User business logic
│   └── utils/
│       ├── __init__.py
│       └── helpers.py          # Utility functions
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Test configuration
│   ├── test_auth.py            # Auth tests
│   └── test_users.py           # User tests
├── .env.example                # Environment variables example
├── .gitignore
├── README.md
└── requirements.txt
```

## Features

- **FastAPI** - Modern, fast web framework
- **Async SQLAlchemy** - Async database operations
- **JWT Authentication** - Secure token-based auth
- **Pydantic v2** - Data validation
- **Clean Architecture** - Separation of concerns
- **API Versioning** - Support for multiple API versions
- **Comprehensive Testing** - Pytest with async support

## Getting Started

### Prerequisites

- Python 3.10+
- pip

### Installation

1. Clone the repository:
```bash
cd Argus_Backend
```

2. Create a virtual environment:
```bash
python -m venv venv
```

3. Activate the virtual environment:
```bash
# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

5. Create `.env` file:
```bash
cp .env.example .env
```

6. Run the application:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/api/v1/openapi.json

## API Endpoints

### Health
- `GET /` - Root health check
- `GET /health` - Health check

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login and get tokens
- `POST /api/v1/auth/refresh` - Refresh access token

### Users
- `GET /api/v1/users/me` - Get current user
- `PUT /api/v1/users/me` - Update current user
- `GET /api/v1/users/` - Get all users (superuser only)
- `GET /api/v1/users/{user_id}` - Get user by ID (superuser only)
- `DELETE /api/v1/users/{user_id}` - Delete user (superuser only)

## Running Tests

```bash
pytest
```

With coverage:
```bash
pytest --cov=app tests/
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PROJECT_NAME` | Project name | Argus Backend |
| `VERSION` | API version | 1.0.0 |
| `ENVIRONMENT` | Environment (development/production) | development |
| `DEBUG` | Debug mode | True |
| `SECRET_KEY` | JWT secret key | auto-generated |
| `DATABASE_URL` | Database connection URL | sqlite+aiosqlite:///./argus.db |
| `BACKEND_CORS_ORIGINS` | Allowed CORS origins | [] |

## License

MIT License
