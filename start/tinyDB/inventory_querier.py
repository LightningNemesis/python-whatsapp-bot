# inventory_querier.py
from inventory_db import InventoryDB
from typing import Dict, List, Optional


class InventoryQuerier:
    def __init__(self):
        self.db = InventoryDB()

    def get_all_items(self) -> List[Dict]:
        """Get all inventory items"""
        items = self.db.list_items()
        # Convert items to dictionary representation
        return [dict(item) for item in items]

    def get_item_by_id(self, item_id: int) -> Optional[Dict]:
        """Get item by ID"""
        item = self.db.get_item(item_id)
        return dict(item) if item else None

    # inventory_querier.py
    def get_items_by_location(self, location: str) -> List[Dict]:
        """Get items by location"""
        all_items = self.db.list_items()

        # Normalize the search term and make matching more flexible
        search_term = location.lower().replace("tank", "").strip()

        # More flexible matching
        matching_items = [
            item
            for item in all_items
            if search_term in item.location.lower()
            or search_term in item.location.lower().replace("storage tank", "").strip()
            or search_term in item.location.lower().replace("pipeline", "").strip()
        ]

        return [dict(item) for item in matching_items]

    def get_total_quantity_by_unit(self, unit: str) -> float:
        """Get total quantity for a specific unit"""
        all_items = self.db.list_items()
        return sum(
            item.quantity for item in all_items if item.unit.lower() == unit.lower()
        )

    def get_items_by_supplier(self, supplier: str) -> List[Dict]:
        """Get items from a specific supplier"""
        all_items = self.db.list_items()
        matching_items = [
            item for item in all_items if supplier.lower() in item.supplier.lower()
        ]
        return [dict(item) for item in matching_items]
