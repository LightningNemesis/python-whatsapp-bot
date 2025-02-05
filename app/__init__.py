from flask import Flask
from app.config import load_configurations, configure_logging
from .views import webhook_blueprint
from .web3_views import web3_blueprint


def create_app():
    app = Flask(
        __name__, static_folder="static", template_folder="templates"  # Add this
    )  # And this

    # Load configurations and logging settings
    load_configurations(app)
    configure_logging()

    # Import and register blueprints, if any
    app.register_blueprint(webhook_blueprint)
    app.register_blueprint(web3_blueprint)

    return app
