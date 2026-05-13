"""
Chapter 6 — Tool Use and Function Calling — Example 3
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch06_03_search_orders_by_product.py
"""
# ch06_debug_cycle.py (additions to ch06_tool_set.py)
# Same pinned versions as ch06_tool_set.py.

def search_orders_by_product(product_keyword: str, customer_id: str) -> str:
    """Search orders by product keyword for a specific customer."""
    # In production this would be a database query; here we filter the in-memory dict
    matches = [
        order for order in ORDERS.values()
        if product_keyword.lower() in order["product"].lower()
        and order["customer_id"] == customer_id
    ]
    if not matches:
        return ToolResult(
            success=False, data=None,
            error=(
                f"No orders found matching '{product_keyword}' for this customer. "
                "Ask the customer to check their confirmation email for the exact order ID."
            ),
            error_category="resource",
        ).to_json()
    return ToolResult(
        success=True,
        data={"orders": matches, "count": len(matches)},
        error=None, error_category=None,
    ).to_json()


SEARCH_TOOL_DEF = {
    "name": "search_orders_by_product",
    "description": (
        "Search for orders by product keyword when the customer remembers what they bought "
        "but not their order ID. Use this tool before get_order_by_id when the customer "
        "describes their order by product rather than by ID. "
        "Do not call this tool if the customer has already provided an order ID. "
        "Requires: a keyword from the product name (e.g. 'kettle', 'grinder') and the customer_id."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "product_keyword": {
                "type": "string",
                "description": "A keyword from the product name as described by the customer."
            },
            "customer_id": {
                "type": "string",
                "description": "The customer's ID from the current session context."
            }
        },
        "required": ["product_keyword", "customer_id"],
    },
}

if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        result = search_orders_by_product('example-key', 'abc-123')
        print(result)
