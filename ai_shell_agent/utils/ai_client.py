"""
Shared AI client factory.

Provides get_openai_client() which returns a configured OpenAI client instance.
This centralizes AOAI/OpenAI initialization and preserves the existing fallback
for older library versions that require an httpx client.
"""
from dotenv import load_dotenv
import os


def get_openai_client():
    """Return a configured OpenAI (AOAI) client instance.

    Environment variables used (optional):
      AOAI_BASE_URL - base URL for AOAI deployment
      AOAI_API_KEY - API key (or dummy if not set)
      AOAI_SUBSCRIPTION_KEY - subscription header value
    """
    load_dotenv()

    base_url = os.environ.get(
        "AOAI_BASE_URL",
        "https://aoai-farm.bosch-temp.com/api/openai/deployments/askbosch-prod-farm-openai-gpt-4o-mini-2024-07-18"
    )
    api_key = os.environ.get("AOAI_API_KEY", "dummy")
    sub_key = os.environ.get("AOAI_SUBSCRIPTION_KEY", "73620a9fe1d04540b9aabe89a2657a61")

    try:
        from openai import OpenAI
    except Exception:
        # If import fails let it surface when caller tries to use the API
        from openai import OpenAI

    try:
        client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            default_headers={
                "genaiplatform-farm-subscription-key": sub_key,
            }
        )
    except TypeError:
        # Older OpenAI versions expect an httpx client to be provided
        import httpx
        client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            default_headers={
                "genaiplatform-farm-subscription-key": sub_key,
            },
            http_client=httpx.Client()
        )

    return client
