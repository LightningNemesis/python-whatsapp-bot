# app/__init__.py
from flask import Flask
from app.config import load_configurations, configure_logging
from .views import webhook_blueprint
from app.utils.inventory.db_manager import init_inventory_db


def create_app():
    print("Starting app creation...")  # Debug print

    app = Flask(__name__, static_folder="static", template_folder="templates")

    # Load configurations and logging settings
    load_configurations(app)
    configure_logging()

    print("About to initialize database...")  # Debug print
    # Initialize the database with default inventory
    with app.app_context():
        try:
            result = init_inventory_db()
            print(f"Database initialization result: {result}")  # Debug print
        except Exception as e:
            print(f"Error initializing database: {e}")  # Debug print

    # Import and register blueprints, if any
    app.register_blueprint(webhook_blueprint)

    return app
