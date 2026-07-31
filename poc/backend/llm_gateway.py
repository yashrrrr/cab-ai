"""
LLM Gateway client — CAB Readiness Agent's LLM backend.

This is a SEPARATE client from cab_orchestrator.py's OpenAI-SDK/GitHub-Models
client (used only by the pre-existing "AI CAB" deliberation feature). The
CAB Readiness Agent instead talks to this repo's pre-configured LiteLLM proxy
gateway, which fronts real Claude models via an OpenAI-compatible
POST /chat/completions route (confirmed by ../../test_llm_gateway.py).

Configuration priority: real env vars (LLM_GATEWAY_*) > repo-root .env.llm
file (gitignored) > built-in defaults. Uses the same key names and .env
parsing approach as test_llm_gateway.py so that file keeps working unedited.
"""

import os
import ssl
import logging
from typing import Optional

import httpx
from openai import OpenAI

logger = logging.getLogger(__name__)

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_BACKEND_DIR, "..", ".."))
_ENV_FILE_PATH = os.path.join(_REPO_ROOT, ".env.llm")
_DEFAULT_PEM_PATH = os.path.join(_REPO_ROOT, "RnDliteLLM_cert.pem")


def _load_env_file(path: str) -> dict:
    """Minimal .env parser — mirrors test_llm_gateway.py's load_env_file."""
    values = {}
    if not os.path.isfile(path):
        return values
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _load_config() -> dict:
    env_file = _load_env_file(_ENV_FILE_PATH)

    def get(name: str, default: str = "") -> str:
        return os.environ.get(name) or env_file.get(name) or default

    base_url = get("LLM_GATEWAY_BASE_URL").rstrip("/")
    api_key = get("LLM_GATEWAY_API_KEY")
    pem_path = get("LLM_GATEWAY_PEM_PATH") or _DEFAULT_PEM_PATH
    pem_mode = get("LLM_GATEWAY_PEM_MODE", "ca_bundle").strip().lower()
    # LLM_GATEWAY_MODEL is the model this module actually calls with; falls
    # back to LLM_GATEWAY_TEST_MODEL (test_llm_gateway.py's existing key)
    # so today's .env.llm keeps working without edits.
    model = get("LLM_GATEWAY_MODEL") or get("LLM_GATEWAY_TEST_MODEL")

    return {
        "base_url": base_url,
        "api_key": api_key,
        "pem_path": pem_path,
        "pem_mode": pem_mode,
        "model": model,
    }


def _build_client(config: dict) -> Optional[OpenAI]:
    if not config["base_url"] or not config["api_key"]:
        return None

    ssl_context = None
    if config["pem_path"] and os.path.isfile(config["pem_path"]):
        if config["pem_mode"] == "ca_bundle":
            ssl_context = ssl.create_default_context(cafile=config["pem_path"])
        elif config["pem_mode"] == "client_cert":
            ssl_context = ssl.create_default_context()
            ssl_context.load_cert_chain(certfile=config["pem_path"])

    http_client = httpx.Client(verify=ssl_context) if ssl_context else None

    return OpenAI(
        api_key=config["api_key"],
        base_url=config["base_url"],
        http_client=http_client,
    )


_config = _load_config()
_client = _build_client(_config)


def chat_completion(system_prompt: str, user_prompt: str, *, model: Optional[str] = None,
                     max_tokens: int = 800, temperature: float = 0) -> Optional[str]:
    """
    Returns the assistant's text, or None on any failure — never raises.

    Callers treat a failed LLM call as an inconclusive area (status stays
    "missing" with a note), never as a fatal error for the whole evaluation.

    Logging on failure includes only the exception type and model name —
    never the prompt or response content, since prompts may contain CR or
    document text that PII guardrails apply to.
    """
    if _client is None:
        logger.warning("llm_gateway: not configured (missing LLM_GATEWAY_BASE_URL/API_KEY)")
        return None

    resolved_model = model or _config["model"]
    if not resolved_model:
        logger.warning("llm_gateway: no model configured (LLM_GATEWAY_MODEL/LLM_GATEWAY_TEST_MODEL)")
        return None

    try:
        response = _client.chat.completions.create(
            model=resolved_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.warning("llm_gateway: chat_completion failed (%s) model=%s", type(e).__name__, resolved_model)
        return None
