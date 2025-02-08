import logging
from flask import current_app, jsonify
import json
import requests
from werkzeug.utils import secure_filename
import os
from collections import defaultdict

from app.services.openai_service import generate_response
from app.services.web3_service import verify_object_signature
import re

# Add this after the imports
user_files = defaultdict(dict)  # Store user's uploaded files


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


# def generate_response(response):
#     # Return text in uppercase
#     return response.upper()


def send_message(data):
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
    }

    print(f"version is {current_app.config['VERSION']}")
    print(f"access token is {current_app.config['ACCESS_TOKEN']}")

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


def handle_document_message(message, wa_id, name):
    """
    Handle incoming document messages from WhatsApp
    """
    document = message["document"]
    mime_type = document["mime_type"]
    filename = document.get("filename", "document.pdf")

    # Check if it's a PDF or JSON
    if mime_type != "application/pdf" and not filename.endswith(".json"):
        response = "Please send either a PDF file or the signature.json file."
        data = get_text_message_input(wa_id, response)
        return send_message(data)

    try:
        document_id = document["id"]

        # Create upload directory if it doesn't exist
        upload_folder = current_app.config["UPLOAD_FOLDER"]
        os.makedirs(upload_folder, exist_ok=True)

        # Use secure filename and create full path
        temp_filename = f"{document_id}_{secure_filename(filename)}"
        temp_path = os.path.join(upload_folder, temp_filename)

        # Get the document download URL
        headers = {"Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}"}
        url = (
            f"https://graph.facebook.com/{current_app.config['VERSION']}/{document_id}"
        )

        # Get the media URL
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Failed to get media URL: {response.text}")

        media_url = response.json().get("url")
        if not media_url:
            raise Exception("Media URL not found in response")

        # Download the actual file
        response = requests.get(media_url, headers=headers)
        if response.status_code != 200:
            raise Exception("Failed to download file")

        # Save the file temporarily
        with open(temp_path, "wb") as f:
            f.write(response.content)

        # Store file paths based on type
        if mime_type == "application/pdf":
            user_files[wa_id]["pdf_path"] = temp_path
            response_message = (
                f"✅ PDF received successfully!\n\n"
                f"📄 Document: {filename}\n"
                f"Please send the signature.json file to verify the document."
            )
        else:  # JSON file
            user_files[wa_id]["json_path"] = temp_path

            # If both files are present, verify the signature
            if "pdf_path" in user_files[wa_id]:
                try:
                    # Load the signature JSON
                    with open(temp_path, "r") as f:
                        signature_data = json.load(f)

                    # Verify the signature
                    is_verified = verify_object_signature(
                        address=signature_data["address"],
                        data=signature_data["data"],
                        signature=signature_data["signature"],
                    )

                    response_message = (
                        "✅ Verification complete!\n\n"
                        f"📄 Document: {filename}\n"
                        f"🔍 Verification result: {'Valid ✅' if is_verified else 'Invalid ❌'}"
                    )

                    # Clean up files after verification
                    os.remove(user_files[wa_id]["pdf_path"])
                    os.remove(temp_path)
                    del user_files[wa_id]

                except Exception as e:
                    response_message = f"❌ Verification failed: {str(e)}"
            else:
                response_message = (
                    f"✅ Signature file received!\n\n"
                    f"Please send the PDF file to verify against this signature."
                )

        data = get_text_message_input(wa_id, response_message)
        return send_message(data)

    except Exception as e:
        logging.error(f"Error processing document: {str(e)}")
        error_message = f"Failed to process document: {str(e)}"
        data = get_text_message_input(wa_id, error_message)
        return send_message(data)


def process_whatsapp_message(body):
    wa_id = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
    name = body["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]
    print(f"wa id is: {wa_id}")

    message = body["entry"][0]["changes"][0]["value"]["messages"][0]
    # message_body = message["text"]["body"]

    # TODO: implement custom function here
    # response = generate_response(message_body)

    # Check if the message is a document
    if "document" in message:
        return handle_document_message(message, wa_id, name)

    elif "text" in message:
        message_body = message["text"]["body"]
        response = generate_response(message_body, wa_id, name)
        response = process_text_for_whatsapp(response)
        data = get_text_message_input(wa_id, response)
        return send_message(data)

    # Handle unsupported message types
    else:
        response = (
            "Sorry, I can only process text messages and PDF documents at the moment."
        )
        data = get_text_message_input(wa_id, response)
        return send_message(data)

    # OpenAI Integration
    # response = generate_response(message_body, wa_id, name)
    # response = process_text_for_whatsapp(response)

    # data = get_text_message_input(current_app.config["RECIPIENT_WAID"], response)
    # send_message(data)


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
