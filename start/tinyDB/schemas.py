# schemas.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum


class UnitType(str, Enum):
    BARRELS = "barrels"
    MCF = "MCF"
    GALLONS = "gallons"


class InventoryItem(BaseModel):
    item_id: int = Field(gt=0)
    item_name: str = Field(min_length=1, max_length=100)
    quantity: float = Field(ge=0)
    symbol: str = Field(min_length=1, max_length=10)
    unit: UnitType
    location: str = Field(min_length=1, max_length=100)
    supplier: str = Field(min_length=1, max_length=100)
    last_updated: Optional[str] = None  # Store as ISO format string
