import logging
import json

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
    """Handle incoming Calendly webhook events"""
    data = request.json
    logging.info(f"Received Calendly webhook with data: {json.dumps(data, indent=2)}")

    try:
        event_type = data.get("event")
        payload = data.get("payload", {})

        # Handle new meeting scheduled
        if event_type == "invitee.created":
            # Extract event details (corrected path)
            scheduled_event = payload.get("scheduled_event", {})
            event_name = payload.get("event_name", "Not provided")
            event_start_time = scheduled_event.get("start_time", "Not provided")

            # Extract tracking data
            tracking = payload.get("tracking", {})
            custom_tracking = tracking.get("custom", {})

            # Try multiple ways to get WhatsApp ID
            wa_id = (
                tracking.get("whatsapp_id")
                or custom_tracking.get("whatsapp_id")
                or tracking.get("utm_source")
                or (
                    custom_tracking.get("source") == "whatsapp"
                    and tracking.get("utm_source")
                )
            )

            logging.info(f"Extracted tracking data: {json.dumps(tracking, indent=2)}")
            logging.info(f"Found WhatsApp ID: {wa_id}")

            # Create meeting confirmation message
            message = (
                "🗓️ New Meeting Scheduled!\n\n"
                f"👤 Name: {payload.get('name', 'Not provided')}\n"
                f"📧 Email: {payload.get('email', 'Not provided')}\n"
                f"📅 Event: {event_name}\n"
                f"⏰ Start: {event_start_time}\n"
                f"⌛ Duration: {scheduled_event.get('duration')} minutes\n"
                f"📝 Status: Confirmed"
            )

            if scheduled_event.get("location"):
                location_info = scheduled_event.get("location", {})
                if isinstance(location_info, dict) and location_info.get("join_url"):
                    message += f"\n📍 Location: {location_info.get('join_url')}"

            # Send WhatsApp notification if ID is available
            if wa_id:
                logging.info(f"Sending meeting confirmation to WhatsApp ID: {wa_id}")
                try:
                    response = send_message(get_text_message_input(wa_id, message))
                    logging.info(f"WhatsApp API response: {response}")
                except Exception as e:
                    logging.error(f"Failed to send WhatsApp message: {e}")
            else:
                logging.warning("No WhatsApp ID found in tracking data")

        # Handle meeting cancellation
        elif event_type == "invitee.canceled":
            # Extract cancellation details
            scheduled_event = payload.get("scheduled_event", {})
            event_name = payload.get("event_name", "Not provided")
            event_start_time = scheduled_event.get("start_time", "Not provided")
            cancellation = payload.get("cancellation", {})

            # Extract tracking data
            tracking = payload.get("tracking", {})
            custom_tracking = tracking.get("custom", {})

            wa_id = (
                tracking.get("whatsapp_id")
                or custom_tracking.get("whatsapp_id")
                or tracking.get("utm_source")
                or (
                    custom_tracking.get("source") == "whatsapp"
                    and tracking.get("utm_source")
                )
            )

            # Create cancellation message
            message = (
                "❌ Meeting Canceled\n\n"
                f"👤 Name: {payload.get('name', 'Not provided')}\n"
                f"📅 Event: {event_name}\n"
                f"⏰ Original Time: {event_start_time}\n"
                f"❓ Reason: {cancellation.get('reason', 'No reason provided')}\n"
                f"📝 Status: Canceled"
            )

            # Send WhatsApp notification if ID is available
            if wa_id:
                logging.info(
                    f"Sending cancellation notification to WhatsApp ID: {wa_id}"
                )
                try:
                    response = send_message(get_text_message_input(wa_id, message))
                    logging.info(f"WhatsApp API response: {response}")
                except Exception as e:
                    logging.error(f"Failed to send WhatsApp message: {e}")
            else:
                logging.warning("No WhatsApp ID found in tracking data")

        else:
            logging.info(f"Received unhandled event type: {event_type}")

        return jsonify({"status": "success"}), 200

    except Exception as e:
        logging.error(f"Error processing Calendly webhook: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500
