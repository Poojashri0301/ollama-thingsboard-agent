# tb_telemetry.py
from mcp_client import MCPClient
import json
import time

mcp = None

def set_mcp_client(client: MCPClient):
    global mcp
    mcp = client

def _extract(result):
    try:
        return result["result"]["content"][0]["text"]
    except:
        return str(result)

def getTimeseriesKeys(entityType: str, entityIdStr: str) -> str:
    """Get all telemetry keys for a device. Use when user asks what telemetry data is available."""
    result = mcp.call_tool("getTimeseriesKeys", {"entityType": entityType, "entityIdStr": entityIdStr})
    return _extract(result)

def getLatestTimeseries(entityType: str, entityIdStr: str, keys: str = "") -> str:
    """Get latest telemetry values by entity ID. Use when entity ID is already known."""
    # If no keys provided, fetch all keys first
    if not keys:
        keys_raw = _extract(mcp.call_tool("getTimeseriesKeys", {
            "entityType": entityType, "entityIdStr": entityIdStr
        }))
        try:
            keys = ",".join(json.loads(keys_raw))
        except:
            return f"Failed to get keys: {keys_raw}"

    result = mcp.call_tool("getLatestTimeseries", {
        "entityType": entityType,
        "entityIdStr": entityIdStr,
        "keys": keys
    })
    return _extract(result)

def getTimeseries(entityType: str, entityIdStr: str, keys: str, startTs: int, endTs: int, limit: int = 100) -> str:
    """Get historical telemetry data for a time range. Use when user asks for telemetry history or past readings."""
    result = mcp.call_tool("getTimeseries", {
        "entityType": entityType,
        "entityIdStr": entityIdStr,
        "keys": keys,
        "startTs": startTs,
        "endTs": endTs,
        "limit": limit
    })
    return _extract(result)

def _find_device_id(entityName: str):
    """Helper: scan all pages to find device ID by name."""
    page = 0
    while True:
        data = json.loads(_extract(mcp.call_tool("getTenantDevices", {"pageSize": "50", "page": str(page)})))
        for e in data.get("data", []):
            if entityName.lower() in e.get("name", "").lower():
                return e["id"]["id"], e.get("name")
        if not data.get("hasNext", False):
            return None, None
        page += 1

def getTimeseriesByName(entityName: str = "", keys: str = "", hours: float = 0, limit: int = 10, calculate: str = "") -> str:
    """
    Get historical telemetry or aggregated stats for devices by key name.
    Automatically finds only devices that have the requested key — fast and efficient.
    NEVER ask for device name — searches ALL devices if not mentioned.
    NEVER default entityName to any specific device name.

    Time conversion:
    - '30 minutes' -> hours=0.5
    - '1 hour'     -> hours=1
    - '1 day'      -> hours=24
    - '1 week'     -> hours=168
    - '1 month'    -> hours=720
    - 'all time'   -> hours=0

    Examples:
    - 'minimum memory usage last 24 hours'  -> keys='memory', calculate='min', hours=24
    - 'average cpu last hour'               -> keys='cpu', calculate='average', hours=1
    - 'maximum water level last week'       -> keys='water', calculate='max', hours=168
    - 'last 10 temperature values'          -> keys='temperature', limit=10
    - 'minimum temperature last week'       -> keys='temperature', calculate='min', hours=168

    Key name hints — use short names, matching is flexible:
    - memory usage  -> keys='memory'
    - cpu usage     -> keys='cpu'
    - disk usage    -> keys='disk'
    - water level   -> keys='water'
    - temperature   -> keys='temperature'
    - humidity      -> keys='humidity'
    """
    now_ts = int(time.time() * 1000)
    start_ts = 0 if hours == 0 else now_ts - int(hours * 3600 * 1000)
    fetch_limit = 5000 if calculate else limit

    # Step 1: Get all devices
    page, all_devices = 0, []
    while True:
        data = json.loads(_extract(mcp.call_tool("getTenantDevices", {"pageSize": "50", "page": str(page)})))
        all_devices.extend(data.get("data", []))
        if not data.get("hasNext", False):
            break
        page += 1

    if entityName:
        all_devices = [d for d in all_devices if entityName.lower() in d.get("name", "").lower()]
        if not all_devices:
            return f"No device found with name: {entityName}"

    results = {}
    for device in all_devices:
        entity_id = device["id"]["id"]
        device_name = device.get("name")
        try:
            available_keys = json.loads(_extract(mcp.call_tool("getTimeseriesKeys", {
                "entityType": "DEVICE", "entityIdStr": entity_id
            })))
            if not available_keys:
                continue

            # Match key
            if keys:
                normalized = keys.lower().replace(" ", "").replace("_", "")
                matched = [k for k in available_keys if normalized in k.lower().replace(" ", "").replace("_", "")
                 or k.lower().replace(" ", "").replace("_", "") in normalized]
                if not matched:
                    continue
                fetch_keys = ",".join(matched)
            else:
                fetch_keys = ",".join(available_keys)

            # Fetch timeseries — single request, no agg parameter
            raw = _extract(mcp.call_tool("getTimeseries", {
                "entityType": "DEVICE", "entityIdStr": entity_id,
                "keys": fetch_keys, "startTs": start_ts,
                "endTs": now_ts, "limit": fetch_limit
            }))
            items = json.loads(raw)
            if not items:
                continue

            # Parse response
            parsed = [{
                "ts": i.get("ts"),
                "key": i.get("key") or i.get("kv", {}).get("key"),
                "value": i.get("strValue") or i.get("value") or i.get("kv", {}).get("strValue")
            } for i in items]

            if not calculate:
                results[device_name] = sorted(parsed, key=lambda x: x.get("ts", 0), reverse=True)
                continue

            # Calculate in Python across all fetched records
            values = []
            for item in parsed:
                try:
                    values.append(float(item["value"]))
                except:
                    continue

            if values:
                calc = calculate.lower().strip()
                results[device_name] = {
                    "key": fetch_keys,
                    "total_records_checked": len(values),
                    "calculate": calc,
                    "result": round(
                        min(values) if calc in ("min", "minimum", "lowest") else
                        max(values) if calc in ("max", "maximum", "highest") else
                        sum(values) / len(values), 4
                    ),
                    "min": round(min(values), 4),
                    "max": round(max(values), 4),
                    "average": round(sum(values) / len(values), 4)
                }

        except:
            continue

    return json.dumps(results, indent=2) if results else f"No telemetry data found for key: '{keys}'"

def getLatestTimeseriesByName(entityType: str = "DEVICE", entityName: str = "", keys: str = "") -> str:
    """
    Get latest telemetry values for a device by name or by key.
    Use when user asks for current/latest telemetry, sensor values, or readings.

    IMPORTANT RULES:
    - NEVER ask user for device name or key.
    - Extract key directly from user message.
    - NEVER use predicted/forecast keys unless user explicitly says predicted or forecast.
    - If no device name mentioned, search ALL devices.
    - Default entityType is always DEVICE.

    Examples:
    - 'what is the water level' -> entityName='', keys='water level'
    - 'current temperature' -> entityName='', keys='temperature'
    - 'telemetry of thermostat' -> entityName='thermostat', keys=''
    - 'humidity of thermostat' -> entityName='thermostat', keys='humidity'
    """
    tool_map = {"DEVICE": "getTenantDevices", "ASSET": "getTenantAssets", "USER": "getUsers"}
    tool = tool_map.get(entityType.upper())
    if not tool:
        return f"Unsupported entityType: {entityType}."

    page, all_entities = 0, []
    while True:
        data = json.loads(_extract(mcp.call_tool(tool, {"pageSize": "50", "page": str(page)})))
        all_entities.extend(data.get("data", []))
        if not data.get("hasNext", False):
            break
        page += 1

    if entityName:
        all_entities = [e for e in all_entities if entityName.lower() in e.get("name", "").lower()]
        if not all_entities:
            return f"No {entityType} found with name: {entityName}"

    user_key = keys.lower().strip()
    is_predicted = "predicted" in user_key or "forecast" in user_key

    results = {}
    for e in all_entities:
        entity_id = e["id"]["id"]
        device_name = e.get("name")
        try:
            keys_raw = _extract(mcp.call_tool("getTimeseriesKeys", {
                "entityType": entityType.upper(), "entityIdStr": entity_id
            }))
            available_keys = json.loads(keys_raw)
            if not available_keys:
                continue

            if user_key:
                normalized_user = user_key.replace(" ", "").replace("_", "").replace("%", "")
                matched_keys = []
                for k in available_keys:
                    normalized_k = k.lower().replace(" ", "").replace("_", "").replace("%", "")
                    if not is_predicted and any(p in k.lower() for p in ["predicted", "forecast", "avg"]):
                        continue
                    if normalized_user in normalized_k:
                        matched_keys.append(k)
                if not matched_keys:
                    continue
                fetch_keys = ",".join(matched_keys)
            else:
                if not is_predicted:
                    fetch_keys = ",".join([k for k in available_keys
                                         if not any(p in k.lower() for p in ["predicted", "forecast", "avg"])])
                else:
                    fetch_keys = ",".join(available_keys)

            if not fetch_keys:
                continue

            raw = _extract(mcp.call_tool("getLatestTimeseries", {
                "entityType": entityType.upper(),
                "entityIdStr": entity_id,
                "keys": fetch_keys
            }))
            telemetry = json.loads(raw)
            if telemetry:
                results[device_name] = telemetry
        except:
            continue

    if not results:
        return f"No telemetry found for key: '{keys}' across all devices."

    return json.dumps(results, indent=2)