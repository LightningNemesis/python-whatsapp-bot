# app/__init__.py
from flask import Flask
from app.config import load_configurations, configure_logging
from .views import webhook_blueprint
from app.utils.inventory.db_manager import init_inventory_db
from app.utils.calendly.calendly_client import CalendlyClient
import os
import json
from app.utils.calendly.booking_mapper import BookingMapper


def create_app():
    print("Starting app creation...")

    app = Flask(__name__, static_folder="static", template_folder="templates")

    # Load configurations and logging settings
    load_configurations(app)
    configure_logging()

    # Initialize booking mapper
    db_path = os.path.join(app.root_path, "data", "bookings.db")
    app.config["booking_mapper"] = BookingMapper(db_path)

    with app.app_context():
        # Initialize inventory database
        try:
            result = init_inventory_db()
            print(f"Database initialization result: {result}")
        except Exception as e:
            app.logger.error(f"Error initializing database: {e}")

        # Initialize Calendly webhook
        try:
            print("\n=== Starting Calendly Webhook Configuration ===")

            calendly_token = os.getenv("CALENDLY_TOKEN")
            base_url = os.getenv("BASE_URL")

            print(f"Base URL: {base_url}")
            print(f"Calendly Token exists: {bool(calendly_token)}")

            if not calendly_token or not base_url:
                raise ValueError(
                    "CALENDLY_TOKEN and BASE_URL environment variables must be set"
                )

            calendly_client = CalendlyClient(calendly_token)
            webhook_url = f"{base_url}/calendly-webhook"
            print(f"Webhook URL to configure: {webhook_url}")

            # Check for existing webhooks first
            print("\nFetching existing webhooks...")
            existing_webhooks = calendly_client.list_webhooks()
            print(
                f"Existing webhooks response: {json.dumps(existing_webhooks, indent=2)}"
            )

            webhook_found = False
            active_webhook_exists = False
            for webhook in existing_webhooks:
                print(f"\nAnalyzing webhook: {json.dumps(webhook, indent=2)}")
                if (
                    webhook.get("callback_url") == webhook_url
                ):  # Changed from url to callback_url
                    webhook_found = True
                    if webhook.get("state") == "active":
                        active_webhook_exists = True
                        print("Found matching active webhook!")
                        break
                    print("Found matching webhook but it's not active")

            if active_webhook_exists:
                print("\nActive webhook already exists, skipping creation")
                app.logger.info("Calendly webhook already exists and is active")
            elif webhook_found:
                print(
                    "\nInactive webhook exists, you may need to reactivate it in Calendly dashboard"
                )
                app.logger.info("Calendly webhook exists but is inactive")
            else:
                print("\nNo matching webhook found, creating new one...")
                # Create new webhook if none exists
                webhook_response = calendly_client.create_webhook(
                    callback_url=webhook_url,
                    events=["invitee.created", "invitee.canceled"],
                    scope="user",
                )
                print(
                    f"Webhook creation response: {json.dumps(webhook_response, indent=2)}"
                )
                app.logger.info("Calendly webhook configured successfully")

        except ValueError as e:
            print(f"\nConfiguration error: {e}")
            app.logger.error(f"Configuration error: {e}")
        except Exception as e:
            print(f"\nFailed to configure Calendly webhook: {e}")
            print(f"Error type: {type(e)}")
            if hasattr(e, "__dict__"):
                print(f"Error attributes: {e.__dict__}")
            app.logger.error(f"Failed to configure Calendly webhook: {e}")
        finally:
            print("\n=== Calendly Webhook Configuration Complete ===")

    app.register_blueprint(webhook_blueprint)
    return app
