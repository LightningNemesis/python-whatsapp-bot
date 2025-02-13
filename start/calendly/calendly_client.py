import requests
from datetime import datetime, timezone, timedelta
import json
import os
from dotenv import load_dotenv
from typing import Dict, List, Optional, Tuple


class CalendlyClient:
    def __init__(self, token: str):
        """
        Initialize the Calendly client with an API token.

        Args:
            token (str): Your Calendly Personal Access Token
        """
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def get_user(self) -> Dict:
        """
        Get current user information.

        Returns:
            Dict: User information
        """
        url = "https://api.calendly.com/users/me"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_event_types(self) -> List[Dict]:
        """
        Get a list of event types and their UUIDs.

        Returns:
            List[Dict]: List of event types with their details
        """
        user_data = self.get_user()
        user_uri = user_data["resource"]["uri"]

        url = "https://api.calendly.com/event_types"
        params = {"user": user_uri, "active": True}

        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()

        event_types = []
        for event_type in response.json().get("collection", []):
            event_types.append(
                {
                    "name": event_type.get("name"),
                    "uuid": event_type.get("uri").split("/")[-1],
                    "duration": event_type.get("duration"),
                    "description": event_type.get("description"),
                    "scheduling_url": event_type.get("scheduling_url"),  # Add this line
                }
            )

        return event_types

    def get_available_slots(
        self,
        event_type_uuid: str,
        start_time: datetime,
        end_time: datetime,
        verbose: bool = False,  # Add this parameter
    ) -> List[Dict]:
        """
        Retrieve available time slots for an event type.

        Args:
            event_type_uuid (str): UUID of the event type
            start_time (datetime): Start of the range to check availability
            end_time (datetime): End of the range to check availability
            verbose (bool): Whether to print debug information

        Returns:
            List[Dict]: Available time slots
        """
        url = "https://api.calendly.com/event_type_available_times"

        # Format dates according to the API requirements
        formatted_start = start_time.strftime("%Y-%m-%d") + "T24:00:00.000000Z"
        formatted_end = end_time.strftime("%Y-%m-%d") + "T24:00:00.000000Z"

        if verbose:  # Only print if verbose is True
            print(f"Formatted Start: {formatted_start}")
            print(f"Formatted End: {formatted_end}")

        querystring = {
            "event_type": f"https://api.calendly.com/event_types/{event_type_uuid}",
            "start_time": formatted_start,
            "end_time": formatted_end,
        }

        if verbose:  # Only print if verbose is True
            print("\nAPI Request Details:")
            print(f"URL: {url}")
            print("Query Parameters:")
            for key, value in querystring.items():
                print(f"  {key}: {value}")

        try:
            response = requests.request(
                "GET", url, headers=self.headers, params=querystring
            )
            if verbose:  # Only print if verbose is True
                print(f"\nResponse Status: {response.status_code}")
                print(f"Response Body: {response.text[:1000]}")

            response.raise_for_status()
            result = response.json()
            return result.get("collection", [])

        except requests.exceptions.RequestException as e:
            if verbose:  # Only print if verbose is True
                print(f"\nError Details:")
                print(f"Error Type: {type(e).__name__}")
                print(f"Error Message: {str(e)}")
                if hasattr(e.response, "text"):
                    print(f"Error Response: {e.response.text}")
            raise

    def create_scheduling_link(
        self, event_type_uuid: str, verbose: bool = False
    ) -> Dict:
        """
        Create a single-use scheduling link for an event type.

        Args:
            event_type_uuid (str): UUID of the event type
            verbose (bool): Whether to print debug information

        Returns:
            Dict: Scheduling link details including the booking URL
        """
        url = "https://api.calendly.com/scheduling_links"

        payload = {
            "max_event_count": 1,
            "owner": f"https://api.calendly.com/event_types/{event_type_uuid}",
            "owner_type": "EventType",
        }

        if verbose:
            print("\nCreating scheduling link...")
            print(f"Event Type: {event_type_uuid}")

        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

    def create_webhook(
        self, callback_url: str, events: List[str], scope: str = "user"
    ) -> Dict:
        """
        Create a webhook subscription.

        Args:
            callback_url (str): The URL where you want to receive POST requests for events
            events (List[str]): List of events to subscribe to (e.g., ["invitee.created"])
            scope (str): Scope of the webhook ("user" or "organization")

        Returns:
            Dict: Webhook subscription details
        """
        url = "https://api.calendly.com/webhook_subscriptions"

        # Get user and organization info
        user_data = self.get_user()
        user_uri = user_data["resource"]["uri"]
        org_uri = user_data["resource"]["current_organization"]

        payload = {
            "url": callback_url,
            "events": events,
            "organization": org_uri,
            "scope": scope,
        }

        if scope == "user":
            payload["user"] = user_uri

        print("\nCreating webhook subscription...")
        print(f"Callback URL: {callback_url}")
        print(f"Events: {events}")
        print(f"Scope: {scope}")

        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

    def list_webhooks(self, scope: str = "user") -> List[Dict]:
        """
        Get a list of webhook subscriptions.

        Args:
            scope (str): Scope to filter webhooks ("user" or "organization")

        Returns:
            List[Dict]: List of webhook subscriptions
        """
        url = "https://api.calendly.com/webhook_subscriptions"

        # Get user and organization info
        user_data = self.get_user()
        org_uri = user_data["resource"]["current_organization"]
        user_uri = user_data["resource"]["uri"]

        params = {"organization": org_uri, "scope": scope}

        if scope == "user":
            params["user"] = user_uri

        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()["collection"]

    def delete_webhook(self, webhook_uuid: str) -> None:
        """
        Delete a webhook subscription.

        Args:
            webhook_uuid (str): UUID of the webhook to delete
        """
        url = f"https://api.calendly.com/webhook_subscriptions/{webhook_uuid}"

        response = requests.delete(url, headers=self.headers)
        response.raise_for_status()


def format_slots_for_whatsapp(slots: List[Dict]) -> str:
    """
    Format available slots into a WhatsApp-friendly message.

    Args:
        slots (List[Dict]): List of available time slots

    Returns:
        str: Formatted message
    """
    if not slots:
        return "No available slots found for the selected time range."

    message = "Available slots:\n\n"
    for i, slot in enumerate(slots, 1):
        start = datetime.fromisoformat(slot["start_time"].replace("Z", "+00:00"))
        message += f"{i}. {start.strftime('%B %d, %Y at %I:%M %p UTC')}\n"

    message += "\nReply with the number of your preferred slot to book."
    return message


def main():
    # Load environment variables from .env file
    load_dotenv()

    # Get token from environment variable
    token = os.getenv("CALENDLY_TOKEN")
    if not token:
        raise ValueError("Please set CALENDLY_TOKEN environment variable")

    client = CalendlyClient(token)

    try:
        # 1. Get event types
        print("Fetching event types...")
        event_types = client.get_event_types()
        print("\nAvailable event types:")
        for i, event_type in enumerate(event_types, 1):
            print(
                f"{i}. {event_type['name']} (Duration: {event_type['duration']} minutes)"
            )
            print(f"   UUID: {event_type['uuid']}")

        # Ask user which event type to use
        while True:
            try:
                choice = int(
                    input(
                        "\nEnter the number of the event type you want to use (1, 2, etc.): "
                    )
                )
                if 1 <= choice <= len(event_types):
                    selected_event_type = event_types[choice - 1]
                    break
                print("Invalid choice. Please select a valid number.")
            except ValueError:
                print("Please enter a valid number.")

        print(f"\nUsing event type: {selected_event_type['name']}")

        # 2. Get available slots for the next 7 days
        print("\nSetting up time range...")
        now = datetime.now(timezone.utc)
        end_time = now + timedelta(days=7)

        print(f"\nTime range:")
        print(f"Start: {now.strftime('%Y-%m-%d')}")
        print(f"End: {end_time.strftime('%Y-%m-%dT%H:%M:%S.000000Z')}")

        print(f"\nEvent Type UUID: {selected_event_type['uuid']}")
        print(
            f"Full Event Type URL: https://api.calendly.com/event_types/{selected_event_type['uuid']}"
        )

        print("\nFetching available slots...")
        slots = client.get_available_slots(selected_event_type["uuid"], now, end_time)

        # 3. Format and display available slots
        whatsapp_message = format_slots_for_whatsapp(slots)
        print("\nFormatted message for WhatsApp:")
        print(whatsapp_message)

        # 4. Create scheduling link
        print("\nCreating scheduling link...")
        scheduling_link = client.create_scheduling_link(selected_event_type["uuid"])

        # 5. Display booking URL
        booking_url = scheduling_link["resource"]["booking_url"]
        print("\nScheduling link created successfully!")
        print(f"Booking URL: {booking_url}")
        print(
            "\nUse this URL to schedule your meeting. The link can be used once to book a time slot."
        )

    except requests.exceptions.RequestException as e:
        print("\nAPI Error Details:")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        if hasattr(e, "response") and e.response is not None:
            print(f"Response Status Code: {e.response.status_code}")
            print(f"Response Body: {e.response.text}")
    except Exception as e:
        print(f"\nUnexpected error: {e}")


def setup_webhook_example():
    """Example of setting up a webhook for meeting notifications."""
    # Load environment variables
    load_dotenv()
    token = os.getenv("CALENDLY_TOKEN")
    if not token:
        raise ValueError("Please set CALENDLY_TOKEN environment variable")

    client = CalendlyClient(token)

    try:
        # Create a webhook for meeting notifications
        webhook_url = "https://your-chatbot-endpoint.com/calendly-webhook"  # Replace with your endpoint
        events = ["invitee.created", "invitee.canceled"]  # Events you want to monitor

        # Create the webhook
        webhook = client.create_webhook(
            callback_url=webhook_url,
            events=events,
            scope="user",  # or "organization" if you want org-wide webhooks
        )

        print("\nWebhook created successfully!")
        print(f"Webhook URI: {webhook['resource']['uri']}")
        print(f"State: {webhook['resource']['state']}")
        print(f"Events: {webhook['resource']['events']}")

        # List existing webhooks
        print("\nExisting webhooks:")
        webhooks = client.list_webhooks()
        for hook in webhooks:
            print(f"- {hook['uri']} ({hook['state']})")

    except requests.exceptions.RequestException as e:
        print(f"\nError: {str(e)}")
        if hasattr(e, "response"):
            print(f"Response: {e.response.text}")


if __name__ == "__main__":
    # Choose which example to run
    main()  # Original scheduling example
    # setup_webhook_example()  # Webhook setup example
