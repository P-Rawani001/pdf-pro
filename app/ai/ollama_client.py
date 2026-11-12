"""Local-only HTTP client for Ollama REST API (http://127.0.0.1:11434)."""

from __future__ import annotations

from dataclasses import dataclass
import requests

from app.config import OLLAMA_BASE_URL, OLLAMA_TIMEOUT_SECONDS


class OllamaUnavailableError(Exception):
    """Raised when local Ollama service cannot be reached or returns an error."""


@dataclass(frozen=True)
class OllamaStatus:
    """Health and model inventory from local Ollama."""

    available: bool
    models: list[str]
    message: str


class OllamaClient:
    """Communicates strictly with localhost Ollama; never contacts external servers."""

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        timeout: int = OLLAMA_TIMEOUT_SECONDS,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def check_status(self) -> OllamaStatus:
        """Query local Ollama server and return installed model names."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=3.0)
            resp.raise_for_status()
            data = resp.json()
            models = [
                m.get("name", "")
                for m in data.get("models", [])
                if m.get("name")
            ]
            if not models:
                return OllamaStatus(
                    available=True,
                    models=[],
                    message="Ollama is running, but no models are pulled yet (run: ollama pull qwen2.5:1.5b).",
                )
            return OllamaStatus(
                available=True,
                models=models,
                message=f"Connected locally ({len(models)} model(s) ready)",
            )
        except Exception:
            return OllamaStatus(
                available=False,
                models=[],
                message="Ollama is not running locally. Start Ollama to enable AI chat (all PDF tools still work).",
            )

    def chat(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Send a single-turn grounded prompt to local Ollama /api/chat."""
        payload = {
            "model": model,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_ctx": 4096,
            },
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        try:
            resp = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data.get("message", {}).get("content", "").strip()
            if not content:
                raise OllamaUnavailableError("Ollama returned an empty response.")
            return content
        except requests.Timeout as exc:
            raise OllamaUnavailableError(
                "Local model timed out. Try selecting a smaller model (e.g., qwen2.5:1.5b)."
            ) from exc
        except requests.RequestException as exc:
            raise OllamaUnavailableError(
                f"Could not communicate with local Ollama: {exc}"
            ) from exc
