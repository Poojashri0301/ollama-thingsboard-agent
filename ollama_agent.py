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
    def __init__(self, model_name: str = None):
        self.model_name = model_name or OLLAMA_MODEL
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
                    "4. HISTORICAL & AGGREGATE: For 'min, max, avg, sum, count', 'historical', 'last 10 values', or questions with timeframes ('last 24 hours', 'last month'), ALWAYS use 'getTimeseriesByName'. You MUST pass the stat type (avg, min, max, sum) to the 'calculate' parameter for all statistics. "
                    "5. OLD DATA: If the tool returns dates from a previous year (like 2025), explicitly tell the user 'These are the most recent values available in the database, but they are from [Year].' Do not pretend they are recent."
                    "6. THERMOSTAT/TANKS: Technical data like forecast or dimensions are in 'SHARED_SCOPE'. "
                    "6. CHILDREN & RELATIONS: If asked for 'children' for a SPECIFIC entity, use 'getEntityChildren'. If asked for 'assets and their children' (BULK), ALWAYS use 'getAssetsWithChildren'. "
                    "7. NO TRIVIAL QUESTIONS: Do not ask 'Would you like to see X?' if you can just call a tool to show X. Never say 'It seems there was an issue' if the tool returned a valid JSON object. "
                    "7. LISTING: To list items (devices, users), use 'getTenantDevices' or 'getUsers'. "
                    "8. USER STATUS: Check the 'enabled' field for disabled users. "
                    "9. KEYS: Common IP keys are 'ipAddress', 'public_ip', 'private_ip'. Common dimension keys are 'Length(feet)', 'Width(feet)'. "
                    "10. TEMPERATURE/CELSIUS: When asked for 'temperature', ALWAYS prioritize keys containing 'celsius' (like 'temperature_celsius'). Show values ONLY in Celsius as they appear in ThingsBoard. NEVER convert to Fahrenheit. NEVER include 'predicted' or 'forecast' data unless explicitly asked. "
                    "11. CONCISENESS & ANS ALONE: Your responses MUST be extremely concise. For 'average temperature' or any numeric statistic, respond ONLY with the answer in a natural sentence, e.g., 'The average temperature is 25.5°C'. DO NOT include timestamps, device IDs, or technical metadata unless specifically asked for 'details' or 'history'. "
                    "You have 50+ local high-quality tools. Use them silently and proactively. If a question is plural, assume bulk."
                )
            }
        ]
        print(f"[Ollama] Agent ready with model: {self.model_name}")

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
        """Sync wrapper for legacy/CLI usage. Prints to stdout."""
        full_content = ""
        for chunk in self.ask_stream(question):
            print(chunk, end="", flush=True)
            full_content += chunk
        print() 
        return full_content

    def _manage_history(self, max_turns: int = 10):
        """
        Ensures the history doesn't exceed context limits.
        - Preserves the system prompt.
        - Keeps the last N turns (user + assistant/tool blocks).
        """
        if len(self.history) <= max_turns + 1:
            return
        
        system_prompt = self.history[0]
        recent_history = self.history[-(max_turns):]
        
        # Ensure we don't start with a 'tool' role without a previous assistant call
        # (Ollama/LLMs can be picky about the sequence)
        while recent_history and recent_history[0]["role"] == "tool":
            recent_history.pop(0)
            
        self.history = [system_prompt] + recent_history
        print(f"[Ollama] Managed history: {len(self.history)} messages retained.")

    def ask_stream(self, question: str):
        """Streaming version of ask. Yields chunks of text for API/UI usage."""
        # 1. Manage history before adding a new question
        self._manage_history()
        
        self.history.append({"role": "user", "content": question})

        max_iterations = 5
        for _ in range(max_iterations):
            payload = {
                "model": self.model_name,
                "messages": self.history,
                "tools": self.tools_schema,
                "stream": True,
                "options": {
                    "num_ctx": 8192,  # Substantially larger context window
                    "temperature": 0  # More stable for tool usage
                }
            }

            try:
                if not OLLAMA_BASE_URL:
                    yield "\n[Ollama Error] OLLAMA_BASE_URL is not configured. Please check your dynamic configuration endpoint."
                    return

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
                            content = msg_chunk.get('content')
                            if content:
                                full_content += content
                                yield content
                            
                            if 'tool_calls' in msg_chunk:
                                if not message_template:
                                    message_template = msg_chunk
                                else:
                                    if "tool_calls" not in message_template:
                                        message_template["tool_calls"] = []
                                    message_template["tool_calls"].extend(msg_chunk["tool_calls"])
                        if chunk.get('done'):
                            break

                # Add content to history if any
                if full_content:
                    self.history.append({"role": "assistant", "content": full_content})

                # Check for tool calls
                if message_template and message_template.get("tool_calls"):
                    # Record the assistant's intent to call tools
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
                                    # This shouldn't happen with the current setup but for safety:
                                    mcp_result = self.mcp.call_tool(func_name, func_args)
                                    try: result = mcp_result["result"]["content"][0]["text"]
                                    except: result = str(mcp_result)
                            except Exception as e:
                                result = f"Error executing tool '{func_name}': {e}"
                        else:
                            result = f"Tool {func_name} not found."
                        
                        # Truncate results to keep context manageable (8k)
                        # We use 8k here to leave room for the prompt and other turn data
                        if isinstance(result, str) and len(result) > 8000:
                            result = result[:8000] + "... [TRUNCATED]"

                        self.history.append({
                            "role": "tool",
                            "content": str(result),
                            "name": func_name
                        })
                    continue # Call Ollama again with tool results
                
                return # Done
                
            except Exception as e:
                yield f"\n[Ollama Error] {e}"
                return

        yield "\n[Error] Exceeded maximum tool call iterations."
