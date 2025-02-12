# main_assistant.py
import asyncio
from assistant_interface import InventoryAssistant
import os
from dotenv import load_dotenv


async def main():
    load_dotenv()
    assistant = InventoryAssistant(os.getenv("OPENAI_API_KEY"))

    print("Inventory Assistant initialized. Type 'quit' to exit.")
    print("Ask me questions about the inventory!")

    while True:
        user_input = input("\nYour question: ").strip()

        if user_input.lower() == "quit":
            break

        response = await assistant.process_query(user_input)
        print("\nAssistant:", response)


if __name__ == "__main__":
    asyncio.run(main())
