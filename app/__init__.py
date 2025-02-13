# app/__init__.py
from flask import Flask
from app.config import load_configurations, configure_logging
from .views import webhook_blueprint
from app.utils.inventory.db_manager import init_inventory_db
from app.utils.calendly.calendly_client import CalendlyClient
import os


# app/__init__.py
def create_app():
    print("Starting app creation...")

    app = Flask(__name__, static_folder="static", template_folder="templates")

    # Load configurations and logging settings
    load_configurations(app)
    configure_logging()

    with app.app_context():
        # Initialize inventory database
        try:
            result = init_inventory_db()
            print(f"Database initialization result: {result}")
        except Exception as e:
            app.logger.error(f"Error initializing database: {e}")

        # Initialize Calendly webhook
        try:
            calendly_token = os.getenv("CALENDLY_TOKEN")
            base_url = os.getenv("BASE_URL")

            if not calendly_token or not base_url:
                raise ValueError(
                    "CALENDLY_TOKEN and BASE_URL environment variables must be set"
                )

            calendly_client = CalendlyClient(calendly_token)
            webhook_url = f"{base_url}/calendly-webhook"

            # Check for existing webhooks first
            existing_webhooks = calendly_client.list_webhooks()
            for webhook in existing_webhooks:
                if webhook["url"] == webhook_url:
                    app.logger.info("Calendly webhook already exists")
                    break
            else:
                # Create new webhook if none exists
                calendly_client.create_webhook(
                    callback_url=webhook_url,
                    events=["invitee.created", "invitee.canceled"],
                    scope="user",
                )
                app.logger.info("Calendly webhook configured successfully")

        except ValueError as e:
            app.logger.error(f"Configuration error: {e}")
        except Exception as e:
            app.logger.error(f"Failed to configure Calendly webhook: {e}")

    app.register_blueprint(webhook_blueprint)
    return app
