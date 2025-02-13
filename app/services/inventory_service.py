# app/services/inventory_service.py
from app.utils.inventory.inventory_db import InventoryDB
from openai import OpenAI
import json
import os


class InventoryAssistantService:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.db = InventoryDB("app/utils/inventory/inventory.db")

        self.system_message = """You are an Inventory Assistant integrated with WhatsApp that helps users query information about stored 
        inventory items. You can only answer questions related to the inventory database.

        You should:
        - Only answer questions about inventory data
        - Use available functions to query the database
        - Give clear, concise responses formatted for WhatsApp
        - Be flexible in interpreting references (e.g., "Tank A" = "Storage Tank A", "FuelMaster" = supplier query)
        - Keep responses concise and easy to read on mobile
        - Always provide a formatted response with emojis and clear structure
        - For supplier queries, show all items supplied by that supplier
        - For location queries, show all items in that location

        Available information includes:
        - Item details (ID, name, quantity, unit, location, supplier)
        - Stock levels
        - Location information
        - Supplier information

        Example valid questions and responses:

        Q: "What does FuelMaster supply?"
        A: "🏢 FuelMaster supplies:
        • Diesel Fuel (2,000 gallons)
        • Location: Storage Tank C"

        Q: "What's in Tank A?"
        A: "📍 Storage Tank A:
        • Crude Oil (5,000 barrels)
        • Supplier: OilCo"

        For non-inventory questions, respond with:
        "I can only help with questions about the inventory database. Please ask about our stock levels, locations, or suppliers."
        """

    async def process_query(self, message: str) -> str:
        """Process an inventory query and return a WhatsApp-friendly response"""
        messages = [
            {"role": "system", "content": self.system_message},
            {"role": "user", "content": message},
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
            {
                "type": "function",
                "function": {
                    "name": "get_all_suppliers",
                    "description": "Get a list of all unique suppliers and their items",
                    "parameters": {"type": "object", "properties": {}},
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
                    result = [dict(item) for item in self.db.list_items()]
                elif function_name == "get_item_by_id":
                    item = self.db.get_item(item_id=function_args["item_id"])
                    result = dict(item) if item else None
                elif function_name == "get_items_by_location":
                    items = self.db.list_items()
                    result = [
                        dict(item)
                        for item in items
                        if function_args["location"].lower() in item.location.lower()
                    ]
                elif function_name == "get_total_quantity_by_unit":
                    items = self.db.list_items()
                    result = sum(
                        item.quantity
                        for item in items
                        if item.unit.lower() == function_args["unit"].lower()
                    )
                elif function_name == "get_items_by_supplier":
                    items = self.db.list_items()
                    matching_items = [
                        dict(item)
                        for item in items
                        if function_args["supplier"].lower() in item.supplier.lower()
                    ]
                    result = {
                        "supplier": function_args["supplier"],
                        "items": matching_items,
                    }
                elif function_name == "get_all_suppliers":
                    items = self.db.list_items()
                    # Create a dictionary of suppliers and their items
                    suppliers_dict = {}
                    for item in items:
                        if item.supplier not in suppliers_dict:
                            suppliers_dict[item.supplier] = []
                        suppliers_dict[item.supplier].append(dict(item))
                    result = {
                        "suppliers": [
                            {"name": supplier, "items": items}
                            for supplier, items in suppliers_dict.items()
                        ]
                    }

                    # Special formatting for supplier list
                    response = "🏢 Our Suppliers:\n\n"
                    for supplier_data in result["suppliers"]:
                        response += f"• {supplier_data['name']}\n"
                        for item in supplier_data["items"]:
                            response += f"  - {item['item_name']} ({item['quantity']:,} {item['unit']})\n"
                    return response

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

                # Format supplier responses specially
                if function_name == "get_items_by_supplier":
                    supplier_name = function_args["supplier"]
                    if not result["items"]:
                        return f"No items found for supplier: {supplier_name}"

                    response = f"🏢 {supplier_name} supplies:\n"
                    for item in result["items"]:
                        response += f"• {item['item_name']} ({item['quantity']:,} {item['unit']})\n"
                        response += f"• Location: {item['location']}\n"
                    return response

                return final_response.choices[0].message.content

            return response_message.content

        except Exception as e:
            return "Sorry, I encountered an error while checking the inventory. Please try asking in a different way."
