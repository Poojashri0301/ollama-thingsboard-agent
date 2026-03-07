
# tb_user.py
from mcp_client import MCPClient
import json
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
def getUsers(pageSize: str = "20", page: str = "0") -> str:
    """Get all users in the tenant. Use when user asks to list all users."""

    result = mcp.call_tool("getUsers", {"pageSize": pageSize, "page": page})
    return _extract(result)

# Get a specific user by their ID.
def getUserById(userId: str) -> str:
    """Get a user by their ID. Use when user provides a specific user ID."""
    result = mcp.call_tool("getUserById", {"userId": userId})
    return _extract(result)

# Find a customer by searching their name.
def findUserByName(userName: str) -> str:
    """
    Find a user by their name or email.
    Use when user asks to find or search for a user by name or email.
    Extract name directly from user message. Do NOT ask for name if already mentioned.
    Examples:
    - 'find user john' -> entityName='john'
    - 'search for john@example.com' -> entityName='john@example.com'
    """
    args = {"pageSize": "50", "page": "0", "textSearch": userName}
    raw_result = _extract(mcp.call_tool("getUsers", args))
    try:
        data = json.loads(raw_result)
        users = data.get("data", [])
        if not users:
            return f"No user found matching: {userName}"
        if len(users) == 1:
            return json.dumps(users[0], indent=2)
        return json.dumps(users, indent=2)
    except:
        return raw_result

# Get all tenant administrator users assigned to a specific tenant. 
def getTenantAdmins() -> str:
    """
    Get all tenant admin users (managers).
    Use when user asks for admins, administrators, or managers.
    Examples:
    - 'show managers'
    - 'list admins'
    - 'who are the tenant admins'
    """
    # Get tenant ID from current user info
    tenant_id = json.loads(_extract(mcp.call_tool("getTenantById", {})))["id"]["id"]
    
    data = json.loads(_extract(mcp.call_tool("getTenantAdmins", {
        "tenantId": tenant_id, "pageSize": "50", "page": "0"
    })))

    users = data.get("data", [])
    if not users:
        return "No admins found."

    result = [{
        "name": f"{u.get('firstName', '')} {u.get('lastName', '')}".strip(),
        "email": u.get("email", "")
    } for u in users]

    return json.dumps(result, indent=2)

# Get all users assigned to a specific customer.
def getCustomerUsers(customerId: str, pageSize: str = "20", page: str = "0", textSearch: str = "", sortProperty: str = "", sortOrder: str = "") -> str:
    """Get all users under a specific customer. Use when user asks for users of a customer by customer ID."""

    args = {"customerId": customerId, "pageSize": pageSize, "page": page}
    if textSearch:
        args["textSearch"] = textSearch
    if sortProperty:
        args["sortProperty"] = sortProperty
    if sortOrder:
        args["sortOrder"] = sortOrder
    result = mcp.call_tool("getCustomerUsers", args)
    return _extract(result)

# Get all users for the current tenant with authority CUSTOMER_USER.
def getAllCustomerUsers() -> str:
    """
    Get all users across all customers (members/regular users).
    Use when user asks for members, customer users, or regular users.
    Examples:
    - 'show members'
    - 'list customer users'
    - 'who are the members'
    """
    # First get all customers
    page, all_users = 0, []
    customers = json.loads(_extract(mcp.call_tool("getCustomers", {"pageSize": "50", "page": "0"})))
    
    for customer in customers.get("data", []):
        customer_id = customer["id"]["id"]
        try:
            data = json.loads(_extract(mcp.call_tool("getCustomerUsers", {
                "customerId": customer_id, "pageSize": "50", "page": "0"
            })))
            all_users.extend(data.get("data", []))
        except:
            continue

    if not all_users:
        return "No members found."

    result = [{
        "name": f"{u.get('firstName', '')} {u.get('lastName', '')}".strip(),
        "email": u.get("email", "")
    } for u in all_users]

    return json.dumps(result, indent=2)

# Get list of users that can be assigned to a specific alarm.
def getUsersForAssign(alarmId: str, pageSize: str = "20", page: str = "0", textSearch: str = "", sortProperty: str = "", sortOrder: str = "") -> str:
    """Get users available for assignment. Use when user asks who can be assigned to a device or entity."""

    args = {"alarmId": alarmId, "pageSize": pageSize, "page": page}
    if textSearch:
        args["textSearch"] = textSearch
    if sortProperty:
        args["sortProperty"] = sortProperty
    if sortOrder:
        args["sortOrder"] = sortOrder
    result = mcp.call_tool("getUsersForAssign", args)
    return _extract(result)

# Get all users that belong to a specific entity group.
def getUsersByEntityGroupId(entityGroupId: str, pageSize: str = "20", page: str = "0", textSearch: str = "", sortProperty: str = "", sortOrder: str = "") -> str:
    """Get users in a specific entity group. Use when user asks for users in a group."""

    args = {"entityGroupId": entityGroupId, "pageSize": pageSize, "page": page}
    if textSearch:
        args["textSearch"] = textSearch
    if sortProperty:
        args["sortProperty"] = sortProperty
    if sortOrder:
        args["sortOrder"] = sortOrder
    result = mcp.call_tool("getUsersByEntityGroupId", args)
    return _extract(result)
