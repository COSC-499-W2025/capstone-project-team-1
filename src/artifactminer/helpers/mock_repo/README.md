# Mock API Project

A simple FastAPI application for demonstration purposes.

## Structure

- `main.py` - FastAPI application with REST endpoints
- `models.py` - Pydantic data models (User, Item)
- `database.py` - Mock database utilities
- `utils/helpers.py` - Helper functions for common operations

## Running

```bash
uvicorn main:app --reload
```

## Endpoints

- `GET /` - Welcome message
- `GET /users/{id}` - Get user by ID
- `POST /items/` - Create new item
- `GET /health` - Health check
