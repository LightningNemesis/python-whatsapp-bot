import logging
from flask import current_app
import json
import os
import requests
from werkzeug.utils import secure_filename

from app.utils.message_utils import get_text_message_input, send_message
from app.utils.state_manager import state_manager, UserState
from app.services.web3_service import verify_object_signature


def handle_document_message(message, wa_id, name):
    """
    Handle incoming document messages with state management
    """
    print(f"\n=== Processing document for user {wa_id} ===")
    logging.info(f"Processing document message for user {wa_id}")

    # Initialize user state if not exists
    state_manager.initialize_user(wa_id)
    print(f"User state initialized: {wa_id}")
    logging.debug(f"User state initialized for {wa_id}")

    if "document" not in message:
        print("❌ No document found in message")
        logging.warning(f"No document found in message for user {wa_id}")
        return send_prompt_message(wa_id)

    document = message["document"]
    mime_type = document["mime_type"]
    filename = document.get("filename", "document.pdf")
    print(f"📄 Received: {filename} ({mime_type})")
    logging.info(f"Received document: {filename} ({mime_type}) from user {wa_id}")

    # Validate file type
    if mime_type != "application/pdf" and not filename.endswith(".json"):
        print(f"❌ Invalid file type: {mime_type}")
        logging.warning(
            f"Invalid file type received from {wa_id}: {mime_type}, filename: {filename}"
        )
        return send_error_message(
            wa_id, "Please send either a PDF file or the signature.json file."
        )

    try:
        # Process and save the file
        print(f"Saving document...")
        logging.info(f"Attempting to save document for user {wa_id}")
        file_path = save_document(document, wa_id)
        print(f"✅ Saved to: {file_path}")
        logging.debug(f"Document saved at: {file_path}")

        # Verify file was actually saved
        if not os.path.exists(file_path):
            print(f"❌ File not found after save: {file_path}")
            logging.error(f"File not found after save attempt: {file_path}")
            raise FileNotFoundError(f"Failed to save file at {file_path}")

        # Update state based on file type
        if mime_type == "application/pdf":
            print("Processing PDF file...")
            logging.info(f"Processing PDF file for user {wa_id}")
            state_manager.add_file(wa_id, "pdf", file_path, filename)
            current_state = state_manager.get_user_state(wa_id)
            print(f"Current state: {current_state}")
            logging.debug(f"Current state after PDF upload: {current_state}")

            if current_state == UserState.VERIFICATION_IN_PROGRESS:
                print("Starting verification...")
                logging.info(
                    f"Both files received, starting verification for user {wa_id}"
                )
                return verify_documents(wa_id)
            else:
                return send_json_request_message(wa_id, filename)

        else:  # JSON file
            print("Processing JSON file...")
            logging.info(f"Processing JSON file for user {wa_id}")
            state_manager.add_file(wa_id, "json", file_path, filename)
            current_state = state_manager.get_user_state(wa_id)
            print(f"Current state: {current_state}")
            logging.debug(f"Current state after JSON upload: {current_state}")

            if current_state == UserState.VERIFICATION_IN_PROGRESS:
                print("Starting verification...")
                logging.info(
                    f"Both files received, starting verification for user {wa_id}"
                )
                return verify_documents(wa_id)
            else:
                return send_pdf_request_message(wa_id, filename)

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        logging.error(
            f"Error processing document for user {wa_id}: {str(e)}", exc_info=True
        )
        cleanup_user_files(wa_id)
        state_manager.clear_user_state(wa_id)
        return send_error_message(wa_id, f"Failed to process document: {str(e)}")


def save_document(document, wa_id):
    """
    Save the document and return the file path
    """
    document_id = document["id"]
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    print(f"\n=== Saving document {document_id} ===")
    logging.info(f"Saving document {document_id} for user {wa_id}")

    # Ensure directory exists with proper permissions
    try:
        os.makedirs(upload_folder, exist_ok=True)
        print(f"Upload directory ready: {upload_folder}")
        logging.debug(f"Upload directory confirmed: {upload_folder}")
    except Exception as e:
        print(f"❌ Failed to create directory: {str(e)}")
        logging.error(f"Failed to create upload directory: {str(e)}", exc_info=True)
        raise

    # Check directory is writable
    if not os.access(upload_folder, os.W_OK):
        print(f"❌ Upload directory not writable: {upload_folder}")
        logging.error(f"Upload directory not writable: {upload_folder}")
        raise PermissionError(f"Upload directory {upload_folder} is not writable")

    # Create secure filename
    filename = document.get("filename", "document.pdf")
    temp_filename = f"{document_id}_{secure_filename(filename)}"
    temp_path = os.path.join(upload_folder, temp_filename)
    print(f"Generated path: {temp_path}")
    logging.debug(f"Generated temp path: {temp_path}")

    # Get document URL and download
    headers = {"Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}"}
    url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{document_id}"

    print("Requesting media URL...")
    logging.debug(f"Requesting media URL for document {document_id}")
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"❌ Failed to get media URL: {response.status_code}")
        logging.error(
            f"Failed to get media URL. Status: {response.status_code}, Response: {response.text}"
        )
        raise Exception(f"Failed to get media URL: {response.text}")

    media_url = response.json().get("url")
    if not media_url:
        print("❌ Media URL not found in response")
        logging.error("Media URL not found in Facebook API response")
        raise Exception("Media URL not found in response")

    print("Downloading file...")
    logging.debug("Downloading file from media URL")
    response = requests.get(media_url, headers=headers)
    if response.status_code != 200:
        print(f"❌ Download failed: {response.status_code}")
        logging.error(f"Failed to download file. Status: {response.status_code}")
        raise Exception("Failed to download file")

    try:
        with open(temp_path, "wb") as f:
            f.write(response.content)
        print("✅ File saved successfully")
        logging.info(f"Successfully saved file to {temp_path}")
    except Exception as e:
        print(f"❌ Failed to write file: {str(e)}")
        logging.error(f"Failed to write file to disk: {str(e)}", exc_info=True)
        raise

    return temp_path


def verify_documents(wa_id):
    """
    Verify the uploaded documents
    """
    print(f"\n=== Starting verification for user {wa_id} ===")
    logging.info(f"Starting document verification for user {wa_id}")
    files = state_manager.get_user_files(wa_id)
    print(f"Files to verify: {files}")
    logging.debug(f"Retrieved files for verification: {files}")

    try:
        # Copy file paths before verification
        json_path = files["json_path"]
        pdf_path = files["pdf_path"]
        print(f"JSON Path: {json_path}")
        print(f"PDF Path: {pdf_path}")
        logging.debug(f"Verifying files - JSON: {json_path}, PDF: {pdf_path}")

        # Verify both files exist
        if not all(os.path.exists(path) for path in [json_path, pdf_path]):
            print("❌ One or more files missing!")
            logging.error(f"Missing files during verification for user {wa_id}")
            raise FileNotFoundError("One or more files missing before verification")

        # Read and verify
        print("Reading signature data...")
        logging.info(f"Reading signature data from JSON file for user {wa_id}")
        with open(files["json_path"], "r") as f:
            signature_data = json.load(f)

        print("Verifying signature...")
        logging.info(f"Verifying signature for user {wa_id}")
        is_verified = verify_object_signature(
            address=signature_data["address"],
            data=signature_data["data"],
            signature=signature_data["signature"],
        )
        print(f"Verification result: {'✅ Valid' if is_verified else '❌ Invalid'}")
        logging.info(f"Verification result for user {wa_id}: {is_verified}")

        if is_verified:
            message = (
                "✅ Verification complete!\n\n"
                f"📄 Document: {files.get('pdf_name', 'document.pdf')}\n"
                f"🔍 Verification result: Valid ✅\n\n"
                "I can help you query our inventory system. Try asking:\n\n"
                "1. What items are in Storage Tank A?\n"
                "2. How much Natural Gas do we have?\n"
                "3. Show me all suppliers\n"
                "4. What's our total inventory in MCF?\n"
                "5. Give me details about Pipeline B"
            )
        else:
            message = (
                "❌ Verification failed\n\n"
                "Please upload a new set of documents to try again:\n"
                "1. Your PDF document\n"
                "2. The corresponding signature.json file"
            )

        state_manager.set_verification_status(wa_id, is_verified)
        logging.info(f"Verification status set for user {wa_id}: {is_verified}")

    except FileNotFoundError as e:
        print(f"❌ File not found: {str(e)}")
        logging.error(f"File access error for user {wa_id}: {str(e)}")
        message = (
            "❌ Verification failed: Files not found\n\n"
            "Please upload both files again:\n"
            "1. Your PDF document\n"
            "2. The corresponding signature.json file"
        )
        state_manager.clear_user_state(wa_id)
    except Exception as e:
        print(f"❌ Verification error: {str(e)}")
        logging.error(f"Verification error for user {wa_id}: {str(e)}", exc_info=True)
        message = (
            "❌ Verification failed\n\n"
            "Please upload a new set of documents to try again:\n"
            "1. Your PDF document\n"
            "2. The corresponding signature.json file"
        )
        state_manager.clear_user_state(wa_id)
    finally:
        print("\n=== Cleaning up files ===")
        logging.info(f"Starting cleanup for user {wa_id}")
        cleanup_user_files(wa_id)

    return send_message(get_text_message_input(wa_id, message))


def cleanup_user_files(wa_id):
    """
    Clean up user files after processing
    """
    print(f"Starting cleanup for user {wa_id}")
    logging.info(f"Starting file cleanup for user {wa_id}")
    files = state_manager.get_user_files(wa_id)

    for key, file_path in files.items():
        if key.endswith("_path") and isinstance(file_path, str):
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"Removed: {file_path}")
                    logging.info(f"Successfully removed file: {file_path}")
                else:
                    print(f"File not found: {file_path}")
                    logging.warning(f"File not found during cleanup: {file_path}")
            except Exception as e:
                print(f"❌ Error removing {file_path}: {str(e)}")
                logging.error(
                    f"Error removing file {file_path}: {str(e)}", exc_info=True
                )


def send_prompt_message(wa_id):
    """
    Send initial prompt message
    """
    print(f"Sending prompt message to user {wa_id}")
    logging.info(f"Sending prompt message to user {wa_id}")
    message = "Please upload your PDF and signature.json files for verification."
    return send_message(get_text_message_input(wa_id, message))


def send_error_message(wa_id, error_text):
    """
    Send error message
    """
    print(f"Sending error message to user {wa_id}: {error_text}")
    logging.info(f"Sending error message to user {wa_id}: {error_text}")
    return send_message(get_text_message_input(wa_id, error_text))


def send_json_request_message(wa_id, pdf_name):
    """
    Request JSON file after PDF received
    """
    print(f"Requesting JSON file from user {wa_id}")
    logging.info(f"Requesting JSON file from user {wa_id}")
    message = (
        f"✅ PDF received successfully!\n\n"
        f"📄 Document: {pdf_name}\n"
        f"Please send the signature.json file to verify the document."
    )
    return send_message(get_text_message_input(wa_id, message))


def send_pdf_request_message(wa_id, json_name):
    """
    Request PDF file after JSON received
    """
    print(f"Requesting PDF file from user {wa_id}")
    logging.info(f"Requesting PDF file from user {wa_id}")
    message = (
        f"✅ Signature file received!\n\n"
        f"Please send the PDF file to verify against this signature."
    )
    return send_message(get_text_message_input(wa_id, message))
