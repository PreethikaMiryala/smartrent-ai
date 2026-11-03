"""
SmartRent AI - Groq AI Service Wrapper
"""
import os
import streamlit as st
from typing import Generator, Optional, Tuple, List, Dict, Any
from groq import Groq
from config import DEFAULT_GROQ_MODEL, ENV_GROQ_API_KEY


def get_active_groq_api_key() -> str:
    """
    Retrieve the current Groq API key with priority:
    1. Streamlit Session State (entered in UI Settings)
    2. Streamlit Secrets (st.secrets["GROQ_API_KEY"])
    3. Environment Variable (GROQ_API_KEY)
    """
    if "groq_api_key" in st.session_state and st.session_state.groq_api_key.strip():
        return st.session_state.groq_api_key.strip()

    try:
        if hasattr(st, "secrets") and "GROQ_API_KEY" in st.secrets:
            return st.secrets["GROQ_API_KEY"].strip()
    except Exception:
        pass

    if ENV_GROQ_API_KEY:
        return ENV_GROQ_API_KEY.strip()

    return ""


def get_groq_client(api_key: Optional[str] = None) -> Optional[Groq]:
    """
    Instantiate and return a Groq client if an API key is available.
    """
    key = api_key if api_key else get_active_groq_api_key()
    if not key:
        return None
    try:
        return Groq(api_key=key)
    except Exception:
        return None


def test_groq_connection(api_key: str) -> Tuple[bool, str]:
    """
    Test connection to Groq API with the specified key.
    """
    if not api_key or not api_key.strip():
        return False, "Please enter a valid Groq API key."
    try:
        client = Groq(api_key=api_key.strip())
        # Make a minimal test call
        resp = client.chat.completions.create(
            model=DEFAULT_GROQ_MODEL,
            messages=[{"role": "user", "content": "ping"}],
            max_completion_tokens=10,
            temperature=0.1
        )
        if resp and resp.choices:
            return True, f"Connection successful! Model '{DEFAULT_GROQ_MODEL}' is active and responding."
        return False, "Connected, but received empty response."
    except Exception as e:
        err_msg = str(e)
        if "401" in err_msg or "Invalid API Key" in err_msg:
            return False, "Authentication failed: Invalid Groq API Key."
        return False, f"Connection error: {err_msg}"


def stream_groq_chat(
    messages: List[Dict[str, Any]], 
    model: str = DEFAULT_GROQ_MODEL,
    temperature: float = 0.6,
    max_tokens: int = 2048,
    top_p: float = 0.95
) -> Generator[str, None, None]:
    """
    Stream chat responses adhering to PRD specifications.
    Yields chunks of text for Streamlit's chat interface.
    """
    client = get_groq_client()
    if not client:
        yield "⚠️ Groq API Key is not configured. Please configure your API key in Settings or contact the administrator."
        return

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_completion_tokens=max_tokens,
            top_p=top_p,
            stream=True,
            stop=None
        )

        for chunk in completion:
            delta = chunk.choices[0].delta
            content = getattr(delta, "content", None)
            if content:
                yield content
    except Exception as e:
        yield f"\n\n⚠️ Error during AI generation: {str(e)}"


def call_groq_completion(
    messages: List[Dict[str, Any]],
    model: str = DEFAULT_GROQ_MODEL,
    temperature: float = 0.2,
    max_tokens: int = 3000
) -> str:
    """
    Non-streaming completion for structured analysis tasks (cleanliness inspection, damage detection).
    """
    client = get_groq_client()
    if not client:
        raise ValueError("Groq API Key is not configured. Please configure your API key in Settings.")

    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_completion_tokens=max_tokens,
        top_p=0.95,
        stream=False,
    )
    if completion.choices and completion.choices[0].message:
        return completion.choices[0].message.content or ""
    return ""
