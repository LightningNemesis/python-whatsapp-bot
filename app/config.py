import sys
import os
from dotenv import load_dotenv
import logging


def load_configurations(app):
    # os.environ.clear()
    load_dotenv(override=True)

    # Log before loading config
    logging.info("Loading configurations...")
    logging.info(f"ACCESS_TOKEN from env: {os.getenv('ACCESS_TOKEN')}")

    app.config["ACCESS_TOKEN"] = os.getenv("ACCESS_TOKEN")

    # Log after loading config
    logging.info(f"ACCESS_TOKEN in app config: {app.config.get('ACCESS_TOKEN')}")

    config_vars = {
        "ACCESS_TOKEN": os.getenv("ACCESS_TOKEN"),
        # "YOUR_PHONE_NUMBER": os.getenv("YOUR_PHONE_NUMBER"),
        "APP_ID": os.getenv("APP_ID"),
        "APP_SECRET": os.getenv("APP_SECRET"),
        "RECIPIENT_WAID": os.getenv("RECIPIENT_WAID"),
        "VERSION": os.getenv("VERSION"),
        "PHONE_NUMBER_ID": os.getenv("PHONE_NUMBER_ID"),
        "VERIFY_TOKEN": os.getenv("VERIFY_TOKEN"),
        "PRIVATE_KEY": os.getenv("PRIVATE_KEY"),
        "UPLOAD_FOLDER": os.getenv("UPLOAD_FOLDER", "/tmp/whatsapp_uploads"),
    }

    # app.config["YOUR_PHONE_NUMBER"] = os.getenv("YOUR_PHONE_NUMBER")
    # app.config["APP_ID"] = os.getenv("APP_ID")
    # app.config["APP_SECRET"] = os.getenv("APP_SECRET")
    # app.config["RECIPIENT_WAID"] = os.getenv("RECIPIENT_WAID")
    # app.config["VERSION"] = os.getenv("VERSION")
    # app.config["PHONE_NUMBER_ID"] = os.getenv("PHONE_NUMBER_ID")
    # app.config["VERIFY_TOKEN"] = os.getenv("VERIFY_TOKEN")
    # app.config["PRIVATE_KEY"] = os.getenv("PRIVATE_KEY")
    # app.config["UPLOAD_FOLDER"] = "/tmp/whatsapp_uploads"

    # Check for missing required configurations
    missing_vars = [key for key, value in config_vars.items() if value is None]
    if missing_vars:
        logging.error(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )

    # Update app config
    app.config.update(config_vars)

    # Create upload directory if it doesn't exist
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    logging.info("Configuration loaded successfully")


def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )
