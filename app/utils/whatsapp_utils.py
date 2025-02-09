import logging


from app.services.openai_service import generate_response
from .document_utils import handle_document_message
from .message_utils import get_text_message_input, send_message
from .state_manager import state_manager, UserState
import re


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


def get_response_by_state(wa_id: str, name: str) -> str:
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
        if verification_status:
            return (
                "Your document has been verified successfully. ✅\n\n"
                "You can upload another set of documents for verification if needed."
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


# def process_whatsapp_message(body):
#     wa_id = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
#     name = body["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]
#     print(f"wa id is: {wa_id}")

#     message = body["entry"][0]["changes"][0]["value"]["messages"][0]
#     # message_body = message["text"]["body"]

#     # TODO: implement custom function here
#     # response = generate_response(message_body)

#     # Check if the message is a document
#     if "document" in message:
#         return handle_document_message(message, wa_id, name)

#     elif "text" in message:
#         message_body = message["text"]["body"]
#         # OpenAI Integration
#         response = generate_response(message_body, wa_id, name)
#         response = process_text_for_whatsapp(response)
#         data = get_text_message_input(wa_id, response)
#         return send_message(data)

#     # Handle unsupported message types
#     else:
#         response = (
#             "Sorry, I can only process text messages and PDF documents at the moment."
#         )
#         data = get_text_message_input(wa_id, response)
#         return send_message(data)


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

    # Handle text messages with fixed responses
    elif "text" in message:
        response = get_response_by_state(wa_id, name)
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
