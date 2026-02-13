import os
import requests
import streamlit as st

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://sse-gateway:8000")

st.set_page_config(page_title="SSE + LangChain", layout="centered")
st.title("SSE + LangChain (microservices)")

prompt = st.text_input("Prompt", value="Explique SSE em 2 frases.")
run = st.button("Enviar")

out = st.empty()

def iter_sse(url: str, params: dict):
    """
    Parser SSE simples: lê linhas, detecta 'event:' e 'data:'.
    """
    with requests.get(url, params=params, stream=True, timeout=None) as r:
        r.raise_for_status()
        event = None
        data_lines = []
        for raw in r.iter_lines(decode_unicode=True):
            if raw is None:
                continue
            line = raw.strip()
            if line == "":
                # dispatch
                if data_lines:
                    data = "\n".join(data_lines)
                    yield event or "message", data
                event = None
                data_lines = []
                continue
            if line.startswith("event:"):
                event = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data_lines.append(line.split(":", 1)[1].lstrip())

if run and prompt.strip():
    text = ""
    for ev, data in iter_sse(f"{GATEWAY_URL}/stream", {"prompt": prompt}):
        if ev == "token":
            text += data
            out.markdown(text)
        elif ev == "error":
            st.error(data)
            break
