# tb_customer.py
from mcp_client import MCPClient
import json

mcp = None

def set_mcp_client(client: MCPClient):
    global mcp
    mcp = client

def _extract(result):
    if "error" in result:
        print(f"[MCP Error] {result['error'].get('message')}")
        return "{}"
    try:
        return result["result"]["content"][0]["text"]
    except Exception as e:
        print(f"[Extract Error] {e}")
        return "{}"
# Get all customers from ThingsBoard.
def getCustomers(pageSize: int = 100, max_pages: int = 10) -> str:
    """
    Get a summary list of all customers.
    Returns: Name, ID, Title.
    """
    all_data = []
    page = 0
    while page < max_pages:
        raw = _extract(mcp.call_tool("getCustomers", {"pageSize": int(pageSize), "page": int(page)}))
        data = json.loads(raw)
        
        # Summarize
        for c in data.get("data", []):
            all_data.append({
                "title": c.get("title"),
                "id": c.get("id", {}).get("id"),
                "name": c.get("name")
            })

        if not data.get("hasNext", False):
            break
        page += 1
    return json.dumps({"customers": all_data, "count": len(all_data), "truncated": page == max_pages}, indent=2)

#  Get a specific customer by their UUID.
def getCustomerById(customerId: str) -> str:
    """Get a customer by their ID. Use when user provides a specific customer ID."""

    result = mcp.call_tool("getCustomerById", {"customerId": customerId})
    return _extract(result)

# Find a customer by searching their name.
def findCustomerByName(customerName: str) -> str:
    """
    Find a customer by their name.
    Use when user asks to find or search for a customer by name.
    Extract name directly from user message. Do NOT ask for name if already mentioned.
    """
    args = {"pageSize": "50", "page": "0", "textSearch": customerName}
    result = mcp.call_tool("getCustomers", args)
    return _extract(result)

# Get all customers that belong to a specific entity group.
def getCustomersByEntityGroupId(entityGroupId: str, pageSize: str = "100", textSearch: str = "", sortProperty: str = "", sortOrder: str = "") -> str:
    """Get customers in a specific entity group. Use when user asks for customers in a group."""
    all_data = []
    page = 0
    max_pages = 10
    while page < max_pages:
        args = {"entityGroupId": entityGroupId, "pageSize": int(pageSize), "page": int(page)}
        if textSearch: args["textSearch"] = textSearch
        if sortProperty: args["sortProperty"] = sortProperty
        if sortOrder: args["sortOrder"] = sortOrder
        data = json.loads(_extract(mcp.call_tool("getCustomersByEntityGroupId", args)))
        all_data.extend(data.get("data", []))
        if not data.get("hasNext", False):
            break
        page += 1
    return json.dumps({"data": all_data}, indent=2)