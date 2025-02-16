import logging
import json
from datetime import datetime

from flask import Blueprint, request, jsonify, current_app

from .decorators.security import signature_required
from .utils.whatsapp_utils import (
    process_whatsapp_message,
    is_valid_whatsapp_message,
)

from app.services.calendly_service import CalendlyAssistantService
from app.utils.message_utils import send_message, get_text_message_input

webhook_blueprint = Blueprint("webhook", __name__)
calendly_assistant = CalendlyAssistantService()


def handle_message():
    """
    Handle incoming webhook events from the WhatsApp API.

    This function processes incoming WhatsApp messages and other events,
    such as delivery statuses. If the event is a valid message, it gets
    processed. If the incoming payload is not a recognized WhatsApp event,
    an error is returned.

    Every message send will trigger 4 HTTP requests to your webhook: message, sent, delivered, read.

    Returns:
        response: A tuple containing a JSON response and an HTTP status code.
    """
    body = request.get_json()
    # logging.info(f"request body: {body}")

    # Check if it's a WhatsApp status update
    if (
        body.get("entry", [{}])[0]
        .get("changes", [{}])[0]
        .get("value", {})
        .get("statuses")
    ):
        logging.info("Received a WhatsApp status update.")
        return jsonify({"status": "ok"}), 200

    try:
        if is_valid_whatsapp_message(body):
            process_whatsapp_message(body)
            return jsonify({"status": "ok"}), 200
        else:
            # if the request is not a WhatsApp API event, return an error
            return (
                jsonify({"status": "error", "message": "Not a WhatsApp API event"}),
                404,
            )
    except json.JSONDecodeError:
        logging.error("Failed to decode JSON")
        return jsonify({"status": "error", "message": "Invalid JSON provided"}), 400


# Required webhook verifictaion for WhatsApp
def verify():
    # Parse params from the webhook verification request
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    # Check if a token and mode were sent
    if mode and token:
        # Check the mode and token sent are correct
        if mode == "subscribe" and token == current_app.config["VERIFY_TOKEN"]:
            # Respond with 200 OK and challenge token from the request
            logging.info("WEBHOOK_VERIFIED")
            return challenge, 200
        else:
            # Responds with '403 Forbidden' if verify tokens do not match
            logging.info("VERIFICATION_FAILED")
            return jsonify({"status": "error", "message": "Verification failed"}), 403
    else:
        # Responds with '400 Bad Request' if verify tokens do not match
        logging.info("MISSING_PARAMETER")
        return jsonify({"status": "error", "message": "Missing parameters"}), 400


@webhook_blueprint.route("/webhook", methods=["GET"])
def webhook_get():
    return verify()


@webhook_blueprint.route("/webhook", methods=["POST"])
@signature_required
def webhook_post():
    return handle_message()


@webhook_blueprint.route("/calendly-webhook", methods=["POST"])
def calendly_webhook():
    """Handle Calendly webhook events"""
    print("\n=== Received Calendly Webhook ===")
    data = request.json
    print(f"Event Type: {data.get('event')}")
    print("Full webhook payload:")
    print(json.dumps(data, indent=2))

    try:
        # Extract the payload
        payload = data.get("payload", {})
        scheduled_event = payload.get("scheduled_event", {})

        # Get essential data
        event_uri = payload.get("event")
        event_type_uri = scheduled_event.get("event_type")
        event_status = scheduled_event.get("status")

        if not event_uri:
            print("No event URI in payload")
            return (
                jsonify({"status": "error", "message": "No event URI in payload"}),
                400,
            )

        # Get the mapper instance from app config
        booking_mapper = current_app.config.get("booking_mapper")
        if not booking_mapper:
            print("No booking mapper found in app config")
            return (
                jsonify(
                    {"status": "error", "message": "Booking mapper not configured"}
                ),
                500,
            )

        # Process the event based on type
        event_type = data.get("event")

        if event_type == "invitee.created":
            # Extract event type ID from URI
            event_type_id = event_type_uri.split("/")[-1]

            print(f"\nNew booking created:")
            print(f"Event URI: {event_uri}")
            print(f"Event Type: {event_type_uri}")
            print(f"Event Type ID: {event_type_id}")
            print(f"Status: {event_status}")

            # Get WhatsApp ID from mapping
            whatsapp_id = booking_mapper.get_whatsapp_id_for_event_type(event_type_id)

            if whatsapp_id:
                print(f"Found WhatsApp ID: {whatsapp_id}")

                # Get meeting details
                start_time = scheduled_event.get("start_time")
                end_time = scheduled_event.get("end_time")
                meeting_name = scheduled_event.get("name")
                location = scheduled_event.get("location", {})
                join_url = location.get("join_url")

                # Format times
                start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))

                # Create WhatsApp message
                message = (
                    f"🎉 *Meeting Confirmed!*\n\n"
                    f"📅 Meeting: {meeting_name}\n"
                    f"📆 Date: {start.strftime('%B %d, %Y')}\n"
                    f"⏰ Time: {start.strftime('%I:%M %p')} - {end.strftime('%I:%M %p')} UTC\n"
                )

                if join_url:
                    message += f"\n🔗 Join here: {join_url}\n"

                message += "\nSee you there! 👋"

                # Send WhatsApp confirmation
                data = get_text_message_input(whatsapp_id, message)
                send_message(data)

            # Add to mapper anyway for tracking
            booking_mapper.add_scheduled_event(
                event_uri=event_uri,
                whatsapp_id=whatsapp_id,
                event_type_id=event_type_id,
                status="scheduled",
            )

        elif event_type == "invitee.canceled":
            whatsapp_id = booking_mapper.get_whatsapp_id_for_event(event_uri)
            if whatsapp_id:
                print(f"\nBooking canceled for WhatsApp ID: {whatsapp_id}")
                booking_mapper.update_event_status(event_uri, "canceled")

                # Send cancellation notification
                message = (
                    "❌ *Meeting Canceled*\n\n"
                    f"The meeting scheduled for {scheduled_event.get('start_time')} has been canceled.\n\n"
                    "Need to reschedule? Just let me know!"
                )

                data = get_text_message_input(whatsapp_id, message)
                send_message(data)

        return jsonify({"status": "success"}), 200

    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        print(f"Error type: {type(e)}")
        current_app.logger.error(f"Error processing Calendly webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
