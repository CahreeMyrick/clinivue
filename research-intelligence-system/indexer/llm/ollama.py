from __future__ import annotations

from dataclasses import dataclass

import requests
from google import genai

client = genai.Client()

@dataclass(frozen=True)
class GeminiLLM:
    """Local LLM client for Gemini."""

    model: str = "gemini-3-flash-preview"

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.0,
    ) -> str:
        config = {"temperature": temperature}
        if system:
            config["system_instruction"] = system

        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )

        if not response.text:
            raise RuntimeError("Gemini response did not contain text.")

        return response.text.strip()

@dataclass(frozen=True)
class OllamaLLM:
    """
    Local LLM client for Ollama.

    The client is deliberately small: retrieval and evidence construction
    remain outside the LLM adapter.
    """

    model: str = "qwen3:4b-docmind"
    base_url: str = "http://localhost:11434"
    timeout_seconds: float = 120.0

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.0,
    ) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        if system:
            payload["system"] = system

        response = requests.post(
            f"{self.base_url.rstrip('/')}/api/generate",
            json=payload,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()

        data = response.json()

        answer = data.get("response")
        if not isinstance(answer, str):
            raise RuntimeError(
                "Ollama response did not contain a valid 'response' field."
            )

        return answer.strip()
