# tb_telemetry.py
from mcp_client import MCPClient
import json
import time
from datetime import datetime

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
    max_pages = 10
    while page < max_pages:
        data = json.loads(_extract(mcp.call_tool("getTenantDevices", {"pageSize": "50", "page": str(page)})))
        for e in data.get("data", []):
            if entityName.lower() in e.get("name", "").lower():
                return e["id"]["id"], e.get("name")
        if not data.get("hasNext", False):
            return None, None
        page += 1

def getTimeseriesByName(entityName: str = "", keys: str = "", hours: float = 0, startTime: str = "", endTime: str = "", limit: int = 10, calculate: str = "") -> str:
    """
    Get historical telemetry or aggregated stats for devices by key name.
    Automatically finds only devices that have the requested key — fast and efficient.

    Time parameters:
    - hours: Relative time from now (e.g., hours=24 for last day).
    - startTime: Specific start (e.g., '2026-03-08' or '1772992095500').
    - endTime: Specific end (default: now).

    Examples:
    - 'temperature at timestamp 1772992095500' -> startTime='1772992095500', endTime='1772992095500'
    - 'highest temperature on march 8 2026'    -> startTime='2026-03-08', calculate='max'
    - 'average cpu last hour'                  -> hours=1, calculate='average'

    Key name hints — use short names, matching is flexible:
    - memory usage  -> keys='memory'
    - CPU/Temperature/Humidity/Water/Energy/Alerts
    """
    now_ts = int(time.time() * 1000)

    def parse_time(t_str: str) -> tuple[int, bool]:
        """Returns (timestamp_ms, is_date_only)"""
        if not t_str: return 0, False
        t_str = t_str.strip()
        if t_str.isdigit():
            val = int(t_str)
            if len(t_str) == 10: return val * 1000, False
            return val, False
        
        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%B %d %Y", "%b %d %Y", "%m/%d/%Y"):
            try:
                dt = datetime.strptime(t_str, fmt)
                is_day = "%H" not in fmt
                return int(dt.timestamp() * 1000), is_day
            except ValueError:
                continue
        return 0, False

            # Resolve time range
            if startTime:
                start_ts, is_day = parse_time(startTime)
                if endTime:
                    end_ts, _ = parse_time(endTime)
                elif is_day:
                    # If only a date like '2026-03-08' is given, search the full 24h of that day
                    end_ts = start_ts + (24 * 3600 * 1000) - 1
                else:
                    end_ts = now_ts
                
                # Ensure range is valid for TB
                if start_ts == end_ts:
                    end_ts += 1000 # 1s window if exact timestamp
                
                # High limit for explicit dates to avoid missing data
                fetch_limit = 10000
            else:
                start_ts = 0 if hours == 0 else now_ts - int(hours * 3600 * 1000)
                end_ts = now_ts
                fetch_limit = 5000 if calculate else limit

            # Resolve if user asked for predicted data
            is_predicted_query = "predicted" in keys.lower() or "forecast" in keys.lower()

            # Step 1: Get all devices
            page, all_devices = 0, []
            while True:
                # print(f"[tb_telemetry] Fetching devices page {page} for historical search...")
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
                        matched = []
                        for k in available_keys:
                            normalized_k = k.lower().replace(" ", "").replace("_", "")
                            if normalized in normalized_k or normalized_k in normalized:
                                # Exclude predicted/forecast keys unless explicitly requested
                                is_k_predicted = "predicted" in k.lower() or "forecast" in k.lower()
                                if not is_predicted_query and is_k_predicted:
                                    continue
                                matched.append(k)
                        
                        # SPECIAL HANDLING: If 'temperature' was asked, and we have both 'temperature' and 'temperature_celsius',
                        # prioritize the 'celsius' one as per user request.
                        if normalized == "temperature":
                            celsius_keys = [k for k in matched if "celsius" in k.lower()]
                            if celsius_keys:
                                matched = celsius_keys

                        if not matched:
                            continue
                        fetch_keys = ",".join(matched)
                    else:
                        fetch_keys = ",".join(available_keys)

            # Fetch timeseries
            args = {
                "entityType": "DEVICE", "entityIdStr": entity_id,
                "keys": fetch_keys, "startTs": str(start_ts),
                "endTs": str(end_ts),
                "orderBy": "DESC"
            }

            # If startTime is explicit, we fetch RAW data to ensure precision
            # and avoid server-side aggregation quirks with different data types.
            # For 24h windows, 5000 points is usually plenty.
            use_server_agg = bool(calculate and not startTime)

            if use_server_agg:
                calc_word = calculate.lower().strip()
                tb_agg = (
                    "MIN" if calc_word in ("min", "minimum", "lowest") else
                    "MAX" if calc_word in ("max", "maximum", "highest") else
                    "SUM" if calc_word in ("sum", "total") else
                    "COUNT" if calc_word in ("count", "number of") else
                    "AVG"
                )
                args["agg"] = tb_agg
                args["interval"] = str(end_ts - start_ts + 1)
            else:
                args["limit"] = str(fetch_limit)
                args["agg"] = "NONE"

            raw = _extract(mcp.call_tool("getTimeseries", args))
            items = json.loads(raw)
            
            if not items:
                continue

            # Parse response and flatten for LLM
            parsed = {}
            if isinstance(items, dict):
                for key, data_points in items.items():
                    if not isinstance(data_points, list): continue
                    parsed[key] = []
                    for dp in data_points:
                        val = str(dp.get("value") if dp.get("value") is not None else dp.get("strValue", ""))
                        ts = dp.get("ts")
                        dt_str = datetime.fromtimestamp(ts / 1000.0).strftime('%Y-%m-%d %H:%M:%S') if ts else "Unknown"
                        parsed[key].append(f"{val} @ {dt_str}")
            elif isinstance(items, list):
                for i in items:
                    key = str(i.get("key") or i.get("kv", {}).get("key"))
                    val = str(i.get("strValue") or i.get("value") or i.get("kv", {}).get("strValue", ""))
                    ts = i.get("ts")
                    dt_str = datetime.fromtimestamp(ts / 1000.0).strftime('%Y-%m-%d %H:%M:%S') if ts else "Unknown"
                    if key not in parsed: parsed[key] = []
                    parsed[key].append(f"{val} @ {dt_str}")

            # Aggregated results handling
            if calculate:
                agg_results = {}
                for key, key_list in parsed.items():
                    values = []
                    for item in key_list:
                        try: values.append(float(item.split(" @ ")[0]))
                        except: continue
                    
                    if values:
                        calc = calculate.lower().strip()
                        res = (
                            min(values) if calc in ("min", "minimum", "lowest") else
                            max(values) if calc in ("max", "maximum", "highest") else
                            sum(values) if calc in ("sum", "total") else
                            len(values) if calc in ("count", "number of") else
                            sum(values) / len(values)
                        )
                        agg_results[key] = {
                            "result": round(res, 4),
                            "count": len(values),
                            "avg": round(sum(values)/len(values), 2) if values else 0
                        }

                if agg_results:
                    results[device_name] = {
                        "calculate": calculate,
                        "results_per_key": agg_results,
                        "note": "Calculated in Python from raw points" if not use_server_agg else "Calculated server-side"
                    }
            else:
                results[device_name] = {k: v[:fetch_limit] for k, v in parsed.items()}

            continue
        except Exception:
            continue

    if results:
        # Check if the returned data is old (older than 24h) and add a note if it is
        twenty_four_hours_ago = now_ts - (24 * 3600 * 1000)
        is_old_data = True
        
        for dev, data in results.items():
            if calculate:
                is_old_data = False # Hard to tell from aggregated result
                break
            else:
                for key, values in data.items():
                    for val_str in values:
                        try:
                            # Extract timestamp string and parse it back to check age
                            dt_str = val_str.split(" @ ")[1]
                            if dt_str != "Unknown":
                                dt_obj = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
                                if dt_obj.timestamp() * 1000 > twenty_four_hours_ago:
                                    is_old_data = False
                                    break
                        except:
                            pass
        
        final_str = json.dumps(results, indent=2)
        if is_old_data:
            final_str += "\n\nNote: The latest available data for these keys is older than 24 hours (e.g. from a previous year). These are the absolute most recent values stored in the database."
        return final_str
    else:
        # Fallback to the absolute most recent values if the requested range is empty
        calc_word = calculate if calculate else 'last 10 values'
        if hours > 0:
            time_range_desc = f"in the last {hours} hours"
        elif startTime:
            time_range_desc = f"for the requested date/time ({startTime})"
        else:
            time_range_desc = "for the requested period"
            
        msg = f"No telemetry data found for key: '{keys}' {time_range_desc}. The data is either older or non-existent in this window.\n\n"
        msg += f"Here is the '{calc_word}' of the absolute most recent values stored in the database instead:\n"
        
        # Recursive call with hours=0 and no startTime to fetch the absolute latest points
        # Guard: only fallback if we weren't already doing a full-history search
        if hours == 0 and not startTime:
            return f"No telemetry data found for key: '{keys}' in the entire database."

        fallback_res = getTimeseriesByName(entityName=entityName, keys=keys, limit=10, hours=0, calculate=calculate)
        return msg + fallback_res

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
                    if normalized_user in normalized_k:
                        # Exclude predicted/forecast keys unless explicitly requested
                        is_k_predicted = "predicted" in k.lower() or "forecast" in k.lower()
                        if not is_predicted and is_k_predicted:
                            continue
                        matched_keys.append(k)
                
                # SPECIAL HANDLING: If 'temperature' was asked, and we have both 'temperature' and 'temperature_celsius',
                # prioritize the 'celsius' one as per user request.
                if normalized_user == "temperature":
                    celsius_keys = [k for k in matched_keys if "celsius" in k.lower()]
                    if celsius_keys:
                        matched_keys = celsius_keys

                if not matched_keys:
                    continue
                fetch_keys = ",".join(matched_keys)
            else:
                # Proactively fetch ALL keys if none specified
                fetch_keys = ",".join(available_keys)

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