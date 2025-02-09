from enum import Enum
from collections import defaultdict
import logging
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
        self._user_states: Dict[str, dict] = defaultdict(dict)

    def initialize_user(self, wa_id: str) -> None:
        """
        Initialize a new user's state
        """
        if wa_id not in self._user_states:
            self._user_states[wa_id] = {
                "state": UserState.INITIAL,
                "files": {},
                "verification_status": None,
            }
            logging.info(f"Initialized new user state for {wa_id}")

    def get_user_state(self, wa_id: str) -> Optional[UserState]:
        """
        Get the current state of a user
        """
        return self._user_states.get(wa_id, {}).get("state")

    def update_user_state(self, wa_id: str, new_state: UserState) -> None:
        """
        Update a user's state
        """
        if wa_id in self._user_states:
            self._user_states[wa_id]["state"] = new_state
            logging.info(f"Updated state for {wa_id} to {new_state.value}")
        else:
            logging.error(f"Attempted to update state for non-existent user {wa_id}")

    def add_file(
        self, wa_id: str, file_type: str, file_path: str, file_name: str
    ) -> None:
        """
        Add a file to a user's state
        """
        if wa_id in self._user_states:
            self._user_states[wa_id]["files"][f"{file_type}_path"] = file_path
            self._user_states[wa_id]["files"][f"{file_type}_name"] = file_name

            # Update state based on files present
            files = self._user_states[wa_id]["files"]
            if "pdf_path" in files and "json_path" in files:
                self.update_user_state(wa_id, UserState.VERIFICATION_IN_PROGRESS)
            elif "pdf_path" in files:
                self.update_user_state(wa_id, UserState.PDF_RECEIVED)
            elif "json_path" in files:
                self.update_user_state(wa_id, UserState.JSON_RECEIVED)

    def get_user_files(self, wa_id: str) -> dict:
        """
        Get all files associated with a user
        """
        return self._user_states.get(wa_id, {}).get("files", {})

    def set_verification_status(self, wa_id: str, status: bool) -> None:
        """
        Set the verification status for a user
        """
        if wa_id in self._user_states:
            self._user_states[wa_id]["verification_status"] = status
            self.update_user_state(wa_id, UserState.VERIFICATION_COMPLETE)

    def clear_user_state(self, wa_id: str) -> None:
        """
        Clear a user's state (e.g., after verification or error)
        """
        if wa_id in self._user_states:
            self._user_states[wa_id] = {
                "state": UserState.INITIAL,
                "files": {},
                "verification_status": None,
            }
            logging.info(f"Cleared state for user {wa_id}")

    def get_verification_status(self, wa_id: str) -> Optional[bool]:
        """
        Get the verification status for a user
        """
        return self._user_states.get(wa_id, {}).get("verification_status")


# Create a global instance of StateManager
state_manager = StateManager()
