# db_viewer.py
from tinydb import TinyDB
from rich.console import Console
from rich.table import Table
from rich.json import JSON
import json
from pathlib import Path


class DBViewer:
    def __init__(self, db_path: str = "inventory.db"):
        self.db = TinyDB(db_path)
        self.console = Console()

    def view_as_table(self):
        """Display database contents as a formatted table"""
        table = Table(title="Inventory Database")

        # Get all items
        items = self.db.table("inventory").all()
        if not items:
            self.console.print("[yellow]No items in database[/yellow]")
            return

        # Dynamic columns based on first item
        columns = list(items[0].keys())
        for column in columns:
            table.add_column(column, style="cyan")

        # Add rows
        for item in items:
            table.add_row(*[str(item[col]) for col in columns])

        self.console.print(table)

    def view_as_json(self):
        """Display database contents as formatted JSON"""
        items = self.db.table("inventory").all()
        formatted_json = json.dumps({"inventory": items}, indent=2)
        self.console.print(JSON(formatted_json))

    def get_db_info(self):
        """Display database metadata"""
        db_path = Path("inventory.db")
        table = Table(title="Database Information")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Database File", str(db_path.absolute()))
        table.add_row("File Size", f"{db_path.stat().st_size / 1024:.2f} KB")
        table.add_row("Total Tables", str(len(self.db.tables())))
        table.add_row("Total Items", str(len(self.db.table("inventory"))))

        self.console.print(table)


def main():
    # First install rich:
    # pip install rich

    viewer = DBViewer()

    print("\n=== Database Information ===")
    viewer.get_db_info()

    print("\n=== Table View ===")
    viewer.view_as_table()

    print("\n=== JSON View ===")
    viewer.view_as_json()


if __name__ == "__main__":
    main()
