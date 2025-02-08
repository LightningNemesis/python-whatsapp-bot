import logging
from flask import current_app, jsonify
import json
import requests
from werkzeug.utils import secure_filename
import os
from collections import defaultdict

# from .whatsapp_utils import get_text_message_input, send_message
from .message_utils import get_text_message_input, send_message
from app.services.web3_service import verify_object_signature
import re

user_files = defaultdict(dict)  # Store user's uploaded files


def handle_document_message(message, wa_id, name):
    """
    Handle incoming document messages from WhatsApp
    """
    if "document" not in message:
        response = "Please send both the PDF and signature.json files."
        data = get_text_message_input(wa_id, response)
        return send_message(data)

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
            user_files[wa_id]["pdf_name"] = filename

            # Check if JSON is already present
            if "json_path" in user_files[wa_id]:
                return verify_and_cleanup(
                    wa_id, user_files[wa_id]["json_path"], temp_path
                )
            else:
                response_message = (
                    f"✅ PDF received successfully!\n\n"
                    f"📄 Document: {filename}\n"
                    f"Please send the signature.json file to verify the document."
                )
        else:  # JSON file
            user_files[wa_id]["json_path"] = temp_path
            user_files[wa_id]["json_name"] = filename

            # Check if PDF is already present
            if "pdf_path" in user_files[wa_id]:
                return verify_and_cleanup(
                    wa_id, temp_path, user_files[wa_id]["pdf_path"]
                )
            else:
                response_message = (
                    f"✅ Signature file received!\n\n"
                    f"Please send the PDF file to verify against this signature."
                )

        data = get_text_message_input(wa_id, response_message)
        return send_message(data)

    except Exception as e:
        # Clean up any stored files for this user in case of error
        if wa_id in user_files:
            for file_path in user_files[wa_id].values():
                if os.path.exists(file_path):
                    os.remove(file_path)
            del user_files[wa_id]

        logging.error(f"Error processing document: {str(e)}")
        error_message = f"Failed to process document: {str(e)}"
        data = get_text_message_input(wa_id, error_message)
        return send_message(data)


def verify_and_cleanup(wa_id, json_path, pdf_path):
    """
    Helper function to verify signatures and clean up files
    """
    try:
        # Load the signature JSON
        with open(json_path, "r") as f:
            signature_data = json.load(f)

        # Verify the signature
        is_verified = verify_object_signature(
            address=signature_data["address"],
            data=signature_data["data"],
            signature=signature_data["signature"],
        )

        response_message = (
            "✅ Verification complete!\n\n"
            f"📄 Document: {user_files[wa_id].get('pdf_name', 'document.pdf')}\n"
            f"🔍 Verification result: {'Valid ✅' if is_verified else 'Invalid ❌'}"
        )

    except Exception as e:
        response_message = f"❌ Verification failed: {str(e)}"
    finally:
        # Clean up files
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        if os.path.exists(json_path):
            os.remove(json_path)
        if wa_id in user_files:
            del user_files[wa_id]

    data = get_text_message_input(wa_id, response_message)
    return send_message(data)
