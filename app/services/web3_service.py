from PyPDF2 import PdfReader
import json
from eth_account import Account
from eth_account.messages import encode_defunct
import os
import logging
from datetime import datetime


def extract_text_from_pdf(pdf_path):
    """
    Extract all text from a PDF file.

    Args:
        pdf_path (str): Path to the PDF file

    Returns:
        str: Extracted text from all pages

    Raises:
        FileNotFoundError: If the PDF file is not found
        PyPDF2.PdfReadError: If there's an error reading the PDF
    """
    try:
        # Create a PDF reader object
        reader = PdfReader(pdf_path)

        # Get total number of pages
        num_pages = len(reader.pages)

        # Extract text from all pages
        text = ""
        for page_num in range(num_pages):
            # Get the page object
            page = reader.pages[page_num]

            # Extract text from page
            text += page.extract_text()

            # Add a newline between pages for better readability
            if page_num < num_pages - 1:
                text += "\n\n"

        return text

    except FileNotFoundError:
        raise FileNotFoundError(f"PDF file not found at path: {pdf_path}")
    except Exception as e:
        raise Exception(f"Error extracting text from PDF: {str(e)}")


def verify_object_signature(address: str, data: dict, signature: str) -> bool:
    """
    Verify if a signature matches the given address and object data

    :param address: Ethereum address that supposedly signed the message
    :param data: Original data dictionary
    :param signature: Signature to verify (hex string)
    :return: Boolean indicating signature validity
    """
    # Ensure signature has '0x' prefix
    if not signature.startswith("0x"):
        signature = "0x" + signature

    # Convert the object to a JSON string with sorted keys for consistency
    message = json.dumps(data, sort_keys=True)

    # Encode the message
    encoded_message = encode_defunct(text=message)

    try:
        # Recover the signing address
        recovered_address = Account.recover_message(
            encoded_message, signature=bytes.fromhex(signature[2:])
        )

        # Compare recovered address with provided address
        return recovered_address.lower() == address.lower()

    except Exception:
        return False


def sign_object(private_key: str, data: dict) -> dict:
    """
    Sign an object using an Ethereum private key

    :param private_key: Ethereum private key (with or without '0x' prefix)
    :param data: Dictionary containing the data to sign
    :return: Dictionary containing signature details
    """
    # Ensure private key has '0x' prefix
    if not private_key.startswith("0x"):
        private_key = "0x" + private_key

    # Create account from private key
    account = Account.from_key(private_key)

    # Convert the object to a JSON string with sorted keys for consistency
    message = json.dumps(data, sort_keys=True)

    # Encode the message
    encoded_message = encode_defunct(text=message)

    # Sign the message
    signed_message = account.sign_message(encoded_message)

    return {
        "address": account.address,
        "data": data,
        "signature": signed_message.signature.hex(),
    }


def sign_pdf_text(pdf_path, wa_id):
    """
    Signs the text content of a PDF file and saves the signature as JSON.

    Args:
        pdf_path (str): Path to the PDF file
        wa_id (str): WhatsApp ID of the user

    Returns:
        tuple: (dict: Contains address, data, and signature, str: Path to signature file)
    """
    try:
        # Extract text and create signature
        extracted_text = extract_text_from_pdf(pdf_path)
        private_key = os.getenv("PRIVATE_KEY")
        data = {"content": extracted_text, "phone_number": wa_id}
        signing_result = sign_object(private_key, data)

        # Create signature filename based on PDF filename
        pdf_filename = os.path.basename(pdf_path)
        pdf_name = os.path.splitext(pdf_filename)[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        signature_filename = f"{pdf_name}_signature_{timestamp}.json"

        # Get the directory of the PDF and create a signatures subdirectory
        pdf_dir = os.path.dirname(pdf_path)
        signatures_dir = os.path.join(pdf_dir, "signatures")
        os.makedirs(signatures_dir, exist_ok=True)

        # Full path for signature file
        signature_path = os.path.join(signatures_dir, signature_filename)

        # Save signature to JSON file
        with open(signature_path, "w") as f:
            json.dump(signing_result, f, indent=2)

        return signing_result, signature_path

    except Exception as e:
        logging.error(f"Error in sign_pdf_text: {str(e)}")
        raise


def verify_pdf_signature(signing_result):
    """
    Verifies a previously generated PDF signature.

    Args:
        signing_result (dict): The result from sign_pdf_text containing address, data, and signature

    Returns:
        bool: True if signature is valid, False otherwise
    """
    return verify_object_signature(
        address=signing_result["address"],
        data=signing_result["data"],
        signature=signing_result["signature"],
    )


# base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# file_path = os.path.join(base_dir, "data", "airbnb-faq.pdf")


# # Sign the PDF text
# signature_data = sign_pdf_text(file_path, wa_id="2139135416")

# # Print the signature details
# print("Signing Address:", signature_data["address"])
# print("Signed Data:", signature_data["data"])
# print("Signature:", signature_data["signature"])

# # Then verify the signature in a separate call
# is_verified = verify_pdf_signature(signature_data)
# print("Signature Verification Result:", is_verified)

# try:
#     signing_result, signature_path = sign_pdf_text(file_path, "12139135416")
#     print(f"Signature saved to: {signature_path}")
# except Exception as e:
#     print(f"Failed to sign PDF: {str(e)}")
