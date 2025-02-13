# app/utils/inventory/db_manager.py
import os
from typing import List, Dict
from app.utils.inventory.inventory_db import InventoryDB
import logging

logger = logging.getLogger(__name__)


def init_inventory_db():
    """Initialize the inventory database with default values"""
    print("Starting database initialization...")  # Debug print

    try:
        # Get the directory of the current file and set DB path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(current_dir, "inventory.db")
        print(f"Database path: {db_path}")

        db = InventoryDB(db_path)

        # Clear existing data
        db.inventory.truncate()
        print("Cleared existing inventory data")

        # Initial inventory data
        inventory_items = [
            {
                "item_id": 1,
                "item_name": "Crude Oil",
                "quantity": 5000.0,
                "symbol": "CO",
                "unit": "barrels",  # Must match UnitType enum
                "location": "Storage Tank A",
                "supplier": "OilCo",
            },
            {
                "item_id": 2,
                "item_name": "Natural Gas",
                "quantity": 10000.0,
                "symbol": "NG",
                "unit": "MCF",  # Must match UnitType enum
                "location": "Pipeline B",
                "supplier": "GasCorp",
            },
            {
                "item_id": 3,
                "item_name": "Diesel Fuel",
                "quantity": 2000.0,
                "symbol": "DF",
                "unit": "gallons",  # Must match UnitType enum
                "location": "Storage Tank C",
                "supplier": "FuelMaster",
            },
        ]

        # Add all items
        for item in inventory_items:
            try:
                db.add_item(item)
                print(f"Added inventory item: {item['item_name']}")
            except Exception as e:
                print(f"Error adding {item['item_name']}: {str(e)}")
                raise

        # Verify items were added
        all_items = db.list_items()
        print(f"Total items in database: {len(all_items)}")

        return True

    except Exception as e:
        print(f"Failed to initialize inventory database: {str(e)}")
