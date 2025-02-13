import logging


from app.services.openai_service import generate_response
from app.services.inventory_service import InventoryAssistantService
from .document_utils import handle_document_message
from .message_utils import get_text_message_input, send_message
from .state_manager import state_manager, UserState
import re
import asyncio
from app.services.calendly_service import CalendlyAssistantService

# Initialize the InventoryAssistantService
inventory_assistant = InventoryAssistantService()
calendly_assistant = CalendlyAssistantService()


def log_http_response(response):
    logging.info(f"Status: {response.status_code}")
    logging.info(f"Content-type: {response.headers.get('content-type')}")
    logging.info(f"Body: {response.text}")


def process_text_for_whatsapp(text):
    # Remove brackets
    pattern = r"\【.*?\】"
    # Substitute the pattern with an empty string
    text = re.sub(pattern, "", text).strip()

    # Pattern to find double asterisks including the word(s) in between
    pattern = r"\*\*(.*?)\*\*"

    # Replacement pattern with single asterisks
    replacement = r"*\1*"

    # Substitute occurrences of the pattern with the replacement
    whatsapp_style_text = re.sub(pattern, replacement, text)

    return whatsapp_style_text


async def get_response_by_state(wa_id: str, name: str, message_text: str = None) -> str:
    """
    Get the appropriate response based on user's current state
    """
    current_state = state_manager.get_user_state(wa_id)

    if current_state is None or current_state == UserState.INITIAL:
        return (
            f"Hello {name}! 👋\n\n"
            "To proceed with verification, please upload:\n"
            "1. Your PDF document\n"
            "2. The corresponding signature.json file"
        )

    elif current_state == UserState.PDF_RECEIVED:
        files = state_manager.get_user_files(wa_id)
        return (
            "I've received your PDF document. ✅\n\n"
            "Please upload the signature.json file to complete verification."
        )

    elif current_state == UserState.JSON_RECEIVED:
        return (
            "I've received your signature file. ✅\n\n"
            "Please upload the PDF document to complete verification."
        )

    elif current_state == UserState.VERIFICATION_COMPLETE:
        verification_status = state_manager.get_verification_status(wa_id)
        if verification_status and message_text:
            # Process Calendly queries
            if any(
                word in message_text.lower()
                for word in ["schedule", "meeting", "book", "appointment"]
            ):
                try:
                    calendly_response = await calendly_assistant.process_query(
                        message_text, wa_id
                    )
                    return calendly_response
                except Exception as e:
                    print(f"Error processing Calendly query: {e}")
                    return "I encountered an error with scheduling. Please try again."

            # Process inventory queries
            try:
                response = await inventory_assistant.process_query(message_text)
                return response
            except Exception as e:
                logging.error(f"Error processing inventory query: {e}")
                return (
                    "I can help you query our inventory system. Try asking questions like:\n"
                    "- What's in Storage Tank A?\n"
                    "- How much Natural Gas do we have?\n"
                    "- Who supplies our Diesel Fuel?"
                )
        elif verification_status:
            return (
                "Your document has been verified successfully. ✅\n\n"
                "You can now query our inventory system. Try asking questions like:\n"
                "- What's in Storage Tank A?\n"
                "- How much Natural Gas do we have?\n"
                "- Who supplies our Diesel Fuel?\n\n"
                "Or upload another set of documents for verification if needed."
            )
        else:
            return (
                "Previous verification failed. ❌\n\n"
                "Please upload a new set of documents to try again:\n"
                "1. Your PDF document\n"
                "2. The corresponding signature.json file"
            )

    else:
        return (
            "Please upload both your PDF document and signature.json file for verification.\n\n"
            "Note: You can send them in any order."
        )


def process_whatsapp_message(body):
    """
    Process incoming WhatsApp messages with state-based responses
    """
    # Extract user information
    wa_id = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
    name = body["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]

    # Initialize user state if needed
    state_manager.initialize_user(wa_id)

    message = body["entry"][0]["changes"][0]["value"]["messages"][0]

    # Handle document messages
    if "document" in message:
        return handle_document_message(message, wa_id, name)

    # Handle text messages
    elif "text" in message:
        message_text = message["text"]["body"]
        # Since get_response_by_state is now async, we need to handle it properly
        response = asyncio.run(get_response_by_state(wa_id, name, message_text))
        response = process_text_for_whatsapp(response)
        data = get_text_message_input(wa_id, response)
        return send_message(data)

    # Handle unsupported message types
    else:
        response = (
            "I can only process PDF documents and signature.json files.\n\n"
            "Please upload:\n"
            "1. Your PDF document\n"
            "2. The corresponding signature.json file"
        )
        data = get_text_message_input(wa_id, response)
        return send_message(data)


def is_valid_whatsapp_message(body):
    """
    Check if the incoming webhook event has a valid WhatsApp message structure.
    """
    return (
        body.get("object")
        and body.get("entry")
        and body["entry"][0].get("changes")
        and body["entry"][0]["changes"][0].get("value")
        and body["entry"][0]["changes"][0]["value"].get("messages")
        and body["entry"][0]["changes"][0]["value"]["messages"][0]
    )
