from enum import Enum
import logging
import os
from typing import Dict, Optional


class UserState(Enum):
    """
    Enum to track the state of each user in the verification flow
    """

    INITIAL = "initial"  # Just started interaction
    AWAITING_FILES = "awaiting_files"  # Needs to upload both files
    PDF_RECEIVED = "pdf_received"  # Has uploaded PDF, waiting for JSON
    JSON_RECEIVED = "json_received"  # Has uploaded JSON, waiting for PDF
    VERIFICATION_IN_PROGRESS = "verifying"  # Both files received, verification ongoing
    VERIFICATION_COMPLETE = "complete"  # Verification finished
    ERROR = "error"  # Error state


class StateManager:
    """
    Manages user states and session data for the WhatsApp bot
    """

    def __init__(self):
        print("Initializing StateManager")
        self._user_states: Dict[str, dict] = {}  # Regular dict instead of defaultdict
        logging.info("StateManager initialized")

    def initialize_user(self, wa_id: str) -> None:
        """
        Initialize a new user's state or reset if in ERROR state
        """
        print(f"\n=== Initializing state for user {wa_id} ===")
        current_state = None

        if wa_id in self._user_states:
            current_state = self._user_states[wa_id].get("state")
            print(f"User exists with state: {current_state}")

            # Only reset if in ERROR state, keep VERIFICATION_COMPLETE
            if (
                current_state == UserState.ERROR
            ):  # Remove VERIFICATION_COMPLETE from this check
                self.clear_user_state(wa_id)
                print(f"Reset state from error state: {current_state}")
                return

            # For other states, show current files and return
            current_files = self._user_states[wa_id].get("files", {})
            print(f"Current files: {current_files}")
            logging.info(
                f"User {wa_id} already initialized with state: {current_state}"
            )
            return

        # Initialize new user
        self._user_states[wa_id] = {
            "state": UserState.INITIAL,
            "files": {},
            "verification_status": None,
        }
        print(f"✅ New user initialized with state: {UserState.INITIAL}")
        logging.info(f"New user {wa_id} initialized with state: {UserState.INITIAL}")

    def get_user_state(self, wa_id: str) -> Optional[UserState]:
        """
        Get the current state of a user
        """
        print(f"\n=== Getting state for user {wa_id} ===")
        state = self._user_states.get(wa_id, {}).get("state")
        print(f"Current state: {state}")
        logging.debug(f"Retrieved state for user {wa_id}: {state}")
        return state

    def update_user_state(self, wa_id: str, new_state: UserState) -> None:
        """
        Update a user's state
        """
        print(f"\n=== Updating state for user {wa_id} ===")
        if wa_id in self._user_states:
            old_state = self._user_states[wa_id]["state"]
            self._user_states[wa_id]["state"] = new_state
            print(f"State transition: {old_state} -> {new_state}")
            logging.info(f"Updated state for {wa_id}: {old_state} -> {new_state}")
        else:
            print(f"❌ Error: Attempted to update state for non-existent user {wa_id}")
            logging.error(f"Attempted to update state for non-existent user {wa_id}")

    def add_file(
        self, wa_id: str, file_type: str, file_path: str, file_name: str
    ) -> None:
        """
        Add a file to a user's state with proper validation and cleanup
        """
        print(f"\n=== Adding {file_type} file for user {wa_id} ===")
        if wa_id not in self._user_states:
            print(f"❌ Error: User {wa_id} not initialized")
            return

        # Verify the new file exists
        if not os.path.exists(file_path):
            print(f"❌ Error: File {file_path} does not exist")
            return

        # Log current state before modification
        current_files = self._user_states[wa_id]["files"].copy()
        print(f"Current files before adding: {current_files}")

        # Clean up old file of same type if it exists
        old_path = current_files.get(f"{file_type}_path")
        if old_path and os.path.exists(old_path):
            try:
                os.remove(old_path)
                print(f"Removed old {file_type} file: {old_path}")
            except Exception as e:
                print(f"❌ Error removing old file: {str(e)}")
                logging.error(f"Error removing old file {old_path}: {str(e)}")

        # Update state with new file
        self._user_states[wa_id]["files"][f"{file_type}_path"] = file_path
        self._user_states[wa_id]["files"][f"{file_type}_name"] = file_name

        # Get updated files and verify existence
        files = self._user_states[wa_id]["files"]
        print(f"Updated files: {files}")

        # Update state based on valid files
        pdf_exists = os.path.exists(files.get("pdf_path", ""))
        json_exists = os.path.exists(files.get("json_path", ""))

        if pdf_exists and json_exists:
            print(
                "Both files present and valid, transitioning to VERIFICATION_IN_PROGRESS"
            )
            self.update_user_state(wa_id, UserState.VERIFICATION_IN_PROGRESS)
        elif pdf_exists:
            print("Valid PDF file present, transitioning to PDF_RECEIVED")
            self.update_user_state(wa_id, UserState.PDF_RECEIVED)
        elif json_exists:
            print("Valid JSON file present, transitioning to JSON_RECEIVED")
            self.update_user_state(wa_id, UserState.JSON_RECEIVED)
        else:
            print("❌ No valid files present, transitioning to AWAITING_FILES")
            self.update_user_state(wa_id, UserState.AWAITING_FILES)

    def verify_files_exist(self, wa_id: str) -> bool:
        """
        Verify that both required files exist
        """
        print(f"\n=== Verifying files for user {wa_id} ===")
        files = self.get_user_files(wa_id)

        pdf_exists = os.path.exists(files.get("pdf_path", ""))
        json_exists = os.path.exists(files.get("json_path", ""))

        if not (pdf_exists and json_exists):
            print("❌ One or more files missing")
            return False

        print("✅ All files present")
        return True

    def get_user_files(self, wa_id: str) -> dict:
        """
        Get all files associated with a user
        """
        print(f"\n=== Getting files for user {wa_id} ===")
        files = self._user_states.get(wa_id, {}).get("files", {})
        print(f"Retrieved files: {files}")
        logging.debug(f"Retrieved files for user {wa_id}: {files}")
        return files

    def set_verification_status(self, wa_id: str, status: bool) -> None:
        """
        Set the verification status for a user
        """
        print(f"\n=== Setting verification status for user {wa_id} ===")
        if wa_id in self._user_states:
            self._user_states[wa_id]["verification_status"] = status
            print(f"Verification status set to: {status}")
            self.update_user_state(wa_id, UserState.VERIFICATION_COMPLETE)
            logging.info(f"Set verification status for {wa_id} to {status}")
        else:
            print(
                f"❌ Error: Attempted to set verification status for non-existent user {wa_id}"
            )
            logging.error(
                f"Attempted to set verification status for non-existent user {wa_id}"
            )

    def clear_user_state(self, wa_id: str) -> None:
        """
        Clear a user's state and clean up files
        """
        print(f"\n=== Clearing state for user {wa_id} ===")
        if wa_id in self._user_states:
            # Log current state before clearing
            old_state = self._user_states[wa_id].get("state", "None")
            old_files = self._user_states[wa_id].get("files", {})

            # Clean up physical files
            for key, file_path in old_files.items():
                if key.endswith("_path") and isinstance(file_path, str):
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            print(f"Removed file: {file_path}")
                    except Exception as e:
                        print(f"❌ Error removing {file_path}: {str(e)}")
                        logging.error(f"Error removing file {file_path}: {str(e)}")

            # Reset state
            self._user_states[wa_id] = {
                "state": UserState.INITIAL,
                "files": {},
                "verification_status": None,
            }

            print(f"Cleared state (was: {old_state})")
            print(f"Cleared files (were: {old_files})")
            logging.info(
                f"Cleared state for user {wa_id} (previous state: {old_state})"
            )
        else:
            print(f"❌ Error: Attempted to clear state for non-existent user {wa_id}")
            logging.error(f"Attempted to clear state for non-existent user {wa_id}")

    def get_verification_status(self, wa_id: str) -> Optional[bool]:
        """
        Get the verification status for a user
        """
        print(f"\n=== Getting verification status for user {wa_id} ===")
        status = self._user_states.get(wa_id, {}).get("verification_status")
        print(f"Verification status: {status}")
        logging.debug(f"Retrieved verification status for user {wa_id}: {status}")
        return status


# Create a global instance of StateManager
state_manager = StateManager()
