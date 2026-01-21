"""Main FastAPI application."""
from fastapi import FastAPI, HTTPException
from models import User, Item
from database import get_db_connection

app = FastAPI(title="Mock API", version="1.0.0")


@app.get("/")
async def root():
    return {"message": "Welcome to the Mock API"}


@app.get("/users/{user_id}")
async def get_user(user_id: int):
    db = get_db_connection()
    user = db.get("users", {}).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.post("/items/")
async def create_item(item: Item):
    return {"item": item, "status": "created"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
