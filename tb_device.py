# tb_device.py
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

# ── Get all devices (paginated) ──────────────────────────

def getTenantDevices(pageSize: str = "20", page: str = "0", type: str = "", textSearch: str = "", sortProperty: str = "", sortOrder: str = "") -> str:
    """Get all devices in the tenant. Use when user asks to list all devices."""
    args = {"pageSize": pageSize, "page": page}
    if type:
        args["type"] = type
    if textSearch:
        args["textSearch"] = textSearch
    if sortProperty:
        args["sortProperty"] = sortProperty
    if sortOrder:
        args["sortOrder"] = sortOrder
    result = mcp.call_tool("getTenantDevices", args)
    return _extract(result)

# ── Get device by ID ─────────────────────────────────────

def getDeviceById(deviceId: str) -> str:
    """Get a device by its ID. Use when user provides a specific device ID."""
    result = mcp.call_tool("getDeviceById", {"deviceId": deviceId})
    return _extract(result)

# ── Get device by name ───────────────────────────────────

def getTenantDevice(deviceName: str) -> str:
    """Get a single tenant device. Use when user asks for a specific device."""
    result = mcp.call_tool("getTenantDevice", {"deviceName": deviceName})
    return _extract(result)

# ── Get detailed device info by ID ───────────────────────

def getDeviceInfo(deviceId: str) -> str:
    """Get detailed info of a device. Use when user asks for device details/info."""

    result = mcp.call_tool("getDeviceInfo", {"deviceId": deviceId})
    return _extract(result)

# ── Get all devices with detailed info ───────────────────

def getTenantDeviceInfos(pageSize: str = "20", page: str = "0", type: str = "", deviceProfileId: str = "", textSearch: str = "", sortProperty: str = "", sortOrder: str = "") -> str:
    """Get detailed info of all tenant devices. Use when user wants full device details list."""
    args = {"pageSize": pageSize, "page": page}
    if type:
        args["type"] = type
    if deviceProfileId:
        args["deviceProfileId"] = deviceProfileId
    if textSearch:
        args["textSearch"] = textSearch
    if sortProperty:
        args["sortProperty"] = sortProperty
    if sortOrder:
        args["sortOrder"] = sortOrder
    result = mcp.call_tool("getTenantDeviceInfos", args)
    return _extract(result)

# ── Get multiple devices by IDs ──────────────────────────

def getDevicesByIds(deviceIds: str) -> str:
    """Get multiple devices by their IDs. Use when user provides multiple device IDs."""
    result = mcp.call_tool("getDevicesByIds", {"deviceIds": deviceIds})
    return _extract(result)

# ── Get devices by customer ──────────────────────────────

def getCustomerDevices(customerId: str, pageSize: str = "20", page: str = "0", type: str = "", textSearch: str = "", sortProperty: str = "", sortOrder: str = "") -> str:
    """Get all devices belonging to a customer. Use when user asks for devices of a specific customer."""
    args = {"customerId": customerId, "pageSize": pageSize, "page": page}
    if type:
        args["type"] = type
    if textSearch:
        args["textSearch"] = textSearch
    if sortProperty:
        args["sortProperty"] = sortProperty
    if sortOrder:
        args["sortOrder"] = sortOrder
    result = mcp.call_tool("getCustomerDevices", args)
    return _extract(result)

# ── Get detailed device info by customer ─────────────────

def getCustomerDeviceInfos(customerId: str, pageSize: str = "20", page: str = "0", type: str = "", deviceProfileId: str = "", textSearch: str = "", sortProperty: str = "", sortOrder: str = "") -> str:
    """Get detailed info of all devices under a customer. Use when user wants full details of customer devices."""

    args = {"customerId": customerId, "pageSize": pageSize, "page": page}
    if type:
        args["type"] = type
    if deviceProfileId:
        args["deviceProfileId"] = deviceProfileId
    if textSearch:
        args["textSearch"] = textSearch
    if sortProperty:
        args["sortProperty"] = sortProperty
    if sortOrder:
        args["sortOrder"] = sortOrder
    result = mcp.call_tool("getCustomerDeviceInfos", args)
    return _extract(result)

# ── Get devices by entity group ──────────────────────────

def getDevicesByEntityGroupId(entityGroupId: str, pageSize: str = "20", page: str = "0", sortProperty: str = "", sortOrder: str = "") -> str:
    """Get devices by entity group ID. Use when user asks for devices in a specific group."""

    args = {"entityGroupId": entityGroupId, "pageSize": pageSize, "page": page}
    if sortProperty:
        args["sortProperty"] = sortProperty
    if sortOrder:
        args["sortOrder"] = sortOrder
    result = mcp.call_tool("getDevicesByEntityGroupId", args)
    return _extract(result)

# Get device details by searching device name across all pages.
def getDeviceByName(deviceName: str) -> str:
    """Get a device by its exact name. Use when user provides exact device name."""
    page = 0
    while True:
        data = json.loads(_extract(mcp.call_tool("getTenantDevices", {
            "pageSize": "50", "page": str(page)
        })))
        match = next((d for d in data.get("data", [])
                     if deviceName.lower() in d.get("name", "").lower()), None)
        if match:
            return json.dumps(match, indent=2)
        if not data.get("hasNext", False):
            return f"No device found with name: {deviceName}"
        page += 1


def getDevicesByUserName(userName: str) -> str:
    """
    Get all devices belonging to a user's customer by username.
    Use when user asks for devices of a specific user.
    Extract userName directly from user message. Do NOT ask again if already mentioned.
    Examples:
    - 'what devices does pooja have' -> userName='pooja'
    - 'list devices of john' -> userName='john'
    - 'devices under pooja user' -> userName='pooja'
    """
    page, user = 0, None

    # Step 1: Find user by name
    while True:
        data = json.loads(_extract(mcp.call_tool("getUsers", {"pageSize": "50", "page": str(page)})))
        for entity in data.get("data", []):
            searchable = " ".join(filter(None, [
                entity.get("firstName", ""),
                entity.get("lastName", ""),
                entity.get("email", "")
            ]))
            if userName.lower() in searchable.lower():
                user = entity
                break
        if user:
            break
        if not data.get("hasNext", False):
            return f"No USER found with name: {userName}"
        page += 1

    # Step 2: Get customer ID from user
    customer_id = user.get("customerId", {}).get("id")
    if not customer_id:
        return f"User '{userName}' is not associated with any customer."

    # Step 3: Get devices for that customer
    devices_raw = _extract(mcp.call_tool("getCustomerDevices", {
        "customerId": customer_id, "pageSize": "50", "page": "0"
    }))

    try:
        devices = json.loads(devices_raw)
    except:
        return f"Failed to parse devices: {devices_raw}"

    device_list = devices.get("data", [])
    if not device_list:
        return f"No devices found for user: {userName}"

    result = [{
        "name": d.get("name"),
        "type": d.get("type"),
        "label": d.get("label")
    } for d in device_list]

    return json.dumps(result, indent=2)