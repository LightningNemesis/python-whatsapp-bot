from flask import Flask, request, jsonify
import hmac
import hashlib
import json

app = Flask(__name__)


@app.route("/calendly-webhook", methods=["POST"])
def handle_webhook():
    # Get the webhook payload
    data = request.json

    from flask import Flask, request, jsonify


from start.calendly.calendly_client import CalendlyClient
from start.calendly.openai_calendly import CalendlyAssistant
from dotenv import load_dotenv
import os

app = Flask(__name__)

# Initialize Calendly client and assistant
load_dotenv()
calendly_client = CalendlyClient(os.getenv("CALENDLY_TOKEN"))
assistant = CalendlyAssistant(calendly_client)


@app.route("/calendly-webhook", methods=["POST"])
def handle_webhook():
    # Get the webhook payload
    data = request.json

    # Process webhook with assistant
    assistant_response = assistant.handle_webhook_event(data)

    # Print details for logging
    event_type = data.get("event")
    if event_type == "invitee.created":
        invitee = data["payload"]
        print("\n=== New Meeting Scheduled! ===")
        print(f"Invitee: {invitee['name']} ({invitee['email']})")
        print(f"Start time: {invitee['scheduled_event']['start_time']}")
        print(f"Event Name: {invitee['scheduled_event']['name']}")
        print("\nAssistant's Response:")
        print(assistant_response)
        print("============================\n")

    elif event_type == "invitee.canceled":
        invitee = data["payload"]
        print("\n=== Meeting Canceled! ===")
        print(f"Invitee: {invitee['name']}")
        print("\nAssistant's Response:")
        print(assistant_response)
        print("========================\n")

    # Always return a 200 status code to Calendly
    return jsonify({"status": "success"}), 200


if __name__ == "__main__":
    print("Starting Calendly webhook server on port 8000...")
    print("Webhook URL: https://immune-grand-bulldog.ngrok-free.app/calendly-webhook")
    app.run(port=8000)
