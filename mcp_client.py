# mcp_client.py
import json
import time
import threading
import requests
import sseclient
from urllib.parse import urlparse, parse_qs
from config import MCP_SERVER_URL

class MCPClient:
    def __init__(self):
        self.session_id = None
        self.messages = []
        self._connected = False
        self._connect()

    def _connect(self):
        self.session_id = None
        self._connected = False
        try:
            resp = requests.get(f"{MCP_SERVER_URL}/sse", stream=True)
            sse = sseclient.SSEClient(resp)
            threading.Thread(target=self._listen, args=(sse,), daemon=True).start()
            print("[MCP] Connecting...")
        except Exception as e:
            print(f"[MCP] Connection error: {e}. Retrying in 5s...")
            time.sleep(5)
            self._connect()

    def _listen(self, sse):
        try:
            for event in sse.events():
                if event.event == "endpoint" and event.data:
                    parsed = urlparse(event.data)
                    qs = parse_qs(parsed.query)
                    if "sessionId" in qs:
                        self.session_id = qs["sessionId"][0]
                    elif "session_id" in qs:
                        self.session_id = qs["session_id"][0]
                    self._connected = True
                    print(f"[MCP] Connected. Session ID: {self.session_id}")
                    threading.Thread(target=self._initialize, daemon=True).start()
                elif event.data:
                    try:
                        self.messages.append(json.loads(event.data))
                    except:
                        pass
        except Exception as e:
            print(f"[MCP] Connection dropped: {e}. Reconnecting in 3s...")
            self._connected = False
            time.sleep(3)
            self._connect()  # auto reconnect

    def _initialize(self):
        time.sleep(0.5)
        self._post({
            "jsonrpc": "2.0", "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "gemini-agent", "version": "1.0"}
            }
        })
        time.sleep(1)
        self._post({
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        })
        print("[MCP] Handshake complete!")

    def _post(self, payload):
        url = f"{MCP_SERVER_URL}/mcp/message?sessionId={self.session_id}"
        try:
            requests.post(
                url,
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload),
                timeout=15
            )
        except Exception as e:
            print(f"[MCP] POST error: {e}")

    def _wait_session(self):
        start = time.time()
        while not self.session_id or not self._connected:
            if time.time() - start > 15:
                raise RuntimeError("MCP session timeout")
            time.sleep(0.1)

    def call_tool(self, tool_name: str, arguments: dict):
        self._wait_session()
        before = len(self.messages)
        self._post({
            "jsonrpc": "2.0",
            "id": int(time.time()),
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments}
        })
        start = time.time()
        while len(self.messages) == before:
            if time.time() - start > 15:
                raise TimeoutError(f"No response for tool: {tool_name}")
            time.sleep(0.1)
        return self.messages[-1]

    def list_tools(self):
        self._wait_session()
        before = len(self.messages)
        self._post({
            "jsonrpc": "2.0",
            "id": int(time.time()),
            "method": "tools/list",
            "params": {}
        })
        start = time.time()
        while len(self.messages) == before:
            if time.time() - start > 10:
                raise TimeoutError("No response for tools/list")
            time.sleep(0.1)
        return self.messages[-1]