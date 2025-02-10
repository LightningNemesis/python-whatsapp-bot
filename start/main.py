from calendly_client import CalendlyClient
from openai_calendly import CalendlyAssistant
from dotenv import load_dotenv
import os


def main():
    # Load environment variables
    load_dotenv()

    # Initialize Calendly client
    calendly_client = CalendlyClient(os.getenv("CALENDLY_TOKEN"))

    # Initialize the assistant
    assistant = CalendlyAssistant(calendly_client)

    # Start conversation
    print("Assistant: Starting conversation...")
    response = assistant.start_conversation()
    print(response)

    # Main conversation loop
    while True:
        # Get user input
        user_input = input("\nYou: ").strip()

        if user_input.lower() in ["exit", "quit", "bye"]:
            print("Assistant: Goodbye!")
            break

        # Get assistant's response
        response = assistant.send_message(user_input)
        print("\nAssistant:", response)


if __name__ == "__main__":
    main()
