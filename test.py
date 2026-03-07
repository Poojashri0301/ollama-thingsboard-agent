from mcp_client import MCPClient
from tb_telemetry import set_mcp_client, _extract
import time
import json

mcp = MCPClient()
time.sleep(2)
set_mcp_client(mcp)

device_id = "c3a39ce0-edc3-11ef-be0d-3325fdfc55bf"

print("\n=== getLatestTimeseries ===")
raw = mcp.call_tool("getLatestTimeseries", {
    "entityType": "DEVICE",
    "entityIdStr": device_id,
    "keys": "temperature,humidity"
})
print(_extract(raw))

print("\n=== getTimeseries with startTs=0 (all time) ===")
raw2 = mcp.call_tool("getTimeseries", {
    "entityType": "DEVICE",
    "entityIdStr": device_id,
    "keys": "temperature",
    "startTs": 0,
    "endTs": int(time.time() * 1000),
    "limit": 10
})
print(_extract(raw2))