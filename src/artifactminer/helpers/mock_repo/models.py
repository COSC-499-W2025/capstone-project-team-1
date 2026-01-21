"""Pydantic models for the API."""
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class User(BaseModel):
    id: int
    username: str
    email: EmailStr
    created_at: datetime = datetime.now()
    is_active: bool = True


class Item(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    price: float
    owner_id: int


class ItemResponse(BaseModel):
    item: Item
    status: str
