"""
Test script for an internal LLM Gateway (LiteLLM-style proxy).

Uses ONLY the Python standard library (urllib, ssl, json) - no pip installs
required. This matters because dependency downloads (pip) are blocked in
this environment.

The API docs screenshot shows a LiteLLM proxy `GET /models` endpoint (query
params like team_id, model_access_groups, include_metadata, fallback_type are
LiteLLM-specific). This script exercises:
  1. GET /models            - list available models
  2. GET /model/info        - detailed model info (pricing, mode, etc.)
  3. POST /chat/completions - a basic OpenAI-compatible chat request

Configuration priority: in-code constants below > .env.llm file > env vars.

  LLM_GATEWAY_PEM_PATH   path to the .pem file (defaults to
                         RnDliteLLM_cert.pem next to this script)
  LLM_GATEWAY_PEM_MODE   "ca_bundle" (default) or "client_cert"
                           - ca_bundle: the pem verifies the gateway's server
                             certificate (this repo's pem is a 3-certificate
                             chain with no private key, so this is the
                             correct default).
                           - client_cert: the pem is YOUR certificate + key,
                             presented to the gateway for mTLS auth.
  LLM_GATEWAY_TEST_MODEL optional - a model name to use for the chat
                           completion test (skipped if not set)

Usage:
  python test_llm_gateway.py
"""

import json
import os
import ssl
import sys
import urllib.error
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PEM_PATH = os.path.join(SCRIPT_DIR, "RnDliteLLM_cert.pem")
ENV_FILE_PATH = os.path.join(SCRIPT_DIR, ".env.llm")

# --- Paste credentials directly here if you'd rather not use .env.llm ---
# WARNING: do not commit this file with real values filled in below.
# (test_llm_gateway.py is NOT gitignored, unlike .env.llm / *.pem.)
API_KEY = "sk-hMHyPNKXswxbUg_8JirHZg"
BASE_URL = "https://llmproxy.ustrnd.com"
# -------------------------------------------------------------------------


def load_env_file(path):
    """Minimal .env parser (no python-dotenv dependency)."""
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


def _mask(value: str, keep: int = 4) -> str:
    if not value:
        return "<empty>"
    if len(value) <= keep * 2:
        return "*" * len(value)
    return f"{value[:keep]}...{value[-keep:]}"


def load_config():
    env_file = load_env_file(ENV_FILE_PATH)

    base_url = (BASE_URL or env_file.get("LLM_GATEWAY_BASE_URL") or os.environ.get("LLM_GATEWAY_BASE_URL", "")).rstrip("/")
    api_key = API_KEY or env_file.get("LLM_GATEWAY_API_KEY") or os.environ.get("LLM_GATEWAY_API_KEY", "")
    pem_path = env_file.get("LLM_GATEWAY_PEM_PATH") or os.environ.get("LLM_GATEWAY_PEM_PATH", "") or DEFAULT_PEM_PATH
    pem_mode = (env_file.get("LLM_GATEWAY_PEM_MODE") or os.environ.get("LLM_GATEWAY_PEM_MODE", "ca_bundle")).strip().lower()
    test_model = env_file.get("LLM_GATEWAY_TEST_MODEL") or os.environ.get("LLM_GATEWAY_TEST_MODEL", "")

    missing = [name for name, val in [("BASE_URL", base_url), ("API_KEY", api_key)] if not val]
    if missing:
        print("Missing required config:", ", ".join(missing))
        print("Fill in API_KEY/BASE_URL at the top of this script, or in .env.llm.")
        sys.exit(1)

    if pem_path and not os.path.isfile(pem_path):
        print(f"PEM file not found: {pem_path}")
        sys.exit(1)

    if pem_mode not in ("client_cert", "ca_bundle"):
        print(f"LLM_GATEWAY_PEM_MODE must be 'client_cert' or 'ca_bundle', got: {pem_mode}")
        sys.exit(1)

    return {
        "base_url": base_url,
        "api_key": api_key,
        "pem_path": pem_path,
        "pem_mode": pem_mode,
        "test_model": test_model,
    }


def build_ssl_context(config):
    """Build an SSLContext honoring the pem mode, using only stdlib ssl."""
    if not config["pem_path"]:
        return ssl.create_default_context()

    if config["pem_mode"] == "ca_bundle":
        return ssl.create_default_context(cafile=config["pem_path"])

    # client_cert: pem is our certificate (+ key). Verification still uses
    # the system's default trust store for the server's certificate.
    context = ssl.create_default_context()
    context.load_cert_chain(certfile=config["pem_path"])
    return context


def request(url, config, ssl_context, method="GET", payload=None, timeout=30):
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
    }
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    return urllib.request.urlopen(req, timeout=timeout, context=ssl_context)


def print_result(label, status, body_text):
    print(f"\n--- {label} ---")
    print(f"Status: {status}")
    try:
        print(json.dumps(json.loads(body_text), indent=2)[:2000])
    except ValueError:
        print(body_text[:2000])


def run_request(label, url, config, ssl_context, method="GET", payload=None, timeout=30):
    try:
        with request(url, config, ssl_context, method=method, payload=payload, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            print_result(label, resp.status, body)
            return 200 <= resp.status < 300
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print_result(label, e.code, body)
        return False
    except urllib.error.URLError as e:
        reason = e.reason
        if isinstance(reason, ssl.SSLError):
            print(f"\n--- {label} ---\nTLS/SSL error: {reason}")
        else:
            print(f"\n--- {label} ---\nConnection failed: {reason}")
        return False
    except TimeoutError:
        print(f"\n--- {label} ---\nRequest timed out")
        return False


def main():
    config = load_config()
    ssl_context = build_ssl_context(config)

    print("LLM Gateway test (stdlib-only, no pip installs required)")
    print(f"  Base URL  : {config['base_url']}")
    print(f"  API key   : {_mask(config['api_key'])}")
    print(f"  PEM file  : {config['pem_path']} (mode={config['pem_mode']})")
    print(f"  Test model: {config['test_model'] or '<none - chat test skipped>'}")

    results = {}

    results["models"] = run_request(
        "GET /models", f"{config['base_url']}/models", config, ssl_context
    )

    results["model_info"] = run_request(
        "GET /model/info", f"{config['base_url']}/model/info", config, ssl_context
    )

    if config["test_model"]:
        payload = {
            "model": config["test_model"],
            "messages": [{"role": "user", "content": "Say 'OK' and nothing else."}],
            "max_tokens": 16,
        }
        results["chat_completion"] = run_request(
            "POST /chat/completions",
            f"{config['base_url']}/chat/completions",
            config,
            ssl_context,
            method="POST",
            payload=payload,
            timeout=60,
        )
    else:
        print("\n--- POST /chat/completions ---\nSkipped (LLM_GATEWAY_TEST_MODEL not set)")
        results["chat_completion"] = True

    print("\n=== Summary ===")
    for name, ok in results.items():
        print(f"  {name}: {'PASS' if ok else 'FAIL'}")

    sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    main()
