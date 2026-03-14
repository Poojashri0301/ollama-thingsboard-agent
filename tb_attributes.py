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
    if "error" in result:
        err_msg = result["error"].get("message", str(result["error"]))
        print(f"[MCP Error] {err_msg}")
        return "{}" # Return empty JSON string instead of raw error
    try:
        return result["result"]["content"][0]["text"]
    except Exception as e:
        print(f"[Extract Error] {e} in {result}")
        return "{}"

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

    max_pages = 10
    while page < max_pages:
        data = json.loads(_extract(mcp.call_tool("getUsers", {"pageSize": "50", "page": str(page)})))
        
        for entity in data.get("data", []):
            searchable = "".join(filter(None, [
                entity.get("firstName", ""),
                entity.get("lastName", ""),
                entity.get("email", "")
            ])).lower()
            if entityName.lower().replace(" ", "") in searchable:
                entity_id = entity["id"]["id"]
                break
        
        if entity_id:
            break
        if not data.get("hasNext", False):
            return f"No USER found with name: {entityName}"
        page += 1

    # Get keys first to avoid "keys is null" error in getAttributesByScope
    keys_raw = getAttributeKeysByScope("USER", entity_id, "SERVER_SCOPE")
    try:
        keys_list = json.loads(keys_raw)
        if not keys_list or not isinstance(keys_list, list):
            return f"No attributes found for USER: {entityName}"
        
        raw = getAttributesByScope("USER", entity_id, "SERVER_SCOPE", keys=",".join(keys_list))
        parsed_list = json.loads(raw)
        
        # Flatten to simpler {key: value} format
        flattened = {item.get("key"): item.get("value") for item in parsed_list}
        return json.dumps(flattened, indent=2)
    except Exception as e:
        return f"Error fetching attributes for {entityName}: {e}"

# # Get attributes by name for DEVICE without knowing the ID.
def getDeviceAttributesByName(entityName: str, scope: str = "") -> str:
    """
    Get attributes of a device by name.
    Optional 'scope': 'SERVER_SCOPE', 'SHARED_SCOPE', or 'CLIENT_SCOPE'.
    If no scope is provided, it returns all three.
    Use when user asks for 'attributes', 'properties', or specific status like 'battery'.
    """

    from datetime import datetime, timezone

    # Helper to convert epoch ms → UTC string
    def convert_epoch_ms_to_utc(epoch_ms):
        dt = datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    page, entity_id = 0, None

    max_pages = 10
    while page < max_pages:
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
    scopes = [scope] if scope else ["SERVER_SCOPE", "SHARED_SCOPE", "CLIENT_SCOPE"]

    for s in scopes:
        try:
            keys_raw = _extract(mcp.call_tool("getAttributeKeysByScope", {
                "entityType": "DEVICE",
                "entityIdStr": entity_id,
                "scope": s
            }))

            keys_list = json.loads(keys_raw)
            if not isinstance(keys_list, list):
                results[s] = {}
                continue

            if keys_list:
                keys_str = ",".join(keys_list)

                attr_raw = _extract(mcp.call_tool("getAttributesByScope", {
                    "entityType": "DEVICE",
                    "entityIdStr": entity_id,
                    "scope": s,
                    "keys": keys_str
                }))

                try:
                    parsed_list = json.loads(attr_raw)
                    if not isinstance(parsed_list, list):
                        results[s] = {}
                        continue

                    # Flatten to {key: value} and convert timestamps
                    flattened = {}
                    for item in parsed_list:
                        key = item.get("key")
                        val = item.get("value")
                        
                        # Fix connection and forecast timestamps (handle typos)
                        if key in [
                            "lastForecastUpdate", "lastForcastUpdate",
                            "lastConnectTime", "lastDisconnectTime", "lastActivityTime"
                        ]:
                            try:
                                flattened[key] = convert_epoch_ms_to_utc(int(val))
                            except:
                                flattened[key] = val
                        else:
                            flattened[key] = val
                    
                    results[s] = flattened

                except json.JSONDecodeError:
                    results[s] = {"error": "JSON decode failed"}
            else:
                results[s] = {}

        except Exception as e:
            results[s] = {"error": str(e)}

    return json.dumps(results, indent=2)

# Fetches all currently active devices.
def getActiveDevices() -> str:
    """
    Get all currently active devices using a high-performance batch fetch.
    """
    # 1. Get all device names/IDs
    from tb_device import getTenantDevices
    raw_devices = json.loads(getTenantDevices(pageSize=500, max_pages=1)) 
    devices = raw_devices.get("devices", [])
    if not devices:
        return "No devices found in tenant."

    entity_ids = [d["id"] for d in devices]

    # 2. Query for their 'active' status and last activity in bulk
    args = {
        "entityListFilter": {
            "type": "entityList",
            "entityType": "DEVICE",
            "entityList": entity_ids
        },
        "keyFilters": [],
        "entityFields": [{"type": "ENTITY_FIELD", "key": "name"}],
        "latestValues": [
            {"type": "ATTRIBUTE", "key": "active"},
            {"type": "SERVER_ATTRIBUTE", "key": "active"},
            {"type": "CLIENT_ATTRIBUTE", "key": "active"},
            {"type": "SHARED_ATTRIBUTE", "key": "active"},
            {"type": "ATTRIBUTE", "key": "lastActivityTime"},
            {"type": "SERVER_ATTRIBUTE", "key": "lastActivityTime"},
            {"type": "CLIENT_ATTRIBUTE", "key": "lastActivityTime"},
            {"type": "SHARED_ATTRIBUTE", "key": "lastActivityTime"}
        ],
        "pageSize": str(len(entity_ids)),
        "page": "0"
    }
    
    try:
        import time
        now_ms = int(time.time() * 1000)
        # Active if 'active' is True OR lastActivityTime < 24 hours ago (1440 mins)
        threshold_ms = 24 * 60 * 60 * 1000 

        raw_data = _extract(mcp.call_tool("findEntityDataByEntityListFilter", args))
        data = json.loads(raw_data)
        
        active_list = []
        for entity in data.get("data", []):
            name = entity.get("latest", {}).get("ENTITY_FIELD", {}).get("name", {}).get("value")
            latest = entity.get("latest", {})
            
            # Check explicit 'active' attribute
            is_active = False
            for scope in ["ATTRIBUTE", "SERVER_ATTRIBUTE", "CLIENT_ATTRIBUTE", "SHARED_ATTRIBUTE"]:
                val = latest.get(scope, {}).get("active", {}).get("value")
                if val in ["true", True]:
                    is_active = True
                    break
            
            # Fallback: Check lastActivityTime (if within 60 mins)
            if not is_active:
                for scope in ["ATTRIBUTE", "SERVER_ATTRIBUTE", "CLIENT_ATTRIBUTE", "SHARED_ATTRIBUTE"]:
                    last_act = latest.get(scope, {}).get("lastActivityTime", {}).get("value")
                    try:
                        if last_act and (now_ms - int(last_act)) < threshold_ms:
                            is_active = True
                            break
                    except:
                        pass

            if is_active:
                active_list.append({
                    "name": name,
                    "id": entity.get("entityId", {}).get("id"),
                    "status": "Active"
                })
            
        return json.dumps({"active_devices": active_list, "count": len(active_list)}, indent=2)
    except Exception as e:
        print(f"[tb_attributes] Batch fetch failed: {e}. Falling back to list-and-check...")
        return "Failed to fetch active status for all devices. Please specify a device name to check specifically."

def getDevicesConnectionStatus() -> str:
    """
    Get connection status (lastConnectTime, lastDisconnectTime, active) for all devices in bulk.
    Use when user asks for 'connection times', 'disconnect times', or 'status of all devices'.
    """
    from tb_device import getTenantDevices
    raw_devices = json.loads(getTenantDevices(pageSize=500, max_pages=1)) 
    devices = raw_devices.get("devices", [])
    if not devices:
        return "No devices found."

    entity_ids = [d["id"] for d in devices]
    
    args = {
        "entityListFilter": {"type": "entityList", "entityType": "DEVICE", "entityList": entity_ids},
        "entityFields": [{"type": "ENTITY_FIELD", "key": "name"}],
        "latestValues": [
            {"type": "ATTRIBUTE", "key": "active"},
            {"type": "SERVER_ATTRIBUTE", "key": "active"},
            {"type": "SERVER_ATTRIBUTE", "key": "lastConnectTime"},
            {"type": "SERVER_ATTRIBUTE", "key": "lastDisconnectTime"},
            {"type": "SERVER_ATTRIBUTE", "key": "lastActivityTime"},
            {"type": "SHARED_ATTRIBUTE", "key": "lastForcastUpdate"},
            {"type": "SHARED_ATTRIBUTE", "key": "lastForcastStatus"},
            {"type": "SHARED_ATTRIBUTE", "key": "lastForecastUpdate"},
            {"type": "SHARED_ATTRIBUTE", "key": "lastForecastStatus"}
        ],
        "pageSize": str(len(entity_ids)),
        "page": "0"
    }
    
    try:
        raw_data = _extract(mcp.call_tool("findEntityDataByEntityListFilter", args))
        data = json.loads(raw_data)
        
        results = []
        for entity in data.get("data", []):
            name = entity.get("latest", {}).get("ENTITY_FIELD", {}).get("name", {}).get("value")
            latest = entity.get("latest", {})
            
            # Extract and convert timestamps
            status = {
                "name": name,
                "active": "false",
                "lastConnectTime": "N/A",
                "lastDisconnectTime": "N/A",
                "lastActivityTime": "N/A",
                "lastForecastStatus": "N/A",
                "lastForecastUpdate": "N/A"
            }
            
            # Active status
            for scope in ["ATTRIBUTE", "SERVER_ATTRIBUTE"]:
                val = latest.get(scope, {}).get("active", {}).get("value")
                if val is not None:
                    status["active"] = str(val)
                    break
            
            # Connection Timestamps (SERVER_ATTRIBUTE)
            for key in ["lastConnectTime", "lastDisconnectTime", "lastActivityTime"]:
                val = latest.get("SERVER_ATTRIBUTE", {}).get(key, {}).get("value")
                if val:
                    try:
                        status[key] = convert_epoch_ms_to_utc(int(val))
                    except:
                        status[key] = str(val)

            # Forecast Status & Update (SHARED_ATTRIBUTE)
            # Handle both spellings (handle typo "Forcast")
            for scope in ["SHARED_ATTRIBUTE", "SERVER_ATTRIBUTE"]:
                # Status
                f_status = latest.get(scope, {}).get("lastForecastStatus", {}).get("value") or \
                           latest.get(scope, {}).get("lastForcastStatus", {}).get("value")
                if f_status:
                    status["lastForecastStatus"] = str(f_status)
                
                # Update Time
                f_update = latest.get(scope, {}).get("lastForecastUpdate", {}).get("value") or \
                           latest.get(scope, {}).get("lastForcastUpdate", {}).get("value")
                if f_update:
                    try:
                        status["lastForecastUpdate"] = convert_epoch_ms_to_utc(int(f_update))
                    except:
                        status["lastForecastUpdate"] = str(f_update)
            
            results.append(status)
            
        return json.dumps({"devices": results, "count": len(results)}, indent=2)
    except Exception as e:
        return f"Error fetching connection status: {e}"

def getDevicesAttributes(keys: str) -> str:
    """
    Get specific attributes for ALL devices in bulk.
    Example keys: 'ipAddress, public_ip, private_ip, software_version, networkSpeed'.
    Use when user asks 'what are the [attribute] for all devices' or 'what is the [attribute]'.
    This avoids asking the user for a device ID if they just want a general list.
    """
    from tb_device import getTenantDevices
    keys_list = [k.strip() for k in keys.split(",") if k.strip()]
    if not keys_list:
        return "No keys specified."

    raw_devices = json.loads(getTenantDevices(pageSize=500, max_pages=1)) 
    devices = raw_devices.get("devices", [])
    if not devices:
        return "No devices found."

    # If the user asks for "all" custom attributes, we fetch all attributes for devices
    if "all" in [k.lower() for k in keys_list] or "custom" in [k.lower() for k in keys_list]:
        results = []
        for d in devices[:20]: # Limit to 20 to avoid massive API overhead/context lengths
            try:
                attr_data = json.loads(getDeviceAttributesByName(d["name"]))
                
                # Flatten all scopes
                all_attrs = {}
                for scope, values in attr_data.items():
                    if isinstance(values, dict):
                        for k, v in values.items():
                            all_attrs[k] = v
                            
                # Filter out standard base attributes to highlight "custom" ones
                standard_keys = {"lastConnectTime", "lastDisconnectTime", "lastActivityTime", "active", "inactivityAlarmTime"}
                custom_attrs = {k: v for k, v in all_attrs.items() if k not in standard_keys}
                
                if custom_attrs:
                    results.append({"name": d["name"], "custom_attributes": custom_attrs})
            except:
                pass
        return json.dumps({"devices": results, "note": "Showing all custom attributes for up to 20 devices."}, indent=2)

    entity_ids = [d["id"] for d in devices]
    
    # We'll check all scopes for these keys
    latest_values = []
    for k in keys_list:
        latest_values.append({"type": "ATTRIBUTE", "key": k})
        latest_values.append({"type": "SERVER_ATTRIBUTE", "key": k})
        latest_values.append({"type": "SHARED_ATTRIBUTE", "key": k})
        latest_values.append({"type": "CLIENT_ATTRIBUTE", "key": k})

    args = {
        "entityListFilter": {"type": "entityList", "entityType": "DEVICE", "entityList": entity_ids},
        "entityFields": [{"type": "ENTITY_FIELD", "key": "name"}],
        "latestValues": latest_values,
        "pageSize": str(len(entity_ids)),
        "page": "0"
    }
    
    try:
        raw_data = _extract(mcp.call_tool("findEntityDataByEntityListFilter", args))
        data = json.loads(raw_data)
        
        results = []
        for entity in data.get("data", []):
            name = entity.get("latest", {}).get("ENTITY_FIELD", {}).get("name", {}).get("value")
            latest = entity.get("latest", {})
            
            status = {"name": name}
            
            # Check all scopes for each requested key
            for k in keys_list:
                found_val = "N/A"
                for scope in ["ATTRIBUTE", "SERVER_ATTRIBUTE", "SHARED_ATTRIBUTE", "CLIENT_ATTRIBUTE"]:
                    val = latest.get(scope, {}).get(k, {}).get("value")
                    if val is not None:
                        found_val = str(val)
                        break
                status[k] = found_val
            
            results.append(status)
            
        return json.dumps({"devices": results, "count": len(results)}, indent=2)
    except Exception as e:
        return f"Error fetching bulk attributes: {e}"
