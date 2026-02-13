import os
from typing import AsyncGenerator

import httpx
from fastapi import FastAPI, Query
from starlette.responses import StreamingResponse

app = FastAPI(title="sse-gateway")

LLM_URL = os.getenv("LLM_URL", "http://llm-service:8001")

def passthrough(chunk: bytes) -> bytes:
    return chunk

@app.get("/stream")
async def stream(prompt: str = Query(..., min_length=1)):
    """
    Exponha SSE ao cliente e repasse o SSE do llm-service.
    """
    async def event_gen() -> AsyncGenerator[bytes, None]:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{LLM_URL}/chat",
                json={"prompt": prompt},
                headers={"Accept": "text/event-stream"},
            ) as resp:
                resp.raise_for_status()
                async for chunk in resp.aiter_bytes():
                    if chunk:
                        yield passthrough(chunk)

    return StreamingResponse(event_gen(), media_type="text/event-stream")
