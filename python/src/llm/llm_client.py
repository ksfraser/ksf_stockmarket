"""
llm_client.py — LLM client with primary/secondary/fallback endpoint chain.

Reads endpoint config from system_settings (via DB) or environment variables.
Routes LLM calls through primary -> secondary -> fallback on failure.

Production usage:
    from python.src.llm.llm_client import LlmClient
    client = LlmClient(db_connection)
    response = client.chat(symbol="RY.TO", prompt="Analyze this...", model=None)

Standalone usage (reads from environment):
    export LLM_PRIMARY_URL=https://api.openai.com/v1
    export LLM_PRIMARY_MODEL=gpt-4o
    export LLM_PRIMARY_TOKEN=sk-...
    python3 -m python.src.llm.llm_client --test
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System settings keys (must match database/migrations/020_*.sql)
# ---------------------------------------------------------------------------
LLM_KEYS = {
    "primary": ["llm_primary_url", "llm_primary_model", "llm_primary_token"],
    "secondary": ["llm_secondary_url", "llm_secondary_model", "llm_secondary_token"],
    "fallback": ["llm_fallback_url", "llm_fallback_model", "llm_fallback_token"],
}


class LlmEndpoint:
    """A single LLM endpoint configuration."""

    def __init__(self, name: str, url: str, model: str, token: str):
        self.name = name
        self.url = url
        self.model = model
        self.token = token
        self.available = False
        self.last_error: Optional[str] = None
        self.last_latency_ms: Optional[float] = None

    def is_configured(self) -> bool:
        return bool(self.url and self.model and self.token)

    def __repr__(self) -> str:
        status = "configured" if self.is_configured() else "unconfigured"
        return f"<LlmEndpoint {self.name} ({status})>"


class LlmClient:
    """
    LLM client with three-endpoint fallback chain.

    Reads configuration from:
    1. system_settings table (if db connection provided)
    2. Environment variables (LLM_PRIMARY_URL, etc.) as fallback

    Call sequence: primary -> secondary -> fallback.
    If an endpoint fails (timeout, HTTP error, exception), the next endpoint
    in the chain is tried automatically.
    """

    def __init__(self, db: Any = None):
        self.db = db
        self.endpoints: dict[str, LlmEndpoint] = {}
        self._last_used: Optional[str] = None
        self._load_config()

    # ------------------------------------------------------------------
    # Configuration loading
    # ------------------------------------------------------------------

    def _load_config(self) -> None:
        """Load endpoint configs from DB or environment."""
        for profile in ("primary", "secondary", "fallback"):
            url = model = token = ""

            # Try system_settings table first
            if self.db is not None:
                try:
                    url = self._get_setting(f"llm_{profile}_url")
                    model = self._get_setting(f"llm_{profile}_model")
                    token = self._get_setting(f"llm_{profile}_token")
                except Exception as exc:
                    logger.debug("Failed to read LLM config from DB for %s: %s", profile, exc)

            # Fall back to environment variables
            if not url:
                url = os.environ.get(f"LLM_{profile.upper()}_URL", "")
            if not model:
                model = os.environ.get(f"LLM_{profile.upper()}_MODEL", "")
            if not token:
                token = os.environ.get(f"LLM_{profile.upper()}_TOKEN", "")

            self.endpoints[profile] = LlmEndpoint(profile, url, model, token)

        logger.info(
            "LLM client initialized: primary=%s, secondary=%s, fallback=%s",
            self.endpoints["primary"].is_configured(),
            self.endpoints["secondary"].is_configured(),
            self.endpoints["fallback"].is_configured(),
        )

    def _get_setting(self, key: str) -> str:
        """Read a single setting from system_settings table."""
        if self.db is None:
            return ""
        try:
            stmt = self.db.prepare("SELECT setting_value FROM system_settings WHERE setting_key = :key")
            stmt.execute([":key", key])
            row = stmt.fetchone()
            return row[0] if row else ""
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chat(
        self,
        prompt: str,
        model_override: Optional[str] = None,
        timeout_seconds: float = 30.0,
        max_tokens: int = 2000,
        temperature: float = 0.2,
    ) -> Tuple[Optional[str], str]:
        """
        Send a chat prompt through the fallback chain.

        Returns (response_text, endpoint_name_used).
        If all endpoints fail, returns (None, "all_failed").
        """
        for profile in ("primary", "secondary", "fallback"):
            endpoint = self.endpoints[profile]
            if not endpoint.is_configured():
                logger.debug("Skipping unconfigured endpoint: %s", profile)
                continue

            logger.info("Trying LLM endpoint: %s (%s, model=%s)",
                        profile, endpoint.url, endpoint.model)
            response, ok = self._call_endpoint(
                endpoint, prompt, model_override, timeout_seconds, max_tokens, temperature
            )
            if ok:
                self._last_used = profile
                endpoint.available = True
                endpoint.last_error = None
                return response, profile

            # Mark unavailable and try next
            endpoint.available = False
            logger.warning("LLM endpoint %s failed: %s", profile, endpoint.last_error or "unknown")

        return None, "all_failed"

    def health_check(self) -> dict[str, dict[str, Any]]:
        """
        Check health of all configured endpoints.
        Returns dict mapping profile name to status info.
        Does NOT send a real prompt — just checks connectivity.
        """
        results = {}
        for profile in ("primary", "secondary", "fallback"):
            ep = self.endpoints[profile]
            if not ep.is_configured():
                results[profile] = {
                    "configured": False,
                    "available": False,
                    "latency_ms": None,
                    "error": "Not configured",
                }
                continue

            # Quick connectivity test — just check if the URL is reachable
            start = time.time()
            try:
                if "openrouter" in ep.url or "openai" in ep.url:
                    # For OpenAI-compatible APIs, do a minimal models.list call
                    import urllib.request
                    import json as json_mod
                    req = urllib.request.Request(
                        f"{ep.url}/models",
                        headers={
                            "Authorization": f"Bearer {ep.token}",
                            "Content-Type": "application/json",
                        },
                    )
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        if resp.status == 200:
                            elapsed = (time.time() - start) * 1000
                            results[profile] = {
                                "configured": True,
                                "available": True,
                                "latency_ms": round(elapsed, 1),
                                "error": None,
                            }
                            ep.available = True
                            continue
                        else:
                            raise Exception(f"HTTP {resp.status}")
                else:
                    # Generic URL check
                    import urllib.request
                    req = urllib.request.Request(ep.url, method="HEAD")
                    req.add_header("Authorization", f"Bearer {ep.token}")
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        elapsed = (time.time() - start) * 1000
                        results[profile] = {
                            "configured": True,
                            "available": resp.status == 200,
                            "latency_ms": round(elapsed, 1),
                            "error": None if resp.status == 200 else f"HTTP {resp.status}",
                        }
                        ep.available = resp.status == 200
                        continue
            except Exception as exc:
                elapsed = (time.time() - start) * 1000
                results[profile] = {
                    "configured": True,
                    "available": False,
                    "latency_ms": round(elapsed, 1),
                    "error": str(exc)[:200],
                }
                ep.last_error = str(exc)
                ep.available = False

        return results

    # ------------------------------------------------------------------
    # Internal: single endpoint call
    # ------------------------------------------------------------------

    def _call_endpoint(
        self,
        endpoint: LlmEndpoint,
        prompt: str,
        model_override: Optional[str],
        timeout_seconds: float,
        max_tokens: int,
        temperature: float,
    ) -> Tuple[Optional[str], bool]:
        """
        Call a single LLM endpoint. Returns (response_text, success_bool).
        On any failure, sets endpoint.last_error and returns (None, False).
        """
        model = model_override or endpoint.model
        if not model:
            model = "gpt-4o"  # sensible default

        messages = [
            {"role": "system", "content": "You are a professional financial analyst. Respond concisely."},
            {"role": "user", "content": prompt},
        ]

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        import urllib.request
        import urllib.error
        import json as json_mod

        try:
            data = json_mod.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{endpoint.url}/chat/completions",
                data=data,
                headers={
                    "Authorization": f"Bearer {endpoint.token}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                if resp.status != 200:
                    endpoint.last_error = f"HTTP {resp.status}"
                    return None, False
                body = json_mod.loads(resp.read().decode("utf-8"))
                choices = body.get("choices", [])
                if not choices:
                    endpoint.last_error = "No choices in response"
                    return None, False
                text = choices[0].get("message", {}).get("content", "")
                if not text:
                    endpoint.last_error = "Empty response content"
                    return None, False
                return text, True

        except urllib.error.HTTPError as exc:
            endpoint.last_error = f"HTTP {exc.code}: {exc.reason}"
            return None, False
        except urllib.error.URLError as exc:
            endpoint.last_error = f"Connection error: {exc.reason}"
            return None, False
        except Exception as exc:
            endpoint.last_error = f"{type(exc).__name__}: {exc}"
            return None, False


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    client = LlmClient()
    print("\n=== LLM Endpoint Configuration ===")
    for name, ep in client.endpoints.items():
        print(f"  {name}: url={ep.url or '(empty)'}, model={ep.model or '(empty)'}, "
              f"token={'*(set)' if ep.token else '(empty)'}, configured={ep.is_configured()}")

    print("\n=== Health Check ===")
    health = client.health_check()
    for profile, info in health.items():
        status = "OK" if info["available"] else "FAIL"
        lat = f"{info['latency_ms']:.0f}ms" if info["latency_ms"] else "N/A"
        err = f" ({info['error']})" if info["error"] else ""
        print(f"  {profile}: [{status}] latency={lat}{err}")

    print("\n=== Chat Test ===")
    response, used = client.chat(
        "Respond with exactly one sentence: 'LLM connection test successful.' "
        "Do not add any other text."
    )
    if response:
        print(f"  Endpoint used: {used}")
        print(f"  Response: {response}")
    else:
        print(f"  Failed. Last error from primary: {client.endpoints['primary'].last_error}")
