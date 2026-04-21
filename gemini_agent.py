# gemini_agent.py
import time
from google import genai
from google.genai import types
from google.genai import errors
from config import GEMINI_API_KEY
from mcp_client import MCPClient

import tb_device
import tb_telemetry
import tb_attributes
import tb_assets
import tb_customer
import tb_user

gemini_client = genai.Client(api_key=GEMINI_API_KEY)
def _clean_history(self, history):
    """Remove any messages with empty or invalid parts."""
    clean = []
    for msg in history:
        if not msg:
            continue
        parts = msg.get("parts", [])
        # Filter out empty parts
        valid_parts = [p for p in parts if p and (p.get("text") or p.get("function_call") or p.get("function_response"))]
        if valid_parts:
            msg["parts"] = valid_parts
            clean.append(msg)
    return clean
class GeminiTBAgent:
    def __init__(self):
        # Start MCP client
        mcp = MCPClient()
        time.sleep(2)

        # Give MCP client to all TB modules
        tb_device.set_mcp_client(mcp)
        tb_telemetry.set_mcp_client(mcp)
        tb_attributes.set_mcp_client(mcp)
        tb_assets.set_mcp_client(mcp)
        tb_customer.set_mcp_client(mcp)
        tb_user.set_mcp_client(mcp)
        # tb_relation.set_mcp_client(mcp)
        # tb_alarm.set_mcp_client(mcp)

        # Register all tools for Gemini
        self.tools = [
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
            # tb_telemetry.getAggregateFromTimeseries,
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
            # # Relation
            # tb_relation.findByFrom,
            # tb_relation.findByTo,
            # # Alarm
            # tb_alarm.ackAlarm,
        ]

        self.history = []
        self.system_prompt = (
            "You are a ThingsBoard Assistant. You MUST use tools for all operations. "
            "1. BE DIRECT: Execute tools immediately. "
            "2. CELSIUS ONLY: When asked for 'temperature', ALWAYS prioritize keys containing 'celsius'. Report values exactly as provided by ThingsBoard in Celsius. NEVER convert to Fahrenheit. "
            "3. HISTORICAL & AGGREGATE: For 'min, max, avg, sum', or questions with timeframes, ALWAYS use 'getTimeseriesByName'. It handles relative time like 'this week' automatically. "
            "4. NO fillers: Be extremely concise. "
        )
        print("[Gemini] Agent ready!")

    def ask(self, question: str):
        print(f"\n[You] {question}")

        self.history.append(
            types.Content(role="user", parts=[types.Part(text=question)])
        )

        for attempt in range(3):
            try:
                response = gemini_client.models.generate_content(
                    model="models/gemini-2.5-flash",
                    contents=self.history,
                    config=types.GenerateContentConfig(
                        system_instruction=self.system_prompt,
                        tools=self.tools,
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(
                            disable=False
                        )
                    )
                )
                answer = response.text
                print(f"[Gemini] {answer}")
                self.history.append(
                    types.Content(role="model", parts=[types.Part(text=answer)])
                )
                return answer

            except errors.ClientError as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    wait = 30 * (attempt + 1)
                    print(f"[Quota] Rate limit hit. Waiting {wait}s before retry {attempt+1}/3...")
                    time.sleep(wait)
                else:
                    print(f"[Error] {e}")
                    return "Sorry, an error occurred."

        return "Quota limit reached. Please wait a few minutes and try again."