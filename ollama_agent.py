# ollama_agent.py
import json
import time
import requests
import inspect
from typing import get_type_hints
from config import OLLAMA_BASE_URL, OLLAMA_MODEL
from mcp_client import MCPClient

import tb_device
import tb_telemetry
import tb_attributes
import tb_assets
import tb_customer
import tb_user

class OllamaTBAgent:
    def __init__(self):
        # Start MCP client
        self.mcp = MCPClient()
        time.sleep(2)

        # Give MCP client to all TB modules
        tb_device.set_mcp_client(self.mcp)
        tb_telemetry.set_mcp_client(self.mcp)
        tb_attributes.set_mcp_client(self.mcp)
        tb_assets.set_mcp_client(self.mcp)
        tb_customer.set_mcp_client(self.mcp)
        tb_user.set_mcp_client(self.mcp)

        # Register comprehensive local tools (high quality wrappers)
        self.local_tools = [
            # Device
            tb_device.getTenantDevices,
            tb_device.getDeviceById,
            tb_device.getTenantDevice,
            tb_device.getDeviceInfo,
            tb_device.getTenantDeviceInfos,
            tb_device.getDevicesByIds,
            tb_device.getCustomerDevices,
            tb_device.getCustomerDeviceInfos,
            tb_device.getDevicesByEntityGroupId,
            tb_device.getDeviceByName,
            tb_device.getDevicesByUserName,
            # Telemetry
            tb_telemetry.getLatestTimeseries,
            tb_telemetry.getTimeseriesKeys,
            tb_telemetry.getTimeseries,
            tb_telemetry.getLatestTimeseriesByName,
            tb_telemetry.getTimeseriesByName,
            # Attributes
            tb_attributes.getAttributes,
            tb_attributes.getAttributeKeysByScope,
            tb_attributes.getAttributeKeys,
            tb_attributes.getAttributesByScope,
            tb_attributes.getUserAttributes,
            tb_attributes.getUserAttributesByName,
            tb_attributes.getDeviceAttributesByName,
            tb_attributes.getActiveDevices,
            # Asset
            tb_assets.getTenantAssets,
            tb_assets.getAssetById,
            tb_assets.getTenantAsset,
            tb_assets.getUserAssets,
            tb_assets.getCustomerAssets,
            # Customer
            tb_customer.getCustomers,
            tb_customer.getCustomerById,
            tb_customer.findCustomerByName,
            tb_customer.getCustomersByEntityGroupId,
            # users
            tb_user.getUserById,
            tb_user.getUsers,
            tb_user.getTenantAdmins,
            tb_user.getCustomerUsers,
            tb_user.getAllCustomerUsers,
            tb_user.getUsersForAssign,
            tb_user.getUsersByEntityGroupId,
            tb_user.findUserByName
        ]

        # 1. Start with local tool mapping
        self.available_tools = {f.__name__: f for f in self.local_tools}
        self.tools_schema = [self._generate_tool_schema(f) for f in self.local_tools]
        
        # 2. Add remaining MCP tools dynamically
        try:
            print("[Ollama] Fetching all MCP tools...")
            mcp_tools_resp = self.mcp.list_tools()
            mcp_tools = mcp_tools_resp.get("result", {}).get("tools", [])
            
            added_count = 0
            for tool in mcp_tools:
                name = tool.get("name")
                if name not in self.available_tools:
                    # Register raw MCP tool
                    self.available_tools[name] = {"type": "mcp", "tool": tool}
                    self.tools_schema.append({
                        "type": "function",
                        "function": {
                            "name": name,
                            "description": tool.get("description", "No description"),
                            "parameters": tool.get("inputSchema", {"type": "object", "properties": {}})
                        }
                    })
                    added_count += 1
            print(f"[Ollama] Registered {len(self.tools_schema)} total tools ({added_count} dynamic).")
        except Exception as e:
            print(f"[Ollama] Error fetching dynamic tools: {e}")
        
        self.history = [
            {
                "role": "system",
                "content": (
                    "You are a ThingsBoard Assistant. You MUST use tools for all operations. "
                    "1. To find a DEVICE by name, use 'getDeviceByName'. "
                    "2. To find a USER by name/email, use 'findUserByName'. "
                    "3. For technical specs of a device (ID, type, etc.), use 'getDeviceInfo'. "
                    "4. For current data/telemetry (CRT details), ALWAYS use 'getLatestTimeseriesByName'. "
                    "If a user asks for 'details', fetch both technical info and current telemetry/attributes. "
                    "Be professional and do not hallucinate data."
                )
            }
        ]
        print(f"[Ollama] Agent ready with model: {OLLAMA_MODEL}")

    def _generate_tool_schema(self, func):
        """Generates robust Ollama-compatible JSON schema with full docstrings."""
        sig = inspect.signature(func)
        doc = str(func.__doc__ or "No description provided.")
        
        properties = {}
        required = []
        
        for name, param in sig.parameters.items():
            param_type = "string"
            if param.annotation == int: param_type = "integer"
            elif param.annotation == float: param_type = "number"
            elif param.annotation == bool: param_type = "boolean"

            # Try to extract parameter description from docstring
            desc = f"Parameter {name}"
            for line in doc.split("\n"):
                if f"{name}" in line and (":" in line or "-" in line):
                    desc = line.strip()
                    break

            properties[name] = {
                "type": param_type,
                "description": desc
            }
            
            if param.default is inspect.Parameter.empty:
                required.append(name)
        
        return {
            "type": "function",
            "function": {
                "name": func.__name__,
                "description": doc, # Use full docstring for maximal context
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }

    def ask(self, question: str):
        print(f"\n[You] {question}")
        self.history.append({"role": "user", "content": question})

        max_iterations = 5
        for _ in range(max_iterations):
            payload = {
                "model": OLLAMA_MODEL,
                "messages": self.history,
                "tools": self.tools_schema,
                "stream": False
            }

            try:
                # Use longer timeout (600s) for robust local LLM execution
                response = requests.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload, timeout=600)
                response.raise_for_status()
                data = response.json()
                message = data.get("message", {})
                
                self.history.append(message)

                if message.get("tool_calls"):
                    for tool_call in message["tool_calls"]:
                        func_name = tool_call["function"]["name"]
                        func_args = tool_call["function"]["arguments"]
                        
                        if func_name in self.available_tools:
                            tool_entry = self.available_tools[func_name]
                            try:
                                if callable(tool_entry):
                                    # Call local Python wrapper
                                    result = tool_entry(**func_args)
                                else:
                                    # Call raw MCP tool
                                    print(f"[Ollama] Calling dynamic MCP tool: {func_name}")
                                    mcp_result = self.mcp.call_tool(func_name, func_args)
                                    try:
                                        result = mcp_result["result"]["content"][0]["text"]
                                    except (KeyError, IndexError):
                                        result = str(mcp_result)
                            except Exception as e:
                                result = f"Error executing tool '{func_name}': {e}"
                        else:
                            result = f"Tool {func_name} not found."
                        
                        self.history.append({
                            "role": "tool",
                            "content": str(result),
                            "name": func_name
                        })
                    continue # Call Ollama again with tool results
                
                answer = message.get("content", "")
                print(f"[Ollama] {answer}")
                return answer

            except Exception as e:
                print(f"[Ollama Error] {e}")
                return "Sorry, I encountered an error with Ollama."

        return "Exceeded maximum tool call iterations."
