# tb_customer.py
from mcp_client import MCPClient

mcp = None

def set_mcp_client(client: MCPClient):
    global mcp
    mcp = client

def _extract(result):
    try:
        return result["result"]["content"][0]["text"]
    except:
        return str(result)
# Get all customers from ThingsBoard.
def getCustomers(pageSize: str = "20", page: str = "0") -> str:
    """Get all customers in the tenant. Use when user asks to list all customers."""

    result = mcp.call_tool("getCustomers", {"pageSize": pageSize, "page": page})
    return _extract(result)

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
def getCustomersByEntityGroupId(entityGroupId: str, pageSize: str = "20", page: str = "0", textSearch: str = "", sortProperty: str = "", sortOrder: str = "") -> str:
    """Get customers in a specific entity group. Use when user asks for customers in a group."""
    args = {"entityGroupId": entityGroupId, "pageSize": pageSize, "page": page}
    if textSearch:
        args["textSearch"] = textSearch
    if sortProperty:
        args["sortProperty"] = sortProperty
    if sortOrder:
        args["sortOrder"] = sortOrder
    result = mcp.call_tool("getCustomersByEntityGroupId", args)
    return _extract(result)