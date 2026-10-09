"""
Shared OpenAI-compatible client, configured from environment variables:

  OPENAI_API_KEY        API key (required for AI features)
  OPENAI_BASE_URL       Endpoint URL; omit to use api.openai.com
  OPENAI_MODEL          Model name (default: gpt-4o-mini)
  OPENAI_API_VERSION    Sent as the ?api-version= query parameter (Azure OpenAI)
  OPENAI_EXTRA_HEADERS  JSON object of extra request headers, e.g. a gateway
                        subscription-key header

Without OPENAI_API_KEY the app still starts; AI requests fail with an auth error.
"""
import json
import logging
import os

from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables once for the process
load_dotenv()

logger = logging.getLogger(__name__)

AI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

_client_instance = None


def ai_extra_query():
    """Query parameters to send with each AI request (api-version for Azure)."""
    api_version = os.getenv("OPENAI_API_VERSION")
    return {"api-version": api_version} if api_version else None


def _extra_headers():
    raw = os.getenv("OPENAI_EXTRA_HEADERS")
    if not raw:
        return None
    try:
        headers = json.loads(raw)
        if not isinstance(headers, dict):
            raise ValueError("must be a JSON object")
        return {str(k): str(v) for k, v in headers.items()}
    except ValueError as e:
        logger.warning(f"Ignoring invalid OPENAI_EXTRA_HEADERS: {e}")
        return None


def get_openai_client():
    global _client_instance
    if _client_instance is not None:
        return _client_instance

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY is not set; AI features will not work")
    options = {
        # The SDK refuses to construct without a key; a placeholder keeps the
        # app (UI, terminals) usable and makes AI calls fail with an auth error
        "api_key": api_key or "not-set",
        "base_url": os.getenv("OPENAI_BASE_URL") or None,
        "default_headers": _extra_headers(),
    }
    try:
        _client_instance = OpenAI(**options)
    except TypeError:
        # Older openai/httpx combinations need an explicit http client
        import httpx
        _client_instance = OpenAI(**options, http_client=httpx.Client())
    return _client_instance
