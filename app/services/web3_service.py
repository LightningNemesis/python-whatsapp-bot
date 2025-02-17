import os
import json
import logging
from web3 import Web3
from PyPDF2 import PdfReader
from datetime import datetime
from eth_account import Account
from eth_account.messages import encode_defunct


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


# def verify_object_signature(address: str, data: dict, signature: str) -> bool:
#     """
#     Verify if a signature matches the given address and object data

#     :param address: Ethereum address that supposedly signed the message
#     :param data: Original data dictionary
#     :param signature: Signature to verify (hex string)
#     :return: Boolean indicating signature validity
#     """
#     # Ensure signature has '0x' prefix
#     if not signature.startswith("0x"):
#         signature = "0x" + signature

#     # Convert the object to a JSON string with sorted keys for consistency
#     message = json.dumps(data, sort_keys=True)

#     # Encode the message
#     encoded_message = encode_defunct(text=message)

#     try:
#         # Recover the signing address
#         recovered_address = Account.recover_message(
#             encoded_message, signature=bytes.fromhex(signature[2:])
#         )

#         # Compare recovered address with provided address
#         return recovered_address.lower() == address.lower()

#     except Exception:
#         return False


# def verify_object_signature(address: str, data: dict, signature: str) -> bool:
#     try:
#         w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
#         print("\n=== Starting Verification Debug ===")

#         # Get content and phone number from data structure
#         document_text = data.get("data", {}).get("content", data.get("content", ""))
#         phone_number = data.get("data", {}).get(
#             "phone_number", data.get("phone_number", "")
#         )

#         print(f"Address to verify: {address}")
#         print(f"Document text length: {len(document_text)}")
#         print(f"Phone number: {phone_number}")

#         # Create hash exactly as the contract does
#         encoded_data = Web3.solidity_keccak(
#             ["string", "string"], [document_text, phone_number]
#         )
#         print(f"Initial hash: {encoded_data.hex()}")

#         # Create Ethereum signed message
#         message_to_verify = encode_defunct(encoded_data)
#         print(f"Ethereum formatted message: {message_to_verify.body.hex()}")

#         try:
#             # Local verification
#             print("\n=== Local Verification Debug ===")
#             signature_bytes = bytes.fromhex(
#                 signature[2:] if signature.startswith("0x") else signature
#             )

#             recovered_address = Account.recover_message(
#                 message_to_verify, signature=signature_bytes
#             )
#             print(f"Recovered address: {recovered_address}")
#             print(f"Expected address: {address}")

#             local_verification = recovered_address.lower() == address.lower()
#             print(f"Local verification result: {local_verification}")

#             # Smart contract verification
#             print("\n=== Smart Contract Verification Debug ===")
#             contract_address = Web3.to_checksum_address(
#                 "0x5fbdb2315678afecb367f032d93f642f64180aa3"
#             )
#             with open(os.path.join(os.path.dirname(__file__), "abi.json"), "r") as f:
#                 abi = json.load(f)
#             contract = w3.eth.contract(address=contract_address, abi=abi)

#             owner_private_key = (
#                 "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
#             )
#             owner_account = w3.eth.account.from_key(owner_private_key)
#             print(f"Contract owner address: {owner_account.address}")

#             # Contract call
#             gas_estimate = contract.functions.verifySignature(
#                 document_text, phone_number, signature_bytes
#             ).estimate_gas({"from": owner_account.address})

#             gas_limit = int(gas_estimate * 1.2)
#             print(f"Gas estimate: {gas_estimate}, limit: {gas_limit}")

#             tx = contract.functions.verifySignature(
#                 document_text, phone_number, signature_bytes
#             ).build_transaction(
#                 {
#                     "from": owner_account.address,
#                     "nonce": w3.eth.get_transaction_count(owner_account.address),
#                     "gas": gas_limit,
#                     "gasPrice": w3.eth.gas_price,
#                     "chainId": w3.eth.chain_id,
#                 }
#             )

#             signed_tx = w3.eth.account.sign_transaction(
#                 tx, private_key=owner_private_key
#             )
#             tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
#             print(f"Transaction hash: {tx_hash.hex()}")

#             receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
#             print(f"Transaction status: {receipt.status}")

#             events = contract.events.SignatureVerified().process_receipt(receipt)

#             if events:
#                 event = events[0]
#                 contract_verification = event.args.verified
#                 print(f"\nContract verification result: {contract_verification}")
#                 print(f"Event details: {event.args}")
#             else:
#                 print("\nNo verification events found")
#                 contract_verification = False

#             final_result = local_verification and contract_verification
#             print(f"\n=== Final Verification Result: {final_result} ===")
#             return final_result

#         except Exception as e:
#             print(f"\nError in verification step: {str(e)}")
#             return False

#     except Exception as e:
#         print(f"\nError in signature verification: {str(e)}")
#         return False


def verify_object_signature_no_data(file_path: str, signature: dict) -> bool:

    w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))

    # Extract text from PDF
    document_text = extract_text_from_pdf(file_path)
    print(f"Extracted text length: {len(document_text)}")

    # Get content and phone number from data structure
    phone_number = signature.get("data", {}).get("phone_number", "")

    # Create hash exactly as the contract does
    encoded_data = Web3.solidity_keccak(
        ["string", "string"], [document_text, phone_number]
    )

    # Create Ethereum signed message
    message_to_verify = encode_defunct(encoded_data)
    print(f"Ethereum formatted message: {message_to_verify.body.hex()}")

    try:
        # smart contract verification
        print("\n=== Smart Contract Verification Debug ===")
        contract_address = Web3.to_checksum_address(os.getenv("CONTRACT_ADDRESS"))
        print(f"Contract address: {contract_address}")

        with open(os.path.join(os.path.dirname(__file__), "abi.json"), "r") as f:
            abi = json.load(f)
        contract = w3.eth.contract(address=contract_address, abi=abi)

        owner_private_key = os.getenv("PRIVATE_KEY")
        print(f"Owner private key: {owner_private_key}")

        owner_account = w3.eth.account.from_key(owner_private_key)
        print(f"Contract owner address: {owner_account.address}")

        # Contract call
        gas_estimate = contract.functions.verifySignature(
            document_text, phone_number, signature["signature"]
        ).estimate_gas({"from": owner_account.address})

        gas_limit = int(gas_estimate * 1.2)
        print(f"Gas estimate: {gas_estimate}, limit: {gas_limit}")

        tx = contract.functions.verifySignature(
            document_text, phone_number, signature["signature"]
        ).build_transaction(
            {
                "from": owner_account.address,
                "nonce": w3.eth.get_transaction_count(owner_account.address),
                "gas": gas_limit,
                "gasPrice": w3.eth.gas_price,
                "chainId": w3.eth.chain_id,
            }
        )

        signed_tx = w3.eth.account.sign_transaction(tx, private_key=owner_private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f"Transaction hash: {tx_hash.hex()}")

        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Transaction status: {receipt.status}")

        events = contract.events.SignatureVerified().process_receipt(receipt)

        if events:
            event = events[0]
            contract_verification = event.args.verified
            print(f"\nContract verification result: {contract_verification}")
            print(f"Event details: {event.args}")
        else:
            print("\nNo verification events found")
            contract_verification = False

        return contract_verification
    except Exception as e:
        print(f"\nError in verification step: {str(e)}")
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


# def sign_pdf_text(pdf_path, wa_id):
#     """
#     Signs the text content of a PDF file and saves the signature as JSON.

#     Args:
#         pdf_path (str): Path to the PDF file
#         wa_id (str): WhatsApp ID of the user

#     Returns:
#         tuple: (dict: Contains address, data, and signature, str: Path to signature file)
#     """
#     try:
#         # Extract text and create signature
#         extracted_text = extract_text_from_pdf(pdf_path)
#         private_key = os.getenv("PRIVATE_KEY")
#         data = {"content": extracted_text, "phone_number": wa_id}
#         signing_result = sign_object(private_key, data)

#         # Create signature filename based on PDF filename
#         pdf_filename = os.path.basename(pdf_path)
#         pdf_name = os.path.splitext(pdf_filename)[0]
#         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#         signature_filename = f"{pdf_name}_signature_{timestamp}.json"

#         # Get the directory of the PDF and create a signatures subdirectory
#         pdf_dir = os.path.dirname(pdf_path)
#         signatures_dir = os.path.join(pdf_dir, "signatures")
#         os.makedirs(signatures_dir, exist_ok=True)

#         # Full path for signature file
#         signature_path = os.path.join(signatures_dir, signature_filename)

#         # Save signature to JSON file
#         with open(signature_path, "w") as f:
#             json.dump(signing_result, f, indent=2)

#         return signing_result, signature_path

#     except Exception as e:
#         logging.error(f"Error in sign_pdf_text: {str(e)}")
#         raise


def sign_pdf_text(pdf_path, wa_id):
    try:
        w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))

        # Extract text from PDF
        extracted_text = extract_text_from_pdf(pdf_path)

        # Load contract
        contract_address = Web3.to_checksum_address(os.getenv("CONTRACT_ADDRESS"))
        print(f"Contract address: {contract_address}")
        with open(os.path.join(os.path.dirname(__file__), "abi.json"), "r") as f:
            abi = json.load(f)
        contract = w3.eth.contract(address=contract_address, abi=abi)

        private_key = os.getenv("PRIVATE_KEY")
        if not private_key.startswith("0x"):
            private_key = "0x" + private_key

        account = w3.eth.account.from_key(private_key)

        # Prepare data for signing
        document_text = extracted_text
        phone_number = wa_id

        # Create hash exactly as the contract does
        encoded_data = Web3.solidity_keccak(
            ["string", "string"], [document_text, phone_number]
        )

        # Convert to Ethereum signed message format
        message_to_sign = encode_defunct(encoded_data)
        print(f"Ethereum formatted message: {message_to_sign.body.hex()}")

        # Sign the message
        signed_message = w3.eth.account.sign_message(
            message_to_sign, private_key=private_key
        )

        # Store data
        # signing_result = {
        #     "address": account.address,
        #     "data": {"content": document_text, "phone_number": phone_number},
        #     "signature": signed_message.signature.hex(),
        # }
        signing_result = {
            "address": account.address,
            "data": {"phone_number": phone_number},
            "signature": signed_message.signature.hex(),
        }

        # Save to file
        pdf_filename = os.path.basename(pdf_path)
        pdf_name = os.path.splitext(pdf_filename)[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        signature_filename = f"{pdf_name}_signature_{timestamp}.json"

        pdf_dir = os.path.dirname(pdf_path)
        signatures_dir = os.path.join(pdf_dir, "signatures")
        os.makedirs(signatures_dir, exist_ok=True)
        signature_path = os.path.join(signatures_dir, signature_filename)

        with open(signature_path, "w") as f:
            json.dump(signing_result, f, indent=2)

        print(f"\n=== Signature saved to: {signature_path} ===")
        print(f"=== Signature Details ===")
        print(f"Signing Address: {signing_result['address']}")
        print(f"data: {signing_result['data']}")
        print(f"Signature: {signing_result['signature']}")

        return signing_result, signature_path

    except Exception as e:
        logging.error(f"Error in sign_pdf_text: {str(e)}")
        raise


# def verify_pdf_signature(signing_result):
#     """
#     Verifies a previously generated PDF signature.

#     Args:
#         signing_result (dict):
#             - address
#             - data
#                 - content
#                 - phone_number
#             - signature

#     Returns:
#         bool: True if signature is valid, False otherwise
#     """
#     return verify_object_signature(
#         address=signing_result["address"],
#         data=signing_result["data"],
#         signature=signing_result["signature"],
#     )


# Test code
# if __name__ == "__main__":
#     base_dir = os.path.dirname(
#         os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#     )
#     file_path = os.path.join(base_dir, "data", "airbnb-faq.pdf")

#     # Sign the PDF text
#     signature_data, signature_path = sign_pdf_text(file_path, wa_id="12139135416")

#     # Print the signature details (now accessing the tuple correctly)
#     print("\n=== Signature Details ===")
#     print("Signing Address:", signature_data["address"])
#     print("Phone Number:", signature_data["data"]["phone_number"])
#     print("Signature:", signature_data["signature"])
#     print("Signature File:", signature_path)

#     # Then verify the signature
#     # is_verified = verify_pdf_signature(signature_data)
#     is_verified = verify_object_signature_no_data(file_path, signature_data)
#     print(
#         "\nSignature Verification Result:", "✅ Valid" if is_verified else "❌ Invalid"
#     )
