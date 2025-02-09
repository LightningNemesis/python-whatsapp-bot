import logging
from flask import current_app
import json
import os
import requests
from werkzeug.utils import secure_filename

from .message_utils import get_text_message_input, send_message
from .state_manager import state_manager, UserState
from app.services.web3_service import verify_object_signature


def handle_document_message(message, wa_id, name):
    """
    Handle incoming document messages with state management
    """
    # Initialize user state if not exists
    state_manager.initialize_user(wa_id)

    if "document" not in message:
        return send_prompt_message(wa_id)

    document = message["document"]
    mime_type = document["mime_type"]
    filename = document.get("filename", "document.pdf")

    # Validate file type
    if mime_type != "application/pdf" and not filename.endswith(".json"):
        return send_error_message(
            wa_id, "Please send either a PDF file or the signature.json file."
        )

    try:
        # Process and save the file
        file_path = save_document(document, wa_id)

        # Update state based on file type
        if mime_type == "application/pdf":
            state_manager.add_file(wa_id, "pdf", file_path, filename)
            current_state = state_manager.get_user_state(wa_id)

            if current_state == UserState.VERIFICATION_IN_PROGRESS:
                return verify_documents(wa_id)
            else:
                return send_json_request_message(wa_id, filename)

        else:  # JSON file
            state_manager.add_file(wa_id, "json", file_path, filename)
            current_state = state_manager.get_user_state(wa_id)

            if current_state == UserState.VERIFICATION_IN_PROGRESS:
                return verify_documents(wa_id)
            else:
                return send_pdf_request_message(wa_id, filename)

    except Exception as e:
        logging.error(f"Error processing document: {str(e)}")
        cleanup_user_files(wa_id)
        state_manager.clear_user_state(wa_id)
        return send_error_message(wa_id, f"Failed to process document: {str(e)}")


def save_document(document, wa_id):
    """
    Save the document and return the file path
    """
    document_id = document["id"]
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)

    # Create secure filename
    filename = document.get("filename", "document.pdf")
    temp_filename = f"{document_id}_{secure_filename(filename)}"
    temp_path = os.path.join(upload_folder, temp_filename)

    # Get document URL and download
    headers = {"Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}"}
    url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{document_id}"

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Failed to get media URL: {response.text}")

    media_url = response.json().get("url")
    if not media_url:
        raise Exception("Media URL not found in response")

    response = requests.get(media_url, headers=headers)
    if response.status_code != 200:
        raise Exception("Failed to download file")

    with open(temp_path, "wb") as f:
        f.write(response.content)

    return temp_path


def verify_documents(wa_id):
    """
    Verify the uploaded documents
    """
    files = state_manager.get_user_files(wa_id)

    try:
        # First verify file existence
        if not os.path.exists(files["json_path"]):
            raise FileNotFoundError(f"JSON file not found at {files['json_path']}")
        if not os.path.exists(files["pdf_path"]):
            raise FileNotFoundError(f"PDF file not found at {files['pdf_path']}")

        # Read and verify
        with open(files["json_path"], "r") as f:
            signature_data = json.load(f)

        is_verified = verify_object_signature(
            address=signature_data["address"],
            data=signature_data["data"],
            signature=signature_data["signature"],
        )

        # Prepare response before cleanup
        message = (
            "✅ Verification complete!\n\n"
            f"📄 Document: {files.get('pdf_name', 'document.pdf')}\n"
            f"🔍 Verification result: {'Valid ✅' if is_verified else 'Invalid ❌'}"
        )

        # Set verification status
        state_manager.set_verification_status(wa_id, is_verified)

    except FileNotFoundError as e:
        logging.error(f"File access error: {str(e)}")
        message = (
            "❌ Verification failed: Files not found. Please upload both files again.\n\n"
            "1. Your PDF document\n"
            "2. The corresponding signature.json file"
        )
        state_manager.clear_user_state(wa_id)
    except Exception as e:
        logging.error(f"Verification error: {str(e)}")
        message = f"❌ Verification failed: {str(e)}"
        state_manager.clear_user_state(wa_id)
    finally:
        # Cleanup after preparing the message
        cleanup_user_files(wa_id)

    return send_message(get_text_message_input(wa_id, message))


def cleanup_user_files(wa_id):
    """
    Clean up user files after processing
    """
    files = state_manager.get_user_files(wa_id)
    for key, file_path in files.items():
        if key.endswith("_path") and isinstance(file_path, str):
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logging.info(f"Successfully removed file: {file_path}")
            except Exception as e:
                logging.error(f"Error removing file {file_path}: {str(e)}")


# Message sending helper functions
def send_prompt_message(wa_id):
    message = "Please upload your PDF and signature.json files for verification."
    return send_message(get_text_message_input(wa_id, message))


def send_error_message(wa_id, error_text):
    return send_message(get_text_message_input(wa_id, error_text))


def send_json_request_message(wa_id, pdf_name):
    message = (
        f"✅ PDF received successfully!\n\n"
        f"📄 Document: {pdf_name}\n"
        f"Please send the signature.json file to verify the document."
    )
    return send_message(get_text_message_input(wa_id, message))


def send_pdf_request_message(wa_id, json_name):
    message = (
        f"✅ Signature file received!\n\n"
        f"Please send the PDF file to verify against this signature."
    )
    return send_message(get_text_message_input(wa_id, message))
