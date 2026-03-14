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
            tb_device.getDeviceFullDetails,
            # Telemetry
            tb_telemetry.getTimeseriesKeys,
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
            tb_attributes.getDevicesConnectionStatus,
            tb_attributes.getDevicesAttributes,
            # Asset
            tb_assets.getTenantAssets,
            tb_assets.getAssetById,
            tb_assets.getTenantAsset,
            tb_assets.getUserAssets,
            tb_assets.getCustomerAssets,
            tb_assets.getCustomerAssetInfos,
            tb_assets.getTenantAssetInfos,
            tb_assets.getAssetsByIds,
            tb_assets.getAssetsByEntityGroupId,
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
            tb_user.findUserByName,
            tb_user.getUserFullDetails
        ]

        # 1. Start with local tool mapping
        self.available_tools = {f.__name__: f for f in self.local_tools}
        self.tools_schema = [self._generate_tool_schema(f) for f in self.local_tools]
        
        # 2. Skip dynamic MCP tools as per user request to use only local high-quality wrappers
        print(f"[Ollama] Registered {len(self.tools_schema)} total local tools. Dynamic MCP tools disabled.")
        
        self.history = [
            {
                "role": "system",
                "content": (
                    "You are a ThingsBoard Assistant. You MUST use tools for all operations. "
                    "1. BE DIRECT: Execute tools immediately. NEVER say 'I will use tool X' or 'Let's try Y'. Just call the tool and show the result. "
                    "2. BULK PROACTIVITY: If asked general questions like 'what are the public IPs', 'what is the software version', or 'what are the custom attributes', NEVER ask 'which device?'. Instead, use 'getDevicesAttributes' with the likely keys (e.g., 'ipAddress, public_ip', or just 'custom' if asking for all custom attributes). "
                    "3. BULK STATUS: For status, connection times, or forecast times for MULTIPLE or 'VARIOUS' devices, ALWAYS use 'getDevicesConnectionStatus'. "
                    "4. HISTORICAL & AGGREGATE: For 'min, max, avg, sum, count', 'historical', 'last 10 values', or questions with timeframes ('last 24 hours', 'last month'), ALWAYS use 'getTimeseriesByName'. It calculates aggregates across devices for the time range automatically, or simply fetches the last N values if no calculation is specified. "
                    "5. OLD DATA: If the tool returns dates from a previous year (like 2025), explicitly tell the user 'These are the most recent values available in the database, but they are from [Year].' Do not pretend they are recent."
                    "6. THERMOSTAT/TANKS: Technical data like forecast or dimensions are in 'SHARED_SCOPE'. "
                    "6. CHILDREN & RELATIONS: If asked for 'children' for a SPECIFIC entity, use 'getEntityChildren'. If asked for 'assets and their children' (BULK), ALWAYS use 'getAssetsWithChildren'. "
                    "7. NO TRIVIAL QUESTIONS: Do not ask 'Would you like to see X?' if you can just call a tool to show X. Never say 'It seems there was an issue' if the tool returned a valid JSON object. "
                    "7. LISTING: To list items (devices, users), use 'getTenantDevices' or 'getUsers'. "
                    "8. USER STATUS: Check the 'enabled' field for disabled users. "
                    "9. KEYS: Common IP keys are 'ipAddress', 'public_ip', 'private_ip'. Common dimension keys are 'Length(feet)', 'Width(feet)'. "
                    "You have 50+ local high-quality tools. Use them silently and proactively. If a question is plural, assume bulk."
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
                "stream": True
            }

            try:
                # Use longer timeout (600s) and streaming for better UX
                print("[Ollama] Thinking...", end="", flush=True)
                response = requests.post(
                    f"{OLLAMA_BASE_URL}/api/chat", 
                    json=payload, 
                    timeout=600,
                    stream=True
                )
                response.raise_for_status()
                
                full_content = ""
                message_template = None

                for line in response.iter_lines():
                    if line:
                        chunk = json.loads(line.decode('utf-8'))
                        if 'message' in chunk:
                            msg_chunk = chunk['message']
                            if 'content' in msg_chunk:
                                content = msg_chunk['content']
                                full_content += content
                                print(content, end="", flush=True)
                            if 'tool_calls' in msg_chunk:
                                if not message_template:
                                    message_template = msg_chunk
                                else:
                                    # Handle tool call chunks if necessary
                                    pass
                        if chunk.get('done'):
                            break

                print() # New line after response
                
                # Add content to history if any
                if full_content:
                    self.history.append({"role": "assistant", "content": full_content})

                # Check for tool calls
                if message_template and message_template.get("tool_calls"):
                    # Only append the tool call message if it hasn't been added yet (it shouldn't be)
                    self.history.append(message_template)
                    
                    for tool_call in message_template["tool_calls"]:
                        func_name = tool_call["function"]["name"]
                        func_args = tool_call["function"]["arguments"]
                        
                        if func_name in self.available_tools:
                            tool_entry = self.available_tools[func_name]
                            try:
                                if callable(tool_entry):
                                    result = tool_entry(**func_args)
                                else:
                                    mcp_result = self.mcp.call_tool(func_name, func_args)
                                    try:
                                        result = mcp_result["result"]["content"][0]["text"]
                                    except (KeyError, IndexError):
                                        result = str(mcp_result)
                            except Exception as e:
                                result = f"Error executing tool '{func_name}': {e}"
                        else:
                            result = f"Tool {func_name} not found."
                        
                        # Truncate results to keep context manageable (15k)
                        if isinstance(result, str) and len(result) > 15000:
                            result = result[:15000] + "... [TRUNCATED - Too much data, please ask for specific parts if missing]"

                        self.history.append({
                            "role": "tool",
                            "content": str(result),
                            "name": func_name
                        })
                    continue # Call Ollama again with tool results
                
                if full_content:
                    return full_content
                
                return "Received empty response from Ollama."

            except Exception as e:
                print(f"\n[Ollama Error] {e}")
                return "Sorry, I encountered an error with Ollama."

        return "Exceeded maximum tool call iterations."
