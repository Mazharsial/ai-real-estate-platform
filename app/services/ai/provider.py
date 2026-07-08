"""Configurable AI provider abstraction.

Set AI_PROVIDER = gemini | ollama | openrouter | openai in the environment.
Every call degrades gracefully to None so callers can use deterministic fallbacks.
"""
from __future__ import annotations

import httpx

from app.core.config import settings


def _gemini(prompt: str, system: str | None, temperature: float, max_tokens: int) -> str | None:
    key = settings.GEMINI_API_KEY
    if not key:
        return None
    body: dict = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
    }
    if system:
        body["system_instruction"] = {"parts": [{"text": system}]}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={key}"
    r = httpx.post(url, json=body, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def _openai_compatible(base_url: str, api_key: str, model: str, prompt: str,
                       system: str | None, temperature: float, max_tokens: int) -> str | None:
    if not api_key:
        return None
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    r = httpx.post(
        f"{base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens},
        timeout=45,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def _ollama(prompt: str, system: str | None, temperature: float) -> str | None:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    r = httpx.post(
        f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat",
        json={"model": settings.OLLAMA_MODEL, "messages": messages, "stream": False,
              "options": {"temperature": temperature}},
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["message"]["content"].strip()


def generate_text(prompt: str, system: str | None = None, temperature: float = 0.5,
                  max_tokens: int = 600) -> str | None:
    """Dispatch to the configured provider. Returns None on any failure."""
    provider = (settings.AI_PROVIDER or "gemini").lower()
    try:
        if provider == "gemini":
            return _gemini(prompt, system, temperature, max_tokens)
        if provider == "openrouter":
            return _openai_compatible("https://openrouter.ai/api/v1", settings.OPENROUTER_API_KEY,
                                      settings.OPENROUTER_MODEL, prompt, system, temperature, max_tokens)
        if provider == "openai":
            return _openai_compatible(settings.OPENAI_BASE_URL, settings.OPENAI_API_KEY,
                                      settings.OPENAI_MODEL, prompt, system, temperature, max_tokens)
        if provider == "ollama":
            return _ollama(prompt, system, temperature)
    except Exception:  # noqa: BLE001 — graceful degradation
        return None
    return None


def ai_available() -> bool:
    p = (settings.AI_PROVIDER or "").lower()
    return bool(
        (p == "gemini" and settings.GEMINI_API_KEY)
        or (p == "openrouter" and settings.OPENROUTER_API_KEY)
        or (p == "openai" and settings.OPENAI_API_KEY)
        or (p == "ollama")
    )
