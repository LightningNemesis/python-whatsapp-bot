# main.py
from inventory_db import InventoryDB
from schemas import InventoryItem
from datetime import datetime


def main():
    # Initialize database
    db = InventoryDB()

    # Clear existing data
    db.inventory.truncate()

    # Initial inventory data
    inventory_items = [
        {
            "item_id": 1,
            "item_name": "Crude Oil",
            "quantity": 5000.0,
            "symbol": "CO",
            "unit": "barrels",
            "location": "Storage Tank A",
            "supplier": "OilCo",
        },
        {
            "item_id": 2,
            "item_name": "Natural Gas",
            "quantity": 10000.0,
            "symbol": "NG",
            "unit": "MCF",
            "location": "Pipeline B",
            "supplier": "GasCorp",
        },
        {
            "item_id": 3,
            "item_name": "Diesel Fuel",
            "quantity": 2000.0,
            "symbol": "DF",
            "unit": "gallons",
            "location": "Storage Tank C",
            "supplier": "FuelMaster",
        },
    ]

    # Add all items
    for item in inventory_items:
        try:
            db.add_item(item)
            print(f"Added item: {item['item_name']}")
        except Exception as e:
            print(f"Error adding {item['item_name']}: {str(e)}")

    print("\nAll items added successfully!")


if __name__ == "__main__":
    main()
