import os
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock, mock_open
from flask import Flask


from app.utils.document_utils import (
    handle_document_message,
    verify_documents,
    save_document,
    cleanup_user_files,
)
from app.utils.state_manager import state_manager


class TestDocumentHandler(unittest.TestCase):
    def setUp(self):
        # Use a consistent WhatsApp id and ensure a clean state each time.
        self.wa_id = "12139135416"
        state_manager.clear_user_state(self.wa_id)
        self.app = Flask(__name__)
        self.app.config["UPLOAD_FOLDER"] = "/tmp/uploads"
        self.app.config["ACCESS_TOKEN"] = "faketoken"
        self.app.config["VERSION"] = "v11.0"

    @patch("app.utils.document_utils.send_prompt_message")
    def test_handle_document_message_no_document(self, mock_send_prompt):
        """
        When the incoming message has no "document" key,
        the function should delegate to send_prompt_message.
        """
        message = {}  # no "document"
        mock_send_prompt.return_value = "sent prompt"

        result = handle_document_message(message, self.wa_id, "dummy_name")
        mock_send_prompt.assert_called_once_with(self.wa_id)
        self.assertEqual(result, "sent prompt")

    @patch("app.utils.document_utils.send_error_message")
    def test_handle_document_message_invalid_mime(self, mock_send_error):
        """
        If the document has an unsupported MIME type and filename,
        the function should return an error message.
        """
        message = {
            "document": {
                "mime_type": "image/png",  # Not a PDF and filename doesn't end with .json
                "filename": "pic.png",
                "id": "doc1",
            }
        }
        mock_send_error.return_value = "sent error"
        result = handle_document_message(message, self.wa_id, "pic.png")
        mock_send_error.assert_called_once_with(
            self.wa_id, "Please send either a PDF file or the signature.json file."
        )
        self.assertEqual(result, "sent error")

    @patch("app.utils.document_utils.verify_documents")
    @patch("app.utils.document_utils.send_json_request_message")
    @patch("app.utils.document_utils.save_document")
    def test_handle_document_message_pdf(
        self, mock_save_doc, mock_send_json, mock_verify_docs
    ):
        """
        For a valid PDF document:
          • save_document should be called,
          • state_manager.add_file will update the user state to PDF_RECEIVED,
          • and if verification is not yet triggered, the assistant sends a prompt for JSON.
        """
        message = {
            "document": {
                "mime_type": "application/pdf",
                "filename": "document.pdf",
                "id": "pdf1",
            }
        }
        fake_path = "/tmp/fake_document.pdf"
        mock_save_doc.return_value = fake_path
        mock_send_json.return_value = "sent json request"

        # Call the function.
        result = handle_document_message(message, self.wa_id, "document.pdf")
        mock_save_doc.assert_called_once_with(message["document"], self.wa_id)
        # Since only the PDF is added, the state is not yet VERIFICATION_IN_PROGRESS.
        mock_send_json.assert_called_once_with(self.wa_id, "document.pdf")
        self.assertEqual(result, "sent json request")

    @patch("app.utils.document_utils.verify_documents")
    @patch("app.utils.document_utils.send_pdf_request_message")
    @patch("app.utils.document_utils.save_document")
    def test_handle_document_message_json(
        self, mock_save_doc, mock_send_pdf, mock_verify_docs
    ):
        """
        For a valid JSON document:
          • save_document should be called,
          • state_manager.add_file will update the state to JSON_RECEIVED,
          • and then the assistant prompts for the PDF file.
        """
        message = {
            "document": {
                "mime_type": "application/json",
                "filename": "signature.json",
                "id": "json1",
            }
        }
        fake_path = "/tmp/fake_signature.json"
        mock_save_doc.return_value = fake_path
        mock_send_pdf.return_value = "sent pdf request"

        result = handle_document_message(message, self.wa_id, "signature.json")
        mock_save_doc.assert_called_once_with(message["document"], self.wa_id)
        mock_send_pdf.assert_called_once_with(self.wa_id, "signature.json")
        self.assertEqual(result, "sent pdf request")

    @patch("app.utils.document_utils.verify_object_signature")
    @patch("app.utils.document_utils.send_message")
    @patch("app.utils.document_utils.get_text_message_input")
    def test_verify_documents_success(
        self, mock_get_text, mock_send_msg, mock_verify_sig
    ):
        """
        Test verification when both files are present and verification succeeds.
        This test creates temporary files to simulate the PDF and JSON.
        """
        # Create temporary files for testing.
        temp_dir = tempfile.gettempdir()
        pdf_path = os.path.join(temp_dir, "test.pdf")
        json_path = os.path.join(temp_dir, "test.json")
        with open(pdf_path, "wb") as f:
            f.write(b"dummy pdf content")
        signature_data = {
            "address": "0x123",
            "data": "dummy data",
            "signature": "dummy_signature",
        }
        with open(json_path, "w") as f:
            json.dump(signature_data, f)

        # Initialize the user and set file paths.
        state_manager.initialize_user(self.wa_id)
        state_manager._user_states[self.wa_id]["files"] = {
            "pdf_path": pdf_path,
            "pdf_name": "test.pdf",
            "json_path": json_path,
            "json_name": "signature.json",
        }

        mock_verify_sig.return_value = True
        mock_get_text.return_value = "fake message input"
        mock_send_msg.return_value = "sent verification message"

        result = verify_documents(self.wa_id)
        self.assertEqual(result, "sent verification message")

        # Clean up temporary files.
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        if os.path.exists(json_path):
            os.remove(json_path)

    @patch("app.utils.document_utils.requests.get")
    @patch("app.utils.document_utils.os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    def test_save_document_success(
        self, mock_open_file, mock_makedirs, mock_requests_get
    ):
        """
        Test that save_document correctly creates directories,
        retrieves the media URL, downloads content, and writes it to a file.
        """
        document = {"id": "123", "filename": "sample.pdf"}

        # Set up fake responses
        fake_media_url = "http://example.com/fake.pdf"
        fake_response_url = MagicMock()
        fake_response_url.status_code = 200
        fake_response_url.json.return_value = {"url": fake_media_url}
        fake_response_download = MagicMock()
        fake_response_download.status_code = 200
        fake_response_download.content = b"fake pdf content"
        mock_requests_get.side_effect = [fake_response_url, fake_response_download]

        # Push an application context
        with self.app.app_context():
            result = save_document(document, "test_wa_id")

        expected_filename = "/tmp/uploads/123_sample.pdf"

        # Assertions
        self.assertEqual(result, expected_filename)
        mock_makedirs.assert_called_once_with("/tmp/uploads", exist_ok=True)

        # Verify that the file was opened and written to
        mock_open_file.assert_called_with(expected_filename, "wb")
        handle = mock_open_file()
        handle.write.assert_called_once_with(b"fake pdf content")


if __name__ == "__main__":
    unittest.main()
