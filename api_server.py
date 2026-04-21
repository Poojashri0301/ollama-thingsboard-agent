# api_server.py
import uvicorn
import json
import asyncio
from fastapi import FastAPI, Header, HTTPException, Body, Depends
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from auth_service import check_token_status
from ollama_agent import OllamaTBAgent
from config import AGENT_TYPE

app = FastAPI(title="ThingsBoard MCP Agent API")
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent instance or per-session? 
# For now, let's stick to the ThingsBoard pattern where the agent is initialized once.
# If you need multi-user conversation state, we would move this into a session manager.
if AGENT_TYPE == "ollama":
    agent = OllamaTBAgent()
else:
    from gemini_agent import GeminiTBAgent
    agent = GeminiTBAgent()

async def get_token(authorization: str = Header(None), x_authorization: str = Header(None)):
    auth_header = authorization or x_authorization
    
    if not auth_header:
        print("[Auth Error] Authorization header missing")
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    # print(f"[Auth] Received Authorization header: {auth_header[:30]}...")
    
    parts = auth_header.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        token = parts[1]
    else:
        # Fallback for raw token if no Bearer prefix
        token = auth_header
    
    if not check_token_status(token):
        # logging is already in check_token_status
        raise HTTPException(status_code=401, detail="Invalid ThingsBoard token")
    
    return token

@app.post("/api/chat")
async def chat_stream(
    question: str = Body(..., embed=True),
    token: str = Depends(get_token)
):
    """
    Standard streaming chat endpoint.
    Returns a Server-Sent Events (SSE) stream for the UI.
    """
    async def event_generator():
        loop = asyncio.get_event_loop()
        gen = agent.ask_stream(question)
        full_content = ""
        
        def safe_next(g):
            try:
                return next(g)
            except StopIteration:
                return None

        while True:
            chunk = await loop.run_in_executor(None, safe_next, gen)
            if chunk is not None:
                full_content += chunk
                # Yield a progressive full-text chunk
                yield {"data": json.dumps({"content": full_content})}
            else:
                yield {"data": "[DONE]"}
                break

    return EventSourceResponse(event_generator(), ping=15)

@app.post("/api/chat/sync")
async def chat_sync(
    question: str = Body(..., embed=True),
    token: str = Depends(get_token)
):
    """
    Standard synchronous chat endpoint.
    Returns the full response as a JSON object after completion.
    """
    loop = asyncio.get_event_loop()
    try:
        # Run the synchronous ask call in a separate thread
        response_text = await loop.run_in_executor(None, agent.ask, question)
        from fastapi.responses import JSONResponse
        return JSONResponse(
            content={"content": response_text},
            headers={"Content-Type": "application/json; charset=utf-8"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health():
    return {"status": "ok", "agent": AGENT_TYPE}

def get_local_ip():
    """Finds the primary local network IP address."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

if __name__ == "__main__":
    local_ip = get_local_ip()
    print("\n" + "="*50)
    print("🚀 Pilti AI Agent - Enterprise API Server")
    print("="*50)
    print(f"📡 API URL:      http://{local_ip}:8000")
    print(f"🏥 Health Check: http://{local_ip}:8000/api/health")
    print(f"🤖 Agent Type:   {AGENT_TYPE.upper()}")
    print("="*50 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
