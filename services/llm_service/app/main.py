import os
import asyncio
from typing import AsyncGenerator, Optional

from fastapi import FastAPI
from pydantic import BaseModel
from starlette.responses import StreamingResponse

app = FastAPI(title="llm-service")

class ChatIn(BaseModel):
    prompt: str
    session_id: Optional[str] = None

def sse(data: str, event: str = "message") -> str:
    # SSE format: event + data + blank line
    data = data.replace("\r", "")
    return f"event: {event}\ndata: {data}\n\n"

async def fake_token_stream(prompt: str) -> AsyncGenerator[str, None]:
    # fallback if no API key configured
    text = f"Echo (fake LLM): {prompt}"
    for ch in text:
        yield ch
        await asyncio.sleep(0.01)

async def langchain_token_stream(prompt: str) -> AsyncGenerator[str, None]:
    """
    Streams tokens using LangChain.
    Requires: OPENAI_API_KEY and langchain-openai installed.
    """
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate

    # Streaming tokens via .astream
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.2,
        streaming=True,
    )

    prompt_t = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant. Answer concisely."),
        ("human", "{q}"),
    ])

    chain = prompt_t | llm

    async for chunk in chain.astream({"q": prompt}):
        # chunk is an AIMessageChunk; chunk.content can be partial token(s)
        token = getattr(chunk, "content", "")
        if token:
            yield token

@app.post("/chat")
async def chat(body: ChatIn):
    async def event_gen() -> AsyncGenerator[bytes, None]:
        api_key = os.getenv("OPENAI_API_KEY")
        stream = langchain_token_stream(body.prompt) if api_key else fake_token_stream(body.prompt)

        yield sse("started", event="status").encode("utf-8")
        try:
            async for token in stream:
                yield sse(token, event="token").encode("utf-8")
            yield sse("done", event="status").encode("utf-8")
        except Exception as e:
            yield sse(f"error: {type(e).__name__}: {e}", event="error").encode("utf-8")

    return StreamingResponse(event_gen(), media_type="text/event-stream")
