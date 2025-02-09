from collections import defaultdict


class StateManager:
    """
    Manages user states and session data for the WhatsApp bot.
    """

    def __init__(self):
        self._user_states = defaultdict(dict)

    def set_state(self, user_id, key, value):
        """Sets a specific state for a given user."""
        self._user_states[user_id][key] = value

    def get_state(self, user_id, key, default=None):
        """Retrieves a state for a given user; returns 'default' if the key is not found."""
        return self._user_states[user_id].get(key, default)


# Create an instance of StateManager
state_manager = StateManager()

# Example user id
user_id = "user123"

# Before setting any state, accessing the user key auto-creates an empty dict
print(state_manager._user_states[user_id])
# Output: {} since no state has been set yet

# Set some state properties for the user
state_manager.set_state(user_id, "last_message", "Hello, World!")
state_manager.set_state(user_id, "step", 1)

# Retrieve the state for the user
print("Last message:", state_manager.get_state(user_id, "last_message"))
# Output: Hello, World!
print("Step:", state_manager.get_state(user_id, "step"))
# Output: 1

# If you try to access a state key that doesn't exist, it returns the default value (None in this case)
print("Non-existent key:", state_manager.get_state(user_id, "non_existent_key"))
# Output: None
