"""
Unified LLM Client for Optimus V3.
Powered by high-speed Groq API (qwen/qwen3.8-27b) for text, code, and multimodal vision inference.
"""
import os
from dotenv import load_dotenv

load_dotenv()

_groq_client = None
PRIMARY_MODEL = "qwen/qwen3.8-27b"
FALLBACK_TEXT_MODEL = "openai/gpt-oss-120b"


def _get_client():
    global _groq_client
    if _groq_client is None:
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key and groq_key.strip():
            from groq import Groq
            _groq_client = Groq(api_key=groq_key.strip())
    return _groq_client


def chat_complete(messages: list, max_tokens: int = 512, temperature: float = 0.5) -> str:
    """
    Sends a chat completion request to the high-speed Groq API.
    """
    client = _get_client()
    if not client:
        print("[LLM] GROQ_API_KEY is missing or invalid.")
        return ""

    # Primary model attempt
    try:
        resp = client.chat.completions.create(
            model=PRIMARY_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        content = resp.choices[0].message.content
        if content:
            return content.strip()
    except Exception as ge:
        print(f"[LLM] Primary model ({PRIMARY_MODEL}) failed: {ge}, trying secondary...")

    # Secondary text model attempt
    try:
        resp = client.chat.completions.create(
            model=FALLBACK_TEXT_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        content = resp.choices[0].message.content
        if content:
            return content.strip()
    except Exception as fe:
        print(f"[LLM] Secondary model ({FALLBACK_TEXT_MODEL}) failed: {fe}")

    return ""


def vision_complete(b64_image: str, prompt: str, max_tokens: int = 400, temperature: float = 0.1) -> str:
    """
    Sends a multimodal vision-language request (image + prompt) to Groq.
    """
    client = _get_client()
    if not client:
        print("[LLM] GROQ_API_KEY is missing or invalid for vision.")
        return ""

    if not b64_image:
        return ""

    # Format data URI if not already prefixed
    if b64_image.startswith("data:"):
        image_url = b64_image
    else:
        image_url = f"data:image/jpeg;base64,{b64_image}"

    try:
        resp = client.chat.completions.create(
            model=PRIMARY_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }],
            max_tokens=max_tokens,
            temperature=temperature
        )
        content = resp.choices[0].message.content
        if content:
            return content.strip()
    except Exception as ve:
        print(f"[LLM] Vision completion failed: {ve}")

    return ""
