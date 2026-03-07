# tb_attributes.py
from mcp_client import MCPClient
import json
mcp = None

from datetime import datetime, timezone

def convert_epoch_ms_to_utc(epoch_ms):
    dt = datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def set_mcp_client(client: MCPClient):
    global mcp
    mcp = client

def _extract(result):
    try:
        return result["result"]["content"][0]["text"]
    except:
        return str(result)

# Get all attribute keys for the specified entity.
def getAttributeKeys(entityType: str, entityIdStr: str) -> str:
    """Get all attribute keys for an entity. Use when user asks what attributes are available for an entity."""

    args = {
        "entityType": entityType,
        "entityIdStr": entityIdStr
    }
    result = mcp.call_tool("getAttributeKeys", args)
    return _extract(result)

# Get all attribute keys for the specified entity and scope.
def getAttributeKeysByScope(entityType: str, entityIdStr: str, scope: str) -> str:
    """Get attribute keys for a specific scope. Use when user asks for attribute keys in SERVER, SHARED, or CLIENT scope."""

    args = {
        "entityType": entityType,
        "entityIdStr": entityIdStr,
        "scope": scope
    }
    result = mcp.call_tool("getAttributeKeysByScope", args)
    return _extract(result)

# Get attributes for the specified entity.
def getAttributes(entityType: str, entityIdStr: str, keys: str = "") -> str:
    """Get attributes by entity ID and keys. Use when entity ID and attribute keys are already known."""

    args = {
        "entityType": entityType,
        "entityIdStr": entityIdStr
    }
    if keys:
        args["keys"] = keys
    result = mcp.call_tool("getAttributes", args)
    return _extract(result)

#  Get attributes for the specified entity and scope.
def getAttributesByScope(entityType: str, entityIdStr: str, scope: str, keys: str = "") -> str:
    """Get attributes for a specific scope. Use when scope is specified (SERVER_SCOPE, SHARED_SCOPE, CLIENT_SCOPE)."""

    args = {
        "entityType": entityType,
        "entityIdStr": entityIdStr,
        "scope": scope
    }
    if keys:
        args["keys"] = keys
    result = mcp.call_tool("getAttributesByScope", args)
    return _extract(result)

# Get attributes of a specific user.
def getUserAttributes(userId: str, scope: str = "SERVER_SCOPE") -> str:
    """Get attributes of a user by user ID. Use when user ID is already known."""

    result = mcp.call_tool("getAttributes", {
        "entityType": "USER",
        "entityIdStr": userId,
        "scope": scope
    })
    return _extract(result)

# Get attributes by name for USER without knowing the ID.
def getUserAttributesByName(entityName: str) -> str:
    """
    Get attributes of a user by name or email.
    Use when user asks for attributes/properties of a user by their name or email.
    Extract name directly from user message. Do NOT ask for name if already mentioned.
    Examples:
    - 'attributes of john@example.com' -> entityName='john@example.com'
    - 'show attributes of John Doe' -> entityName='John Doe'
    """
    page, entity_id = 0, None

    while True:
        data = json.loads(_extract(mcp.call_tool("getUsers", {"pageSize": "50", "page": str(page)})))
        
        for entity in data.get("data", []):
            searchable = " ".join(filter(None, [
                entity.get("firstName", ""),
                entity.get("lastName", ""),
                entity.get("email", "")
            ]))
            if entityName.lower() in searchable.lower():
                entity_id = entity["id"]["id"]
                break
        
        if entity_id:
            break
        if not data.get("hasNext", False):
            return f"No USER found with name: {entityName}"
        page += 1

    raw = getAttributesByScope("USER", entity_id, "SERVER_SCOPE")  # No keys = fetch all
    try:
        return json.dumps(json.loads(raw), indent=2)
    except json.JSONDecodeError:
        return raw

# # Get attributes by name for DEVICE without knowing the ID.
def getDeviceAttributesByName(entityName: str) -> str:
    """
    Get all attributes (SERVER, SHARED, CLIENT scope) of a device by name.
    Use when user asks for attributes, properties, last connect time, disconnect time,
    lastForecastUpdate, lastActivityTime, active status, ip address, or ANY non-telemetry data.
    Extract device name directly from user message. Do NOT ask for name if already mentioned.
    
    IMPORTANT: These are ATTRIBUTES not telemetry:
    - lastConnectTime, lastDisconnectTime, lastActivityTime, active
    - lastForecastUpdate, ipAddress, batteryStatus, firmware
    
    Examples:
    - 'attributes of thermostat' -> entityName='thermostat'
    - 'last connect time of thermostat' -> entityName='thermostat'
    - 'lastForecastUpdate for thermostat' -> entityName='thermostat'
    - 'is thermostat active' -> entityName='thermostat'
    - 'ip address of thermostat' -> entityName='thermostat'
    """

    from datetime import datetime, timezone

    # Helper to convert epoch ms → UTC string
    def convert_epoch_ms_to_utc(epoch_ms):
        dt = datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    page, entity_id = 0, None

    while True:
        data = json.loads(_extract(mcp.call_tool("getTenantDevices", {
            "pageSize": "50",
            "page": str(page)
        })))

        for entity in data.get("data", []):
            if entityName.lower() in entity.get("name", "").lower():
                entity_id = entity["id"]["id"]
                break

        if entity_id:
            break

        if not data.get("hasNext", False):
            return f"No DEVICE found with name: {entityName}"

        page += 1

    results = {}

    for scope in ["SERVER_SCOPE", "SHARED_SCOPE", "CLIENT_SCOPE"]:
        try:
            keys_raw = _extract(mcp.call_tool("getAttributeKeysByScope", {
                "entityType": "DEVICE",
                "entityIdStr": entity_id,
                "scope": scope
            }))

            keys_list = json.loads(keys_raw)

            if keys_list:
                keys_str = ",".join(keys_list)

                attr_raw = _extract(mcp.call_tool("getAttributesByScope", {
                    "entityType": "DEVICE",
                    "entityIdStr": entity_id,
                    "scope": scope,
                    "keys": keys_str
                }))

                try:
                    parsed_attrs = json.loads(attr_raw)

                    # 🔥 Timestamp Fix Added Here
                    for attr in parsed_attrs:
                        if attr.get("key") in [
                            "lastForecastUpdate",
                            "lastConnectTime",
                            "lastDisconnectTime",
                            "lastActivityTime"
                        ]:
                            try:
                                epoch = int(attr.get("value"))
                                attr["value"] = convert_epoch_ms_to_utc(epoch)
                            except:
                                pass

                    results[scope] = parsed_attrs

                except json.JSONDecodeError:
                    results[scope] = attr_raw
            else:
                results[scope] = []

        except Exception as e:
            results[scope] = f"Error: {str(e)}"

    return json.dumps(results, indent=2)

# Fetches all currently active devices.
def getActiveDevices() -> str:
   
    page, all_devices = 0, []

    while True:
        data = json.loads(_extract(mcp.call_tool("getTenantDevices", {"pageSize": "50", "page": str(page)})))
        all_devices.extend(data.get("data", []))
        if not data.get("hasNext", False):
            break
        page += 1

    active_devices = []
    for device in all_devices:
        entity_id = device["id"]["id"]
        try:
            keys_raw = json.loads(_extract(mcp.call_tool("getAttributeKeysByScope", {
                "entityType": "DEVICE", "entityIdStr": entity_id, "scope": "SERVER_SCOPE"
            })))
            if "active" in keys_raw:
                attrs = json.loads(_extract(mcp.call_tool("getAttributesByScope", {
                    "entityType": "DEVICE", "entityIdStr": entity_id, "scope": "SERVER_SCOPE", "keys": "active"
                })))
                if any(a.get("key") == "active" and a.get("value") == True for a in attrs):
                    active_devices.append({"name": device.get("name"), "type": device.get("type"), "id": entity_id})
        except:
            continue

    return json.dumps(active_devices, indent=2) if active_devices else "No active devices found."
