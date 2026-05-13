"""
Chapter 9 — Model Context Protocol — Example 2
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch09_02_list_tools.py
"""
# ch09_mcp_server.py
# Tested against mcp[cli]>=1.5.0, as of April 2026.
# Run with: python ch09_mcp_server.py
# Requires: mcp[cli]>=1.5

import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

app = Server("product-catalog")

CATALOG = {
    "kettle-blue": {"name": "Blue Kettle", "price": 49.99, "category": "kitchen"},
    "grinder-pro": {"name": "Coffee Grinder Pro", "price": 89.99, "category": "kitchen"},
    "lamp-desk": {"name": "Adjustable Desk Lamp", "price": 34.99, "category": "office"},
}
INVENTORY = {"kettle-blue": 12, "grinder-pro": 3, "lamp-desk": 0}


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_product",
            description=(
                "Look up product details by product ID. Use when the customer asks about "
                "a specific product's name, price, or category. Returns product info or an "
                "error if the product ID does not exist in the catalog."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "Product ID (e.g. 'kettle-blue'). Use search_products if you do not know the ID.",
                    }
                },
                "required": ["product_id"],
            },
        ),
        types.Tool(
            name="check_inventory",
            description=(
                "Check current stock level for a product. Returns the number of units in stock. "
                "A result of 0 means the product is out of stock. "
                "Only call this after confirming the product exists using get_product."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "Product ID (same format as get_product).",
                    }
                },
                "required": ["product_id"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "get_product":
        product_id = arguments.get("product_id", "")
        product = CATALOG.get(product_id)
        if product is None:
            result = {"success": False, "error": f"Product '{product_id}' not found. Valid IDs: {list(CATALOG.keys())}"}
        else:
            result = {"success": True, "data": product}
        return [types.TextContent(type="text", text=json.dumps(result))]

    if name == "check_inventory":
        product_id = arguments.get("product_id", "")
        if product_id not in CATALOG:
            result = {"success": False, "error": f"Product '{product_id}' not found. Verify the product ID first."}
        else:
            stock = INVENTORY.get(product_id, 0)
            result = {"success": True, "data": {"product_id": product_id, "units_in_stock": stock}}
        return [types.TextContent(type="text", text=json.dumps(result))]

    return [types.TextContent(type="text", text=json.dumps(
        {"success": False, "error": f"Unknown tool: {name}"}
    ))]


if __name__ == "__main__":
    import asyncio
    asyncio.run(stdio_server(app))
