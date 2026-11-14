"""REST providers sharing a small generate interface."""

import json
import os
from urllib.parse import quote

import requests


class ProviderError(Exception):
    def __init__(self, message, retryable=False):
        super().__init__(message)
        self.retryable = retryable


def _post(url, *, headers=None, payload):
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=120)
    except requests.RequestException as exc:
        # İstisna metni URL'deki olası kimlik bilgilerini açığa çıkarabilir.
        raise ProviderError("Network error", retryable=True) from exc
    if not response.ok:
        # Sunucu hata gövdesi kimlik bilgisi içerebilir; yalnızca durum kodunu göster.
        raise ProviderError(f"HTTP {response.status_code}", response.status_code == 429 or response.status_code >= 500)
    try:
        return response.json()
    except ValueError as exc:
        raise ProviderError("Invalid JSON response") from exc


DRY_JSON = json.dumps({"intent": "faq", "secondary_intents": [], "issues": [],
                       "ticket_id": None, "missing_fields": [], "lang": "tr"})


class DryProvider:
    def generate(self, system, user, temperature, max_tokens, seed, *, json_mode=False):
        output = DRY_JSON if json_mode else "[dry-run] " + user[:40]
        return {"output": output, "input_tokens": len(user) // 4, "output_tokens": len(output) // 4}


class GeminiProvider:
    def __init__(self, model, api_key):
        self.model, self.api_key = model, api_key

    def generate(self, system, user, temperature, max_tokens, seed, *, json_mode=False):
        data = _post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{quote(self.model, safe='')}:generateContent",
            headers={"x-goog-api-key": self.api_key},
            payload={"systemInstruction": {"parts": [{"text": system}]},
                     "contents": [{"role": "user", "parts": [{"text": user}]}],
                     "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens,
                                          "seed": seed,
                                          **({"responseMimeType": "application/json"} if json_mode else {})}},
        )
        candidate = (data.get("candidates") or [{}])[0]
        parts = candidate.get("content", {}).get("parts", [])
        usage = data.get("usageMetadata") or {}
        # Thinking token'ları da çıktı olarak faturalanır; maliyet için çıktıya eklenir.
        out_tokens = usage.get("candidatesTokenCount")
        if out_tokens is not None:
            out_tokens += usage.get("thoughtsTokenCount") or 0
        return {"output": "".join(p.get("text", "") for p in parts if not p.get("thought")),
                "input_tokens": usage.get("promptTokenCount"),
                "output_tokens": out_tokens,
                "finish_reason": candidate.get("finishReason")}


class OllamaProvider:
    def __init__(self, model, host):
        self.model, self.host = model, host.rstrip("/")

    def generate(self, system, user, temperature, max_tokens, seed, *, json_mode=False):
        data = _post(f"{self.host}/api/chat", payload={
            "model": self.model, "stream": False,
            **({"format": "json"} if json_mode else {}),
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "options": {"temperature": temperature, "num_predict": max_tokens, "seed": seed},
        })
        return {"output": (data.get("message") or {}).get("content", ""),
                "input_tokens": data.get("prompt_eval_count"), "output_tokens": data.get("eval_count")}


class OpenAICompatProvider:
    def __init__(self, model, base_url, api_key):
        self.model, self.base_url, self.api_key = model, base_url.rstrip("/"), api_key

    def generate(self, system, user, temperature, max_tokens, seed, *, json_mode=False):
        data = _post(f"{self.base_url}/chat/completions",
                     headers={"Authorization": f"Bearer {self.api_key}"},
                     payload={"model": self.model, "temperature": temperature,
                              **({"response_format": {"type": "json_object"}} if json_mode else {}),
                              "max_tokens": max_tokens, "seed": seed,
                              "messages": [{"role": "system", "content": system},
                                           {"role": "user", "content": user}]})
        choices = data.get("choices") or []
        usage = data.get("usage") or {}
        return {"output": (choices[0].get("message") or {}).get("content", "") if choices else "",
                "input_tokens": usage.get("prompt_tokens"), "output_tokens": usage.get("completion_tokens")}


def make_provider(name, model, base_url=None, api_key_env=None):
    if name == "dry":
        return DryProvider()
    if name == "ollama":
        return OllamaProvider(model, base_url or os.getenv("OLLAMA_HOST", "http://localhost:11434"))
    key_name = api_key_env or ("GEMINI_API_KEY" if name == "gemini" else "GROQ_API_KEY")
    key = os.getenv(key_name)
    if not key:
        raise ValueError(f"{key_name} is not set")
    if name == "gemini":
        return GeminiProvider(model, key)
    return OpenAICompatProvider(model, base_url or "https://api.groq.com/openai/v1", key)
