# app/utils/calendly/calendly_client.py
import requests
from datetime import datetime, timezone, timedelta
import json
import os
from dotenv import load_dotenv
from typing import Dict, List, Optional, Tuple
import logging


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
        try:
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
                        "scheduling_url": event_type.get("scheduling_url"),
                    }
                )

            return event_types
        except Exception as e:
            logging.error(f"Error getting event types: {e}")
            return []

    def get_available_slots(
        self,
        event_type_uuid: str,
        start_time: datetime,
        end_time: datetime,
        verbose: bool = False,
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

        # Format dates in ISO format
        formatted_start = start_time.isoformat()
        formatted_end = end_time.isoformat()

        if verbose:
            logging.debug(f"Formatted Start: {formatted_start}")
            logging.debug(f"Formatted End: {formatted_end}")

        querystring = {
            "event_type": f"https://api.calendly.com/event_types/{event_type_uuid}",
            "start_time": formatted_start,
            "end_time": formatted_end,
        }

        if verbose:
            logging.debug(f"Request details: {querystring}")

        try:
            response = requests.get(url, headers=self.headers, params=querystring)
            if verbose:
                logging.debug(f"Response Status: {response.status_code}")
                logging.debug(f"Response Body: {response.text[:1000]}")

            response.raise_for_status()
            result = response.json()
            return result.get("collection", [])

        except requests.exceptions.RequestException as e:
            logging.error(f"Error getting available slots: {e}")
            if verbose and hasattr(e.response, "text"):
                logging.error(f"Error Response: {e.response.text}")
            raise

    # app/services/calendly_service.py

    def create_scheduling_link(
        self,
        event_type_uuid: str,
        tracking: Dict = None,
        start_time: Optional[str] = None,
    ) -> Dict:
        """
        Create a single-use scheduling link for an event type.

        Args:
            event_type_uuid (str): UUID of the event type
            tracking (Dict, optional): Tracking parameters
            start_time (str, optional): Specific start time in ISO format

        Returns:
            Dict: Scheduling link details including the booking URL
        """
        try:
            url = "https://api.calendly.com/scheduling_links"
            print(f"\nCreating scheduling link...")
            print(f"Event Type UUID: {event_type_uuid}")

            payload = {
                "max_event_count": 1,
                "owner": f"https://api.calendly.com/event_types/{event_type_uuid}",
                "owner_type": "EventType",
            }

            if tracking:
                payload["tracking"] = tracking
                print(f"Added tracking: {tracking}")

            if start_time:
                payload["booking_options"] = {"start_time": start_time}
                print(f"Added start time: {start_time}")

            print(f"Request payload: {json.dumps(payload, indent=2)}")
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)}")
            return result

        except Exception as e:
            logging.error(f"Error creating scheduling link: {e}", exc_info=True)
            print(f"Error creating scheduling link: {str(e)}")
            return None

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
        try:
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

            logging.info(f"Creating webhook subscription: {payload}")
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()

        except Exception as e:
            logging.error(f"Error creating webhook: {e}")
            raise

    def list_webhooks(self, scope: str = "user") -> List[Dict]:
        """
        Get a list of webhook subscriptions.

        Args:
            scope (str): Scope to filter webhooks ("user" or "organization")

        Returns:
            List[Dict]: List of webhook subscriptions
        """
        try:
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

        except Exception as e:
            logging.error(f"Error listing webhooks: {e}")
            raise

    def delete_webhook(self, webhook_uuid: str) -> None:
        """
        Delete a webhook subscription.

        Args:
            webhook_uuid (str): UUID of the webhook to delete
        """
        try:
            url = f"https://api.calendly.com/webhook_subscriptions/{webhook_uuid}"
            response = requests.delete(url, headers=self.headers)
            response.raise_for_status()
            logging.info(f"Successfully deleted webhook: {webhook_uuid}")

        except Exception as e:
            logging.error(f"Error deleting webhook: {e}")
            raise
