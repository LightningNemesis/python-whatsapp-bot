from flask import Flask, request, jsonify
import hmac
import hashlib
import json

app = Flask(__name__)


@app.route("/calendly-webhook", methods=["POST"])
def handle_webhook():
    # Get the webhook payload
    data = request.json

    # Handle different event types
    event_type = data.get("event")
    if event_type == "invitee.created":
        # Someone scheduled a meeting
        invitee = data["payload"]
        print(invitee)
        print("\n=== New Meeting Scheduled! ===")
        print(f"Invitee: {invitee['name']} ({invitee['email']})")
        print(f"Start time: {invitee['scheduled_event']['start_time']}")
        print(f"Event Name: {invitee['scheduled_event']['name']}")
        print("============================\n")

    elif event_type == "invitee.canceled":
        # Someone canceled a meeting
        invitee = data["payload"]
        print(invitee)
        print("\n=== Meeting Canceled! ===")
        print(f"Invitee: {invitee['name']}")
        print("========================\n")

    # Always return a 200 status code to Calendly
    return jsonify({"status": "success"}), 200


if __name__ == "__main__":
    print("Starting Calendly webhook server on port 8000...")
    print("Webhook URL: https://immune-grand-bulldog.ngrok-free.app/calendly-webhook")
    app.run(port=8000)
