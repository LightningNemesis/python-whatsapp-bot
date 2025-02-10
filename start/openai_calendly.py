from openai import OpenAI
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import json


class CalendlyAssistant:
    def __init__(self, calendly_client):
        """Initialize the assistant with Calendly client."""
        load_dotenv()
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.calendly_client = calendly_client
        self.assistant = self._create_assistant()
        self.thread = None

    def _create_assistant(self):
        """Create or load the OpenAI assistant with specific functions."""
        # Define the assistant's functions
        functions = [
            {
                "name": "get_event_types",
                "description": "Get all available event types from Calendly",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
            {
                "name": "get_available_slots",
                "description": "Get available time slots for a specific event type",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "event_type_uuid": {
                            "type": "string",
                            "description": "UUID of the event type",
                        }
                    },
                    "required": ["event_type_uuid"],
                },
            },
            {
                "name": "create_scheduling_link",
                "description": "Generate a scheduling link for an event type",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "event_type_uuid": {
                            "type": "string",
                            "description": "UUID of the event type",
                        }
                    },
                    "required": ["event_type_uuid"],
                },
            },
        ]

        # Create the assistant
        assistant = self.openai_client.beta.assistants.create(
            name="Calendly Scheduling Assistant",
            instructions="""You are a helpful scheduling assistant that helps users book meetings using Calendly. 
            Start each conversation by presenting the available options:
            1. View all available event types
            2. Check available slots for a specific event
            3. Generate a scheduling link
            4. Get confirmation details (after scheduling)
            
            Guide users through the scheduling process step by step.""",
            model="gpt-4-turbo-preview",
            tools=[{"type": "function", "function": f} for f in functions],
        )
        return assistant

    def _handle_function_call(self, function_name: str, arguments: Dict) -> Dict:
        """Handle function calls from the assistant."""
        if function_name == "get_event_types":
            return self.calendly_client.get_event_types()
        elif function_name == "get_available_slots":
            event_type_uuid = arguments["event_type_uuid"]
            now = datetime.now(timezone.utc)
            end_time = now + timedelta(days=7)
            return self.calendly_client.get_available_slots(
                event_type_uuid, now, end_time
            )
        elif function_name == "create_scheduling_link":
            event_type_uuid = arguments["event_type_uuid"]
            return self.calendly_client.create_scheduling_link(event_type_uuid)
        return {"error": "Unknown function"}

    def start_conversation(self):
        """Start a new conversation thread."""
        self.thread = self.openai_client.beta.threads.create()
        return self.send_message("Hi! I'd like to schedule a meeting.")

    def send_message(self, message: str) -> str:
        """Send a message to the assistant and get the response."""
        if not self.thread:
            self.thread = self.openai_client.beta.threads.create()

        # Add the user's message to the thread
        self.openai_client.beta.threads.messages.create(
            thread_id=self.thread.id, role="user", content=message
        )

        # Run the assistant
        run = self.openai_client.beta.threads.runs.create(
            thread_id=self.thread.id, assistant_id=self.assistant.id
        )

        # Wait for the run to complete
        while run.status in ["queued", "in_progress"]:
            run = self.openai_client.beta.threads.runs.retrieve(
                thread_id=self.thread.id, run_id=run.id
            )

        # Handle function calls if any
        if run.status == "requires_action":
            tool_outputs = []
            for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                result = self._handle_function_call(function_name, arguments)
                tool_outputs.append(
                    {"tool_call_id": tool_call.id, "output": json.dumps(result)}
                )

            # Submit the results back to the assistant
            run = self.openai_client.beta.threads.runs.submit_tool_outputs(
                thread_id=self.thread.id, run_id=run.id, tool_outputs=tool_outputs
            )

            # Wait for final response
            while run.status in ["queued", "in_progress"]:
                run = self.openai_client.beta.threads.runs.retrieve(
                    thread_id=self.thread.id, run_id=run.id
                )

        # Get the assistant's messages
        messages = self.openai_client.beta.threads.messages.list(
            thread_id=self.thread.id
        )

        # Return the latest assistant message
        for msg in messages.data:
            if msg.role == "assistant":
                return msg.content[0].text.value

        return "No response from assistant."

    def handle_webhook_event(self, webhook_data: Dict) -> str:
        """Handle incoming webhook events and generate appropriate responses."""
        event_type = webhook_data.get("event")
        payload = webhook_data.get("payload", {})

        if event_type == "invitee.created":
            # Someone scheduled a meeting
            scheduled_event = payload.get("scheduled_event", {})
            message = f"""
    A new meeting has been scheduled!
    - Name: {payload.get('name')}
    - Email: {payload.get('email')}
    - Event: {scheduled_event.get('name')}
    - Start Time: {scheduled_event.get('start_time')}
    - End Time: {scheduled_event.get('end_time')}
    """
            return self.send_message(
                f"Process this new meeting notification: {message}"
            )

        elif event_type == "invitee.canceled":
            # Someone canceled a meeting
            cancellation = payload.get("cancellation", {})
            message = f"""
    A meeting has been canceled!
    - Name: {payload.get('name')}
    - Email: {payload.get('email')}
    - Canceled by: {cancellation.get('canceled_by', 'Unknown')}
    - Reason: {cancellation.get('reason', 'No reason provided')}
    """
            return self.send_message(
                f"Process this cancellation notification: {message}"
            )

        return self.send_message(
            f"Process this webhook event: {json.dumps(webhook_data)}"
        )
