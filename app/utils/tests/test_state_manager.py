import unittest
from state_manager import StateManager, UserState


class TestInitializeUser(unittest.TestCase):
    def setUp(self):
        # create a new instance of StateManager
        self.sm = StateManager()

    def test_initial_state(self):
        wa_id = "12139135416"

        # Before initializing the user, get_user_state should return None since the user is not defined
        self.assertIsNone(self.sm.get_user_state(wa_id))

        # Call initialize_user to set the initial state for the user
        self.sm.initialize_user(wa_id)

        # After initializing the user, the state should be set to UserState.INITIAL
        self.assertEqual(self.sm.get_user_state(wa_id), UserState.INITIAL)

        # The files dictionary should be empty after initialization
        self.assertEqual(self.sm.get_user_files(wa_id), {})

        # The verification status should be None after initialization
        self.assertIsNone(self.sm.get_verification_status(wa_id))

    def test_update_user_state(self):
        wa_id = "12139135416"

        # Initialize the user
        self.sm.initialize_user(wa_id)

        # Update the user state to PDF_RECEIVED
        self.sm.update_user_state(wa_id, UserState.PDF_RECEIVED)
        self.assertEqual(self.sm.get_user_state(wa_id), UserState.PDF_RECEIVED)

        # Update the user state to JSON_RECEIVED
        self.sm.update_user_state(wa_id, UserState.JSON_RECEIVED)
        self.assertEqual(self.sm.get_user_state(wa_id), UserState.JSON_RECEIVED)

        # Update the user state to VERIFICATION_COMPLETE
        self.sm.update_user_state(wa_id, UserState.VERIFICATION_COMPLETE)
        self.assertEqual(self.sm.get_user_state(wa_id), UserState.VERIFICATION_COMPLETE)

        # Update the user state to INITIAL
        self.sm.update_user_state(wa_id, UserState.INITIAL)
        self.assertEqual(self.sm.get_user_state(wa_id), UserState.INITIAL)

    def test_add_file(self):
        wa_id = "12139135416"

        # Initialize the user
        self.sm.initialize_user(wa_id)

        # Add a PDF file
        pdf_path = "/path/to/pdf_file.pdf"
        pdf_name = "pdf_file.pdf"
        self.sm.add_file(wa_id, "pdf", pdf_path, pdf_name)

        # The files dictionary should contain the PDF file details
        self.assertEqual(
            self.sm.get_user_files(wa_id), {"pdf_path": pdf_path, "pdf_name": pdf_name}
        )

        # The user state should be set to PDF_RECEIVED
        self.assertEqual(self.sm.get_user_state(wa_id), UserState.PDF_RECEIVED)

        # Add a JSON file
        json_path = "/path/to/json_file.json"
        json_name = "json_file.json"
        self.sm.add_file(wa_id, "json", json_path, json_name)

        # The files dictionary should contain both PDF and JSON file details
        self.assertEqual(
            self.sm.get_user_files(wa_id),
            {
                "pdf_path": pdf_path,
                "pdf_name": pdf_name,
                "json_path": json_path,
                "json_name": json_name,
            },
        )

        # The user state should be set to VERIFICATION_IN_PROGRESS
        self.assertEqual(
            self.sm.get_user_state(wa_id), UserState.VERIFICATION_IN_PROGRESS
        )

    def test_set_verification_status(self):
        wa_id = "12139135416"

        # Initialize the user
        self.sm.initialize_user(wa_id)

        # Set the verification status to True
        self.sm.set_verification_status(wa_id, True)

        # The verification status should be True
        self.assertTrue(self.sm.get_verification_status(wa_id))

        # The user state should be set to VERIFICATION_COMPLETE
        self.assertEqual(self.sm.get_user_state(wa_id), UserState.VERIFICATION_COMPLETE)

        # Set the verification status to False
        self.sm.set_verification_status(wa_id, False)

        # The verification status should be False
        self.assertFalse(self.sm.get_verification_status(wa_id))

        # The user state should remain as VERIFICATION_COMPLETE
        self.assertEqual(self.sm.get_user_state(wa_id), UserState.VERIFICATION_COMPLETE)

    def test_non_existent_user(self):
        wa_id = "12139135416"

        # Attempt to update the state for a non-existent user
        self.sm.update_user_state(wa_id, UserState.PDF_RECEIVED)

        # The user state should still be None
        self.assertIsNone(self.sm.get_user_state(wa_id))

        # Attempt to add a file for a non-existent user
        self.sm.add_file(wa_id, "pdf", "/path/to/pdf_file.pdf", "pdf_file.pdf")

        # The files dictionary should still be empty
        self.assertEqual(self.sm.get_user_files(wa_id), {})

        # Attempt to set the verification status for a non-existent user
        self.sm.set_verification_status(wa_id, True)

        # The verification status should still be None
        self.assertIsNone(self.sm.get_verification_status(wa_id))


if __name__ == "__main__":
    unittest.main()
