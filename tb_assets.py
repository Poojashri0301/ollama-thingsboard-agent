# tb_asset.py
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

# Get all assets from ThingsBoard tenant
def getTenantAssets(pageSize: int = 100, max_pages: int = 10) -> str:
    """
    Get a summary list of all assets in the tenant.
    Returns: Name, ID, Type, Label.
    Use when user asks to list all assets OR asks how many assets there are.
    """
    all_data = []
    page = 0
    while page < max_pages:
        raw = _extract(mcp.call_tool("getTenantAssets", {"pageSize": int(pageSize), "page": int(page)}))
        data = json.loads(raw)
        
        # Summarize
        for a in data.get("data", []):
            all_data.append({
                "name": a.get("name"),
                "id": a.get("id", {}).get("id"),
                "type": a.get("type"),
                "label": a.get("label")
            })

        if not data.get("hasNext", False):
            break
        page += 1
    return json.dumps({"assets": all_data, "count": len(all_data), "truncated": page == max_pages}, indent=2, ensure_ascii=False)

# Get a specific asset by its ID.
def getAssetById(assetId: str) -> str:
    """Get an asset by its ID. Use when user provides a specific asset ID."""

    result = mcp.call_tool("getAssetById", {"assetId": assetId})
    return _extract(result)

# Get an asset by its name.
def getTenantAsset(assetName: str) -> str:
    """Get a single tenant asset by name. Use when user asks for a specific asset."""

    result = mcp.call_tool("getTenantAsset", {"assetName": assetName})
    return _extract(result)

# Get all assets assigned to a specific customer.
def getCustomerAssets(customerId: str, pageSize: str = "100", type: str = "", textSearch: str = "", sortProperty: str = "", sortOrder: str = "", max_pages: int = 10) -> str:
    """Get assets belonging to a customer. Use when user asks for assets of a specific customer."""
    all_data = []
    page = 0
    while page < max_pages:
        args = {"customerId": customerId, "pageSize": int(pageSize), "page": page}
        if type: args["type"] = type
        if textSearch: args["textSearch"] = textSearch
        if sortProperty: args["sortProperty"] = sortProperty
        if sortOrder: args["sortOrder"] = sortOrder
        data = json.loads(_extract(mcp.call_tool("getCustomerAssets", args)))
        all_data.extend(data.get("data", []))
        if not data.get("hasNext", False):
            break
        page += 1
    return json.dumps({"data": all_data, "truncated": page == max_pages}, indent=2, ensure_ascii=False)

# Get all assets assigned to a specific user.
def getUserAssets(userId: str, pageSize: str = "100", type: str = "", textSearch: str = "", sortProperty: str = "", sortOrder: str = "") -> str:
    """Get assets belonging to a user. Use when user asks for assets of a specific user."""
    all_data = []
    page = 0
    max_pages = 10
    while page < max_pages:
        args = {"userId": userId, "pageSize": int(pageSize), "page": page}
        if type: args["type"] = type
        if textSearch: args["textSearch"] = textSearch
        if sortProperty: args["sortProperty"] = sortProperty
        if sortOrder: args["sortOrder"] = sortOrder
        data = json.loads(_extract(mcp.call_tool("getUserAssets", args)))
        all_data.extend(data.get("data", []))
        if not data.get("hasNext", False):
            break
        page += 1
    return json.dumps({"data": all_data}, indent=2, ensure_ascii=False)


# Get detailed info of all assets assigned to a specific customer.
def getCustomerAssetInfos(customerId: str, pageSize: str = "100", type: str = "", assetProfileId: str = "", textSearch: str = "", sortProperty: str = "", sortOrder: str = "") -> str:
    all_data = []
    page = 0
    max_pages = 10
    while page < max_pages:
        args = {"customerId": customerId, "pageSize": int(pageSize), "page": page}
        if type: args["type"] = type
        if assetProfileId: args["assetProfileId"] = assetProfileId
        if textSearch: args["textSearch"] = textSearch
        if sortProperty: args["sortProperty"] = sortProperty
        if sortOrder: args["sortOrder"] = sortOrder
        data = json.loads(_extract(mcp.call_tool("getCustomerAssetInfos", args)))
        all_data.extend(data.get("data", []))
        if not data.get("hasNext", False):
            break
        page += 1
    return json.dumps({"data": all_data}, indent=2, ensure_ascii=False)

#  Get all assets with extra details like customer name and asset profile.
def getTenantAssetInfos(pageSize: str = "100", type: str = "", assetProfileId: str = "", textSearch: str = "", sortProperty: str = "", sortOrder: str = "") -> str:
    all_data = []
    page = 0
    max_pages = 10
    while page < max_pages:
        args = {"pageSize": int(pageSize), "page": page}
        if type: args["type"] = type
        if assetProfileId: args["assetProfileId"] = assetProfileId
        if textSearch: args["textSearch"] = textSearch
        if sortProperty: args["sortProperty"] = sortProperty
        if sortOrder: args["sortOrder"] = sortOrder
        data = json.loads(_extract(mcp.call_tool("getTenantAssetInfos", args)))
        all_data.extend(data.get("data", []))
        if not data.get("hasNext", False):
            break
        page += 1
    return json.dumps({"data": all_data}, indent=2, ensure_ascii=False)

# Get multiple assets at once using comma separated IDs.
def getAssetsByIds(assetIds: str) -> str:
    
    result = mcp.call_tool("getAssetsByIds", {"assetIds": assetIds})
    return _extract(result)

# Get all assets that belong to a specific entity group.
def getAssetsByEntityGroupId(entityGroupId: str, pageSize: str = "100", sortProperty: str = "", sortOrder: str = "") -> str:
    all_data = []
    page = 0
    max_pages = 10
    while page < max_pages:
        args = {"entityGroupId": entityGroupId, "pageSize": int(pageSize), "page": page}
        if sortProperty: args["sortProperty"] = sortProperty
        if sortOrder: args["sortOrder"] = sortOrder
        data = json.loads(_extract(mcp.call_tool("getAssetsByEntityGroupId", args)))
        all_data.extend(data.get("data", []))
        if not data.get("hasNext", False):
            break
        page += 1
    return json.dumps({"data": all_data}, indent=2, ensure_ascii=False)
