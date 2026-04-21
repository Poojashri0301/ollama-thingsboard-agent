
# tb_user.py
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
def getUsers(pageSize: int = 100, max_pages: int = 10) -> str:
    """
    Get a summary list of all users in the tenant.
    Returns: Name, Email, Authority, ID.
    Use ONLY when user asks to 'list all users'.
    """
    all_data = []
    page = 0
    while page < max_pages:
        result = mcp.call_tool("getUsers", {"pageSize": int(pageSize), "page": int(page)})
        data = json.loads(_extract(result))
        
        # Summarize
        for u in data.get("data", []):
            all_data.append({
                "name": f"{u.get('firstName', '')} {u.get('lastName', '')}".strip(),
                "email": u.get("email"),
                "authority": u.get("authority"),
                "userId": u.get("id", {}).get("id"),
                "enabled": u.get("additionalInfo", {}).get("userStatus", "") != "DISABLED" # Standard TB way or common field
            })

        if not data.get("hasNext", False):
            break
        page += 1
    return json.dumps({"users": all_data, "count": len(all_data), "truncated": page == max_pages}, indent=2, ensure_ascii=False)

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
    all_users = []
    page = 0
    max_pages = 10
    while page < max_pages:
        args = {"pageSize": 50, "page": page, "textSearch": userName}
        raw_result = _extract(mcp.call_tool("getUsers", args))
        try:
            data = json.loads(raw_result)
            users_page = data.get("data", [])
            all_users.extend(users_page)
            if not data.get("hasNext", False):
                break
            page += 1
        except json.JSONDecodeError:
            # If raw_result is not JSON, it's likely an error message
            return raw_result
        except Exception as e:
            return f"An unexpected error occurred: {e}"

    if not all_users:
        return f"No user found matching: {userName}"
    if len(all_users) == 1:
        return json.dumps(all_users[0], indent=2, ensure_ascii=False)
    return json.dumps(all_users, indent=2, ensure_ascii=False)

def getUserFullDetails(userName: str) -> str:
    """
    Get everything about a user: profile, attributes, and settings.
    Use when user asks for 'details', 'info', 'everything', or 'who is' a user.
    """
    from tb_attributes import getUserAttributesByName
    
    # 1. Get user profile
    user_raw = findUserByName(userName)
    if "No user found" in user_raw:
        return user_raw
    
    try:
        user_base = json.loads(user_raw)
        if isinstance(user_base, list):
            return f"Multiple users found for '{userName}':\n" + json.dumps(user_base, indent=2, ensure_ascii=False)
    except:
        return f"Error parsing user info: {user_raw}"

    # 2. Get Attributes
    attrs_raw = getUserAttributesByName(userName)
    try:
        attrs = json.loads(attrs_raw)
    except:
        attrs = {"error": attrs_raw}

    # 3. Combine
    full_details = {
        "profile_summary": {
            "name": f"{user_base.get('firstName', '')} {user_base.get('lastName', '')}".strip(),
            "email": user_base.get("email"),
            "authority": user_base.get("authority"),
            "customerId": user_base.get("customerId", {}).get("id")
        },
        "attributes": attrs,
        "raw_profile": user_base
    }

    return json.dumps(full_details, indent=2, ensure_ascii=False)


# Get all tenant administrator users assigned to a specific tenant. 
def getTenantAdmins() -> str:
    """
    Get all tenant admin users (managers).
    Use when user asks for admins, administrators, or managers.
    """
    # Get tenant ID from current user info
    tenant_id = json.loads(_extract(mcp.call_tool("getTenantById", {})))["id"]["id"]
    
    all_users = []
    page = 0
    max_pages = 10
    while page < max_pages:
        data = json.loads(_extract(mcp.call_tool("getTenantAdmins", {
            "tenantId": tenant_id, "pageSize": 100, "page": page
        })))
        all_users.extend(data.get("data", []))
        if not data.get("hasNext", False):
            break
        page += 1

    if not all_users:
        return "No admins found."

    result = [{
        "name": f"{u.get('firstName', '')} {u.get('lastName', '')}".strip(),
        "email": u.get("email", "")
    } for u in all_users]

    return json.dumps(result, indent=2, ensure_ascii=False)

# Get all users assigned to a specific customer.
def getCustomerUsers(customerId: str, pageSize: str = "100", textSearch: str = "", sortProperty: str = "", sortOrder: str = "") -> str:
    """Get all users under a specific customer. Use when user asks for users of a customer by customer ID."""
    all_data = []
    page = 0
    max_pages = 10
    while page < max_pages:
        args = {"customerId": customerId, "pageSize": int(pageSize), "page": page}
        if textSearch: args["textSearch"] = textSearch
        if sortProperty: args["sortProperty"] = sortProperty
        if sortOrder: args["sortOrder"] = sortOrder
        
        data = json.loads(_extract(mcp.call_tool("getCustomerUsers", args)))
        all_data.extend(data.get("data", []))
        if not data.get("hasNext", False):
            break
        page += 1
    return json.dumps({"data": all_data}, indent=2, ensure_ascii=False)

def getAllCustomerUsers(max_customers: int = 5, max_users_per_customer: int = 2) -> str:
    """
    Get all users across all customers (members/regular users).
    Use when user asks for members, customer users, or regular users.
    """
    page, all_users = 0, []
    while page < max_customers:
        customers = json.loads(_extract(mcp.call_tool("getCustomers", {"pageSize": "50", "page": str(page)})))
        
        for customer in customers.get("data", []):
            customer_id = customer["id"]["id"]
            cust_name = customer.get("name", "Unknown")
            print(f"[tb_user] Fetching users for customer: {cust_name}...")
            cust_page = 0
            while cust_page < max_users_per_customer:
                try:
                    data = json.loads(_extract(mcp.call_tool("getCustomerUsers", {
                        "customerId": customer_id, "pageSize": "50", "page": str(cust_page)
                    })))
                    all_users.extend(data.get("data", []))
                    if not data.get("hasNext", False):
                        break
                    cust_page += 1
                except:
                    break
        
        if not customers.get("hasNext", False):
            break
        page += 1

    if not all_users:
        return "No members found."

    result = [{
        "name": f"{u.get('firstName', '')} {u.get('lastName', '')}".strip(),
        "email": u.get("email", ""),
        "customer": u.get("customerTitle", "N/A"),
        "enabled": u.get("additionalInfo", {}).get("userStatus", "") != "DISABLED"
    } for u in all_users]

    return json.dumps({"data": result, "truncated": page == max_customers}, indent=2, ensure_ascii=False)

# Get list of users that can be assigned to a specific alarm.
def getUsersForAssign(alarmId: str, pageSize: str = "100", textSearch: str = "", sortProperty: str = "", sortOrder: str = "") -> str:
    """Get users available for assignment. Use when user asks who can be assigned to a device or entity."""
    all_data = []
    page = 0
    max_pages = 10
    while page < max_pages:
        args = {"alarmId": alarmId, "pageSize": int(pageSize), "page": page}
        if textSearch: args["textSearch"] = textSearch
        if sortProperty: args["sortProperty"] = sortProperty
        if sortOrder: args["sortOrder"] = sortOrder
        data = json.loads(_extract(mcp.call_tool("getUsersForAssign", args)))
        all_data.extend(data.get("data", []))
        if not data.get("hasNext", False):
            break
        page += 1
    return json.dumps({"data": all_data}, indent=2, ensure_ascii=False)

# Get all users that belong to a specific entity group.
def getUsersByEntityGroupId(entityGroupId: str, pageSize: str = "100", textSearch: str = "", sortProperty: str = "", sortOrder: str = "") -> str:
    """Get users in a specific entity group. Use when user asks for users in a group."""
    all_data = []
    page = 0
    max_pages = 10
    while page < max_pages:
        args = {"entityGroupId": entityGroupId, "pageSize": int(pageSize), "page": page}
        if textSearch: args["textSearch"] = textSearch
        if sortProperty: args["sortProperty"] = sortProperty
        if sortOrder: args["sortOrder"] = sortOrder
        data = json.loads(_extract(mcp.call_tool("getUsersByEntityGroupId", args)))
        all_data.extend(data.get("data", []))
        if not data.get("hasNext", False):
            break
        page += 1
    return json.dumps({"data": all_data}, indent=2, ensure_ascii=False)
