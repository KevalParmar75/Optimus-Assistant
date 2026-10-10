"""
Unified LLM Client for Optimus V3.
Prioritizes ultra-fast Groq (Llama-3.3-70b-versatile) when GROQ_API_KEY is present,
with graceful fallback to HuggingFace InferenceClient.
"""
import os
from dotenv import load_dotenv

load_dotenv()

_groq_client = None
_hf_client = None


def chat_complete(messages: list, max_tokens: int = 512, temperature: float = 0.5) -> str:
    """
    Sends a chat completion request to Groq (primary) or HuggingFace (fallback).
    """
    global _groq_client, _hf_client

    # 1. Groq (300+ tokens/sec, state-of-the-art)
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key and groq_key.strip():
        try:
            if _groq_client is None:
                from groq import Groq
                _groq_client = Groq(api_key=groq_key.strip())
            resp = _groq_client.chat.completions.create(
                model="qwen/qwen3.8-27b",
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            content = resp.choices[0].message.content
            if content:
                return content.strip()
        except Exception as ge:
            print(f"[LLM] Groq call failed ({ge}), trying fallback...")

    # 2. Hugging Face fallback
    hf_token = os.getenv("HF_TOKEN")
    if hf_token and hf_token.strip():
        try:
            if _hf_client is None:
                from huggingface_hub import InferenceClient
                _hf_client = InferenceClient(token=hf_token.strip())
            resp = _hf_client.chat_completion(
                model="Qwen/Qwen2.5-72B-Instruct",
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            content = resp.choices[0].message.content
            if content:
                return content.strip()
        except Exception as he:
            print(f"[LLM] HuggingFace call failed ({he})")

    return ""
