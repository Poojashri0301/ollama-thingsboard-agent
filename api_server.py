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
    Streaming chat endpoint. 
    Accepts a question and streams back the assistant's response via SSE.
    """
    async def event_generator():
        # Running the synchronous generator in a thread to not block the event loop
        loop = asyncio.get_event_loop()
        gen = agent.ask_stream(question)
        
        def safe_next(g):
            try:
                return next(g)
            except StopIteration:
                return None

        while True:
            try:
                # Run the safe helper in a separate thread
                chunk = await loop.run_in_executor(None, safe_next, gen)
                if chunk is not None:
                    yield {
                        "event": "message",
                        "data": json.dumps({"content": chunk})
                    }
                else:
                    # End of stream
                    yield {
                        "event": "done",
                        "data": "[DONE]"
                    }
                    break
            except Exception as e:
                yield {
                    "event": "error",
                    "data": json.dumps({"detail": str(e)})
                }
                break

    return EventSourceResponse(event_generator())

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
        return {"content": response_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health():
    return {"status": "ok", "agent": AGENT_TYPE}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
