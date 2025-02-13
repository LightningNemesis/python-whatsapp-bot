# assistant_interface.py
from inventory_querier import InventoryQuerier
from openai import OpenAI
from typing import Dict, List
import json


class InventoryAssistant:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.querier = InventoryQuerier()

        self.system_message = """You are an Inventory Assistant that helps users query information about stored 
        inventory items. 
        You can only answer questions related to the inventory database.

        You should:
        - Only answer questions about inventory data
        - Use available functions to query the database
        - Give clear, concise responses
        - Be flexible in interpreting location references (e.g., "Tank A" = "Storage Tank A")
        - If a question is not about inventory, politely explain that you can only help with inventory-related queries

        Available information includes:
        - Item details (ID, name, quantity, unit, location, supplier)
        - Stock levels
        - Location information
        - Supplier information

        Example valid questions:
        - How many barrels of Crude Oil do we have?
        - What items are in Storage Tank A? (or simply "Tank A")
        - Who supplies our Natural Gas?
        - What's our total inventory in MCF?
        - Show me everything in Tank A
        - Give me details about Pipeline B

        For non-inventory questions, respond with:
        "I can only help with questions about the inventory database. Please ask a question about the inventory items, 
        their quantities, locations, or suppliers."
        """

    async def process_query(self, user_query: str) -> str:
        messages = [
            {"role": "system", "content": self.system_message},
            {"role": "user", "content": user_query},
        ]

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_all_items",
                    "description": "Get all inventory items",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_item_by_id",
                    "description": "Get an item by its ID",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "item_id": {
                                "type": "integer",
                                "description": "The ID of the item",
                            }
                        },
                        "required": ["item_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_items_by_location",
                    "description": "Get items in a specific location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "The location to search for",
                            }
                        },
                        "required": ["location"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_total_quantity_by_unit",
                    "description": "Get total quantity for a specific unit",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "unit": {
                                "type": "string",
                                "description": "The unit to total (e.g., barrels, MCF, gallons)",
                            }
                        },
                        "required": ["unit"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_items_by_supplier",
                    "description": "Get items from a specific supplier",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "supplier": {
                                "type": "string",
                                "description": "The supplier name to search for",
                            }
                        },
                        "required": ["supplier"],
                    },
                },
            },
        ]

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini", messages=messages, tools=tools, tool_choice="auto"
            )

            response_message = response.choices[0].message

            if response_message.tool_calls:
                tool_call = response_message.tool_calls[0]
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                # Call the appropriate function
                if function_name == "get_all_items":
                    result = self.querier.get_all_items()
                elif function_name == "get_item_by_id":
                    result = self.querier.get_item_by_id(**function_args)
                elif function_name == "get_items_by_location":
                    result = self.querier.get_items_by_location(**function_args)
                elif function_name == "get_total_quantity_by_unit":
                    result = self.querier.get_total_quantity_by_unit(**function_args)
                elif function_name == "get_items_by_supplier":
                    result = self.querier.get_items_by_supplier(**function_args)

                messages.append(response_message)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": str(result),
                    }
                )

                final_response = self.client.chat.completions.create(
                    model="gpt-4o-mini", messages=messages
                )

                return final_response.choices[0].message.content

            return response_message.content

        except Exception as e:
            return f"Sorry, I encountered an error: {str(e)}"
