# inventory_db.py
from tinydb import TinyDB, Query
from datetime import datetime
from typing import Dict, Optional, List
from app.utils.inventory.schemas import InventoryItem


class InventoryDB:
    def __init__(self, db_path: str = "inventory.db"):
        self.db = TinyDB(db_path)
        self.inventory = self.db.table("inventory")
        self.Item = Query()

    def add_item(self, item_data: Dict) -> int:
        """Add a new item to inventory with schema validation."""
        # Add current timestamp
        item_data["last_updated"] = datetime.now().isoformat()

        # Validate data against schema
        item = InventoryItem(**item_data)

        # Convert to dict and insert
        # Using dict() instead of model_dump() to get a basic dict with datetime as string
        return self.inventory.insert(dict(item))

    def get_item(self, item_id: int) -> Optional[InventoryItem]:
        """Retrieve an item from inventory by ID."""
        item_data = self.inventory.get(self.Item.item_id == item_id)
        return InventoryItem(**item_data) if item_data else None

    def update_item(self, item_id: int, updates: Dict) -> bool:
        """Update an existing item in inventory."""
        # Get current item
        current_item = self.get_item(item_id)
        if not current_item:
            return False

        # Add current timestamp
        updates["last_updated"] = datetime.now().isoformat()

        # Merge updates with current data
        updated_data = dict(current_item)
        updated_data.update(updates)

        # Validate merged data
        validated_item = InventoryItem(**updated_data)

        # Update in database
        return bool(
            self.inventory.update(dict(validated_item), self.Item.item_id == item_id)
        )

    def delete_item(self, item_id: int) -> bool:
        """Delete an item from inventory."""
        return bool(self.inventory.remove(self.Item.item_id == item_id))

    def list_items(self) -> List[InventoryItem]:
        """Return all items in inventory."""
        return [InventoryItem(**item) for item in self.inventory.all()]

    def update_quantity(self, item_id: int, quantity: float) -> bool:
        """Update the quantity of an item."""
        return self.update_item(item_id, {"quantity": quantity})
