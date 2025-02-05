import logging
from flask import current_app, jsonify
import json
import requests

from app.services.openai_service import generate_response
import re

from ..services.web3_service import Web3Service
import redis
from eth_account import Account
from eth_account.messages import encode_defunct
from datetime import datetime

import requests
import PyPDF2
import io

# Initialize redis and web3_service at module level
redis_client = redis.Redis(host="localhost", port=6379, db=0)
web3_service = Web3Service(redis_client)


def log_http_response(response):
    logging.info(f"Status: {response.status_code}")
    logging.info(f"Content-type: {response.headers.get('content-type')}")
    logging.info(f"Body: {response.text}")


def get_text_message_input(recipient, text):
    return json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
    )


def extract_text_from_pdf(document_id):
    """Download and extract text content from PDF from WhatsApp"""
    try:
        # Get document URL from WhatsApp API
        headers = {
            "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
            "User-Agent": "WhatsApp/2.24.2.82",  # Add User-Agent header
        }

        url = (
            f"https://graph.facebook.com/{current_app.config['VERSION']}/{document_id}"
        )

        # Get the document URL from WhatsApp
        response = requests.get(url, headers=headers)
        if not response.ok:
            logging.error(f"Failed to fetch document URL: {response.text}")
            raise Exception("Failed to fetch document URL from WhatsApp")

        document_url = response.json().get("url")
        if not document_url:
            raise Exception("Document URL not found in response")

        # Download PDF with same headers
        pdf_response = requests.get(
            document_url, headers=headers, timeout=30  # Add timeout
        )
        if not pdf_response.ok:
            logging.error(f"Failed to download PDF: {pdf_response.text}")
            raise Exception("Failed to download PDF")

        # Create PDF reader object
        pdf_file = io.BytesIO(pdf_response.content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)

        # Extract text from all pages
        text_content = ""
        for page in pdf_reader.pages:
            text_content += page.extract_text()

        # Clean and normalize text
        text_content = " ".join(text_content.split())

        if not text_content:
            raise Exception("No text content extracted from PDF")

        return text_content

    except Exception as e:
        logging.error(f"Error extracting PDF text: {str(e)}")
        raise Exception("Failed to extract text from PDF document")


# [Pending]
def sign_with_org_key(content, phone_number):
    """Sign content with organization's private key"""
    # Implement organizational signing
    private_key = current_app.config["PRIVATE_KEY"]
    print(f"Private key is {private_key}")

    # Combine content and phone number into a single message
    message = f"{content}:{phone_number}"

    # Encode the message for signing
    encoded_message = encode_defunct(text=message)

    # Sign the message using the private key
    signed_message = Account.sign_message(encoded_message, private_key=private_key)

    # Return the signature in hex format
    return signed_message.signature.hex()


def send_document_message(wa_id, signature_json):
    """Send signature file via WhatsApp"""
    # First send the LOI document
    loi_data = json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": wa_id,
            "type": "document",
            "document": {
                "link": signature_json["text_content"],
                "caption": "Here is your LOI document for reference",
            },
        }
    )
    send_message(loi_data)

    # Then send the signature JSON file
    signature_message = (
        f"Signature Information:\n"
        f"Document Hash: {signature_json['text_content']}\n"
        f"Signature: {signature_json['signature']}\n"
        f"Phone Number: {signature_json['phone_number']}"
    )

    data = get_text_message_input(wa_id, signature_message)
    send_message(data)

    # Send instructions
    instructions = (
        "Please save this signature information. "
        "You'll need it for verification when scheduling meetings. "
        "To schedule a meeting, simply send 'schedule meeting'."
    )

    data = get_text_message_input(wa_id, instructions)
    send_message(data)


def create_verification_url(session_id):
    """Create MetaMask deep link for verification"""
    # Implement deep link generation
    pass


def schedule_meeting(wa_id):
    """Handle actual meeting scheduling"""
    # Implement calendar integration
    pass


def handle_document_message(message, wa_id):
    """Handle incoming document messages"""

    # Download and extract text content from PDF
    document_id = message.get("document", {}).get("id", "")
    text_content = extract_text_from_pdf(document_id)  # New function needed

    # Sign content with organization's private key
    signature = sign_with_org_key(text_content, wa_id)  # New function needed

    # Store signature in JSON format
    signature_json = {
        "text_content": text_content,
        "signature": signature,
        "phone_number": wa_id,
        "timestamp": datetime.now().isoformat(),
    }
    print(f"Signature JSON is {signature_json}")

    # Create signing session
    session_id = web3_service.create_signing_session(wa_id, signature_json)

    # # Generate signing URL
    # signing_url = f"https://immune-grand-bulldog.ngrok-free.app/sign/{session_id}"

    # # Send response message
    # response = f"""I've received your LOI document. To sign it, please click this link:
    # {signing_url}

    # You'll need to scan a QR code with your preferred wallet app."""

    # Send signature file in chat
    send_document_message(wa_id, signature_json)  # New function needed

    # data = get_text_message_input(wa_id, response)
    # print(f"Data is {data}")
    # send_message(data)


# def generate_response(response):
#     # Return text in uppercase
#     return response.upper()


def send_message(data):
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
    }

    url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{current_app.config['PHONE_NUMBER_ID']}/messages"

    try:
        response = requests.post(
            url, data=data, headers=headers, timeout=10
        )  # 10 seconds timeout as an example
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
    except requests.Timeout:
        logging.error("Timeout occurred while sending message")
        return jsonify({"status": "error", "message": "Request timed out"}), 408
    except (
        requests.RequestException
    ) as e:  # This will catch any general request exception
        logging.error(f"Request failed due to: {e}")
        return jsonify({"status": "error", "message": "Failed to send message"}), 500
    else:
        # Process the response as normal
        log_http_response(response)
        return response


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


def process_whatsapp_message(body):
    wa_id = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
    name = body["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]

    message = body["entry"][0]["changes"][0]["value"]["messages"][0]
    print(f"message is {message}")

    # Handle different message types
    if "document" in message:
        handle_document_message(message, wa_id)
        return

    message_body = message["text"]["body"]

    # Check if this is a meeting request
    if message_body.lower() == "schedule meeting":
        # Create verification session
        session_id = web3_service.create_signing_session(wa_id, None)
        verify_url = f"https://immune-grand-bulldog.ngrok-free.app/verify/{session_id}"

        response = f"""Please verify your wallet ownership first.
        Click here to verify: {verify_url}"""

        data = get_text_message_input(wa_id, response)
        send_message(data)
        return

    # TODO: implement custom function here
    # response = generate_response(message_body)

    # OpenAI Integration
    response = generate_response(message_body, wa_id, name)
    response = process_text_for_whatsapp(response)

    data = get_text_message_input(current_app.config["RECIPIENT_WAID"], response)
    send_message(data)


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
