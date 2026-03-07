# tb_asset.py
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

# Get all assets from ThingsBoard tenant
def getTenantAssets(pageSize: str = "20", page: str = "0") -> str:
    """
    Get all assets in the tenant.
    Use when user asks to list all assets OR asks how many assets there are.
    The response includes 'totalElements' which gives the exact total count.
    Examples:
    - 'list all assets'
    - 'how many assets are there' -> read totalElements from response
    - 'total number of assets' -> read totalElements from response
    """
    result = mcp.call_tool("getTenantAssets", {"pageSize": pageSize, "page": page})
    return _extract(result)

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
def getCustomerAssets(customerId: str, pageSize: str = "20", page: str = "0", type: str = "", textSearch: str = "", sortProperty: str = "", sortOrder: str = "") -> str:
    """Get assets belonging to a customer. Use when user asks for assets of a specific customer."""
    args = {"customerId": customerId, "pageSize": pageSize, "page": page}
    if type:
        args["type"] = type
    if textSearch:
        args["textSearch"] = textSearch
    if sortProperty:
        args["sortProperty"] = sortProperty
    if sortOrder:
        args["sortOrder"] = sortOrder
    result = mcp.call_tool("getCustomerAssets", args)
    return _extract(result)

# Get all assets assigned to a specific user.
def getUserAssets(userId: str, pageSize: str = "20", page: str = "0", type: str = "", textSearch: str = "", sortProperty: str = "", sortOrder: str = "") -> str:
    """Get assets belonging to a user. Use when user asks for assets of a specific user."""
    args = {"userId": userId, "pageSize": pageSize, "page": page}
    if type:
        args["type"] = type
    if textSearch:
        args["textSearch"] = textSearch
    if sortProperty:
        args["sortProperty"] = sortProperty
    if sortOrder:
        args["sortOrder"] = sortOrder
    result = mcp.call_tool("getUserAssets", args)
    return _extract(result)


# Get detailed info of all assets assigned to a specific customer.
def getCustomerAssetInfos(customerId: str, pageSize: str = "20", page: str = "0", type: str = "", assetProfileId: str = "", textSearch: str = "", sortProperty: str = "", sortOrder: str = "") -> str:
    
    args = {"customerId": customerId, "pageSize": pageSize, "page": page}
    if type:
        args["type"] = type
    if assetProfileId:
        args["assetProfileId"] = assetProfileId
    if textSearch:
        args["textSearch"] = textSearch
    if sortProperty:
        args["sortProperty"] = sortProperty
    if sortOrder:
        args["sortOrder"] = sortOrder
    result = mcp.call_tool("getCustomerAssetInfos", args)
    return _extract(result)

#  Get all assets with extra details like customer name and asset profile.
def getTenantAssetInfos(pageSize: str = "20", page: str = "0", type: str = "", assetProfileId: str = "", textSearch: str = "", sortProperty: str = "", sortOrder: str = "") -> str:
    
    args = {"pageSize": pageSize, "page": page}
    if type:
        args["type"] = type
    if assetProfileId:
        args["assetProfileId"] = assetProfileId
    if textSearch:
        args["textSearch"] = textSearch
    if sortProperty:
        args["sortProperty"] = sortProperty
    if sortOrder:
        args["sortOrder"] = sortOrder
    result = mcp.call_tool("getTenantAssetInfos", args)
    return _extract(result)

# Get multiple assets at once using comma separated IDs.
def getAssetsByIds(assetIds: str) -> str:
    
    result = mcp.call_tool("getAssetsByIds", {"assetIds": assetIds})
    return _extract(result)

# Get all assets that belong to a specific entity group.
def getAssetsByEntityGroupId(entityGroupId: str, pageSize: str = "20", page: str = "0", sortProperty: str = "", sortOrder: str = "") -> str:
   
    args = {"entityGroupId": entityGroupId, "pageSize": pageSize, "page": page}
    if sortProperty:
        args["sortProperty"] = sortProperty
    if sortOrder:
        args["sortOrder"] = sortOrder
    result = mcp.call_tool("getAssetsByEntityGroupId", args)
    return _extract(result)
