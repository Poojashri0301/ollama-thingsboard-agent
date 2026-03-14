# tb_device.py
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

# ── Get all devices (paginated) ──────────────────────────

def getTenantDevices(pageSize: int = 100, type: str = "", textSearch: str = "", sortProperty: str = "", sortOrder: str = "", max_pages: int = 10) -> str:
    """
    Get a summary list of all devices in the tenant.
    Returns: Name, ID, Type, Label for each device.
    Use when user asks to 'list all devices' or 'count devices'.
    """
    all_data = []
    page = 0
    while page < max_pages:
        args = {}
        args["pageSize"] = int(pageSize)
        args["page"] = int(page)
        if type: args["type"] = type
        if textSearch: args["textSearch"] = textSearch
        if sortProperty: args["sortProperty"] = sortProperty
        if sortOrder: args["sortOrder"] = sortOrder
        
        raw = _extract(mcp.call_tool("getTenantDevices", args))
        data = json.loads(raw)
        
        # Summarize to save context space (Crucial for large tenants)
        for d in data.get("data", []):
            all_data.append({
                "name": d.get("name"),
                "id": d.get("id", {}).get("id"),
                "type": d.get("type"),
                "label": d.get("label"),
                "active": d.get("active") # Activity status
            })

        if not data.get("hasNext", False):
            break
        page += 1
    
    return json.dumps({"devices": all_data, "count": len(all_data), "truncated": page == max_pages}, indent=2)

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

def getTenantDeviceInfos(pageSize: int = 100, type: str = "", deviceProfileId: str = "", textSearch: str = "", sortProperty: str = "", sortOrder: str = "", max_pages: int = 10) -> str:
    """
    Get summary list with extra info for all devices.
    Returns: Name, ID, Type, Customer, Profile for each device.
    """
    all_data = []
    page = 0
    while page < max_pages:
        args = {}
        args["pageSize"] = int(pageSize)
        args["page"] = int(page)
        if type: args["type"] = type
        if deviceProfileId: args["deviceProfileId"] = deviceProfileId
        if textSearch: args["textSearch"] = textSearch
        if sortProperty: args["sortProperty"] = sortProperty
        if sortOrder: args["sortOrder"] = sortOrder
        
        raw = _extract(mcp.call_tool("getTenantDeviceInfos", args))
        data = json.loads(raw)
        
        # Summarize
        for d in data.get("data", []):
            all_data.append({
                "name": d.get("name"),
                "id": d.get("id", {}).get("id"),
                "type": d.get("type"),
                "active": d.get("active"), # Activity status
                "customer": d.get("customerTitle"),
                "profile": d.get("deviceProfileName")
            })

        if not data.get("hasNext", False):
            break
        page += 1
    
    return json.dumps({"device_infos": all_data, "count": len(all_data), "truncated": page == max_pages}, indent=2)

# ── Get multiple devices by IDs ──────────────────────────

def getDevicesByIds(deviceIds: str) -> str:
    """Get multiple devices by their IDs. Use when user provides multiple device IDs."""
    result = mcp.call_tool("getDevicesByIds", {"deviceIds": deviceIds})
    return _extract(result)

# ── Get devices by customer ──────────────────────────────

def getCustomerDevices(customerId: str, pageSize: int = 100, type: str = "", textSearch: str = "", sortProperty: str = "", sortOrder: str = "", max_pages: int = 10) -> str:
    """Get summarized devices belonging to a customer."""
    all_data = []
    page = 0
    while page < max_pages:
        print(f"[tb_device] Fetching customer devices page {page} for customer {customerId}...")
        args = {"customerId": customerId, "pageSize": int(pageSize), "page": int(page)}
        if type: args["type"] = type
        if textSearch: args["textSearch"] = textSearch
        if sortProperty: args["sortProperty"] = sortProperty
        if sortOrder: args["sortOrder"] = sortOrder
        
        raw = _extract(mcp.call_tool("getCustomerDevices", args))
        data = json.loads(raw)
        for d in data.get("data", []):
            all_data.append({
                "name": d.get("name"), 
                "id": d.get("id", {}).get("id"), 
                "type": d.get("type"),
                "active": d.get("active")
            })
        if not data.get("hasNext", False):
            break
        page += 1
        
    return json.dumps({"devices": all_data, "count": len(all_data), "truncated": page == max_pages}, indent=2)

# ── Get detailed device info by customer ─────────────────

def getCustomerDeviceInfos(customerId: str, pageSize: str = "100", type: str = "", deviceProfileId: str = "", textSearch: str = "", sortProperty: str = "", sortOrder: str = "") -> str:
    """Get detailed info of all devices under a customer. Use when user wants full details of customer devices."""
    all_data = []
    page = 0
    while True:
        args = {"customerId": customerId, "pageSize": pageSize, "page": str(page)}
        if type: args["type"] = type
        if deviceProfileId: args["deviceProfileId"] = deviceProfileId
        if textSearch: args["textSearch"] = textSearch
        if sortProperty: args["sortProperty"] = sortProperty
        if sortOrder: args["sortOrder"] = sortOrder
        
        raw = _extract(mcp.call_tool("getCustomerDeviceInfos", args))
        data = json.loads(raw)
        all_data.extend(data.get("data", []))
        if not data.get("hasNext", False):
            break
        page += 1
        
    return json.dumps({"data": all_data}, indent=2)

# ── Get devices by entity group ──────────────────────────

def getDevicesByEntityGroupId(entityGroupId: str, pageSize: str = "100", sortProperty: str = "", sortOrder: str = "") -> str:
    """Get devices by entity group ID. Use when user asks for devices in a specific group."""
    all_data = []
    page = 0
    while True:
        args = {"entityGroupId": entityGroupId, "pageSize": pageSize, "page": str(page)}
        if sortProperty: args["sortProperty"] = sortProperty
        if sortOrder: args["sortOrder"] = sortOrder
        
        raw = _extract(mcp.call_tool("getDevicesByEntityGroupId", args))
        data = json.loads(raw)
        all_data.extend(data.get("data", []))
        if not data.get("hasNext", False):
            break
        page += 1
        
    return json.dumps({"data": all_data}, indent=2)

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


def getDeviceFullDetails(deviceName: str) -> str:
    """
    Get everything about a device: profile, all server/shared/client attributes, and latest telemetry.
    Use when user asks for 'details', 'info', 'full info', 'everything', or 'specs' of a device.
    """
    from tb_attributes import getDeviceAttributesByName
    from tb_telemetry import getLatestTimeseriesByName

    print(f"[tb_device] Fetching full details for device: {deviceName}...")
    
    # 1. Get device basic info
    device_raw = getDeviceByName(deviceName)
    if "No device found" in device_raw:
        return device_raw

    try:
        device_base = json.loads(device_raw)
    except:
        return f"Error parsing device info: {device_raw}"

    # 2. Get ALL Attributes (SERVER, SHARED, CLIENT)
    attrs_raw = getDeviceAttributesByName(deviceName)
    try:
        attrs = json.loads(attrs_raw)
    except:
        attrs = {"error": attrs_raw}

    # 3. Get Latest Telemetry
    telemetry_raw = getLatestTimeseriesByName(entityType="DEVICE", entityName=deviceName)
    try:
        telemetry = json.loads(telemetry_raw)
    except:
        telemetry = {"error": telemetry_raw}

    # 4. Filter out empty scopes to keep output clean
    clean_attrs = {k: v for k, v in attrs.items() if v}

    # 5. Combine
    full_details = {
        "summary": {
            "name": device_base.get("name"),
            "type": device_base.get("type"),
            "label": device_base.get("label"),
            "createdTime": device_base.get("createdTime")
        },
        "attributes": clean_attrs,
        "latest_telemetry": telemetry,
        "raw_profile": device_base
    }

    return json.dumps(full_details, indent=2)


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
    all_devices = []
    page = 0
    while True:
        devices_raw = _extract(mcp.call_tool("getCustomerDevices", {
            "customerId": customer_id, "pageSize": "100", "page": str(page)
        }))
        devices_data = json.loads(devices_raw)
        all_devices.extend(devices_data.get("data", []))
        if not devices_data.get("hasNext", False):
            break
        page += 1

    if not all_devices:
        return f"No devices found for user: {userName}"

    result = [{
        "name": d.get("name"),
        "type": d.get("type"),
        "label": d.get("label")
    } for d in all_devices]

    return json.dumps(result, indent=2)