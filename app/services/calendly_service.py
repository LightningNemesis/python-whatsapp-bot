# app/services/calendly_service.py
from app.utils.calendly.calendly_client import CalendlyClient
from openai import OpenAI
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional
import re
import json
from flask import current_app


class CalendlyAssistantService:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.calendly_client = CalendlyClient(os.getenv("CALENDLY_TOKEN"))

        self.system_message = """You are a scheduling assistant integrated with WhatsApp. 
        Help users schedule meetings through Calendly.
        
        Keep responses concise and WhatsApp-friendly using emojis and clear formatting.
        
        You can:
        - Show available event types
        - Check available time slots for specific dates
        - Create scheduling links for specific times
        - Process meeting notifications
        
        Example responses:
        "📅 Available Meeting Types:
        1. Quick Chat (15 min)
        2. Product Demo (30 min)
        3. Consultation (60 min)"

        "⏰ Available slots for tomorrow:
        • 9:00 AM
        • 2:30 PM
        • 4:00 PM"
        
        For non-scheduling questions, respond with:
        "I can only help with scheduling meetings. Would you like to see available meeting types?"
        """

    def _parse_date_time(self, message: str) -> tuple[datetime, str]:
        """Parse date and time from message"""
        target_date = datetime.now(timezone.utc)
        time_str = ""

        message = message.lower()

        # Parse date
        if "tomorrow" in message:
            target_date += timedelta(days=1)
        elif "today" in message:
            pass
        else:
            days = {
                "monday": 0,
                "tuesday": 1,
                "wednesday": 2,
                "thursday": 3,
                "friday": 4,
                "saturday": 5,
                "sunday": 6,
            }
            for day, offset in days.items():
                if day in message:
                    current_day = target_date.weekday()
                    days_ahead = (offset - current_day) % 7
                    if days_ahead == 0:
                        days_ahead = 7
                    target_date += timedelta(days=days_ahead)
                    break

        # Parse time
        time_pattern = r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b"
        time_match = re.search(time_pattern, message)
        if time_match:
            time_str = time_match.group()

        return target_date, time_str

    async def process_query(self, message: str, wa_id: str) -> str:
        """Process a scheduling-related query"""
        try:
            message_lower = message.lower()
            logging.info(
                f"Processing scheduling query: {message_lower} for wa_id: {wa_id}"
            )

            # Show available event types
            if any(
                word in message_lower
                for word in ["show", "list", "available", "types", "meetings"]
            ):
                try:
                    event_types = self.calendly_client.get_event_types()
                    if not event_types:
                        return "No meeting types are currently available."

                    response = "📅 Available Meeting Types:\n\n"
                    for i, event_type in enumerate(event_types, 1):
                        scheduling_link = self.create_scheduling_link(
                            event_type["uuid"],
                            wa_id,
                            booking_mapper=current_app.config[
                                "booking_mapper"
                            ],  # Add this
                        )
                        description = event_type.get(
                            "description", "No description available"
                        )

                        response += (
                            f"{i}. {event_type['name']}\n"
                            f"⏰ Duration: {event_type['duration']} min\n"
                            f"📝 {description}\n"
                            f"🔗 {scheduling_link}\n\n"
                        )

                    response += (
                        "Click any link above to schedule a meeting!\n\n"
                        "You can also:\n"
                        "• Check availability: 'Show available slots for tomorrow'\n"
                        "• Book specific time: 'Book meeting at 2pm tomorrow'"
                    )
                    return response

                except Exception as e:
                    logging.error(f"Error getting event types: {e}")
                    return "Sorry, I couldn't retrieve the meeting types. Please try again."

            # Check availability for specific date
            elif any(
                word in message_lower
                for word in ["slots", "times", "availability", "available"]
            ):
                try:
                    target_date, _ = self._parse_date_time(message_lower)
                    if not target_date:
                        return (
                            "Please specify a day for availability check.\n"
                            "For example:\n"
                            "• Show slots for tomorrow\n"
                            "• What times are available on Friday?"
                        )

                    event_types = self.calendly_client.get_event_types()
                    if not event_types:
                        return "No event types available."

                    slots = self.calendly_client.get_available_slots(
                        event_types[0]["uuid"],
                        target_date,
                        target_date + timedelta(days=1),
                    )

                    if not slots:
                        return f"No available slots found for {target_date.strftime('%A, %B %d')}."

                    response = f"⏰ Available slots for {target_date.strftime('%A, %B %d')}:\n\n"
                    for slot in slots:
                        slot_time = datetime.fromisoformat(
                            slot["start_time"].replace("Z", "+00:00")
                        )
                        response += f"• {slot_time.strftime('%I:%M %p')}\n"

                    response += "\nTo book, say 'Book a meeting at [preferred time]'"
                    return response

                except Exception as e:
                    logging.error(f"Error checking availability: {e}")
                    return "Sorry, I couldn't check availability. Please try again."

            # Handle specific time booking
            elif "book" in message_lower and any(
                indicator in message_lower for indicator in ["at ", "for ", "pm", "am"]
            ):
                try:
                    target_date, time_str = self._parse_date_time(message_lower)
                    if not time_str:
                        return "Please specify a time (e.g., 2pm or 2:30pm)"

                    event_types = self.calendly_client.get_event_types()
                    if not event_types:
                        return "No event types available."

                    scheduling_link = self.create_scheduling_link(
                        event_types[0]["uuid"],
                        wa_id,
                        start_time=target_date.isoformat(),
                        booking_mapper=current_app.config["booking_mapper"],
                    )

                    if scheduling_link:
                        return (
                            f"🔗 Here's your booking link for {target_date.strftime('%I:%M %p on %A, %B %d')}:\n"
                            f"{scheduling_link}"
                        )
                    return "Sorry, I couldn't create a booking link for that time."

                except Exception as e:
                    logging.error(f"Error creating time-specific booking: {e}")
                    return "Sorry, I couldn't create the booking. Please try again."

            # General scheduling request
            elif "schedule" in message_lower or "book" in message_lower:
                try:
                    event_types = self.calendly_client.get_event_types()
                    if not event_types:
                        return "No event types are currently available for scheduling."

                    response = "📅 Available Meeting Options:\n\n"
                    for event_type in event_types:
                        scheduling_link = self.create_scheduling_link(
                            event_type["uuid"],
                            wa_id,
                            booking_mapper=current_app.config["booking_mapper"],
                        )
                        response += (
                            f"• {event_type['name']}\n"
                            f"⏰ Duration: {event_type['duration']} min\n"
                            f"🔗 {scheduling_link}\n\n"
                        )

                    response += (
                        "Click any link above to schedule!\n\n"
                        "You can also:\n"
                        "• 'Show available slots for tomorrow'\n"
                        "• 'Book a meeting at 2pm tomorrow'"
                    )
                    return response

                except Exception as e:
                    logging.error(f"Error creating scheduling options: {e}")
                    print(e)
                    return "Sorry, I encountered an error while setting up scheduling. Please try again."

            # Default response
            return (
                "I can help you schedule meetings! Try:\n\n"
                "1. 'Show available meeting types'\n"
                "2. 'Show available slots for tomorrow'\n"
                "3. 'Book a meeting at 2pm'\n"
                "4. 'Schedule a consultation'"
            )

        except Exception as e:
            logging.error(f"Error processing scheduling query: {e}")
            return "Sorry, I encountered an error while scheduling. Please try asking in a different way."

    async def _get_event_types_response(self) -> str:
        """Get formatted event types response"""
        event_types = self.calendly_client.get_event_types()
        if not event_types:
            return "No meeting types are currently available."

        response = "📅 Available Meeting Types:\n\n"
        for i, event_type in enumerate(event_types, 1):
            response += (
                f"{i}. {event_type['name']}\n"
                f"⏰ Duration: {event_type['duration']} min\n"
                f"📝 {event_type.get('description', 'No description')}\n\n"
            )

        response += (
            "Try:\n• 'Show available slots for tomorrow'\n• 'Book a meeting at 2pm'"
        )
        return response

    async def _get_availability_response(self, message: str) -> str:
        """Get availability for a specific date"""
        try:
            target_date, _ = self._parse_date_time(message)

            event_types = self.calendly_client.get_event_types()
            if not event_types:
                return "No event types available."

            slots = self.calendly_client.get_available_slots(
                event_types[0]["uuid"], target_date, target_date + timedelta(days=1)
            )

            if not slots:
                return (
                    f"No available slots found for {target_date.strftime('%A, %B %d')}."
                )

            response = (
                f"⏰ Available slots for {target_date.strftime('%A, %B %d')}:\n\n"
            )
            for slot in slots:
                slot_time = datetime.fromisoformat(
                    slot["start_time"].replace("Z", "+00:00")
                )
                response += f"• {slot_time.strftime('%I:%M %p')}\n"

            response += "\nTo book, say 'Book a meeting at [preferred time]'"
            return response

        except Exception as e:
            logging.error(f"Error getting availability: {e}")
            return "Sorry, I couldn't check availability. Please try again."

    async def _create_specific_time_link(self, message: str, wa_id: str) -> str:
        """Create a scheduling link for a specific time"""
        try:
            target_date, time_str = self._parse_date_time(message)

            if not time_str:
                return "Please specify a time (e.g., 2pm or 2:30pm)"

            # Parse the time
            try:
                if ":" in time_str:
                    hour, minute = (
                        time_str.replace("pm", "").replace("am", "").split(":")
                    )
                    hour = int(hour)
                    minute = int(minute)
                else:
                    hour = int(time_str.replace("pm", "").replace("am", ""))
                    minute = 0

                if "pm" in time_str.lower() and hour != 12:
                    hour += 12
                elif "am" in time_str.lower() and hour == 12:
                    hour = 0

                target_time = target_date.replace(hour=hour, minute=minute)

                # Get first event type (or parse from message if specified)
                event_types = self.calendly_client.get_event_types()
                if not event_types:
                    return "No event types available."

                link = self.create_scheduling_link(
                    event_types[0]["uuid"], wa_id, start_time=target_time.isoformat()
                )

                if link:
                    return (
                        f"🔗 Here's your booking link for {target_time.strftime('%I:%M %p on %A, %B %d')}:\n"
                        f"{link}"
                    )
                return "Sorry, I couldn't create a booking link for that time."

            except ValueError:
                return "Invalid time format. Please use format like '2pm' or '2:30pm'"

        except Exception as e:
            logging.error(f"Error creating specific time link: {e}")
            return "Sorry, I couldn't create the booking link. Please try again."

    def create_scheduling_link(
        self,
        event_type_uuid: str,
        wa_id: str,
        start_time: Optional[str] = None,
        booking_mapper=None,  # Add this parameter
    ) -> Optional[str]:
        """Create a scheduling link with WhatsApp tracking"""
        try:
            print(f"\nCreating scheduling link for event: {event_type_uuid}")
            print(f"WhatsApp ID: {wa_id}")

            tracking_data = {
                "whatsapp_id": wa_id,
                "custom": {"whatsapp_id": wa_id, "source": "whatsapp"},
                "utm_source": wa_id,
                "utm_medium": "whatsapp",
                "utm_campaign": "whatsapp_booking",
            }

            print(f"Tracking data: {json.dumps(tracking_data, indent=2)}")

            result = self.calendly_client.create_scheduling_link(
                event_type_uuid=event_type_uuid,
                tracking=tracking_data,
                start_time=start_time,
            )

            # If we have the booking mapper, store the mapping after creating the link
            if result and isinstance(result, dict) and booking_mapper:
                booking_url = result.get("resource", {}).get("booking_url")
                event_uri = result.get("resource", {}).get("owner")
                if booking_url and event_uri:
                    try:
                        booking_mapper.add_scheduled_event(
                            event_uri=event_uri,
                            whatsapp_id=wa_id,
                            event_type_id=event_type_uuid,
                            status="pending",
                        )
                    except Exception as e:
                        print(f"Error storing booking mapping: {e}")
                        # Continue even if mapping fails

            if result and isinstance(result, dict):
                booking_url = result.get("resource", {}).get("booking_url")
                print(f"Created booking URL: {booking_url}")
                return booking_url

            print("Failed to create booking URL")
            return None

        except Exception as e:
            logging.error(f"Error creating scheduling link: {e}", exc_info=True)
            print(f"Error in create_scheduling_link: {str(e)}")
            return None
