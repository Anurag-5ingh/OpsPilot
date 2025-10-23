from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables once for the process
load_dotenv()

_client_instance = None

def get_openai_client():
    global _client_instance
    if _client_instance is not None:
        return _client_instance
    try:
        _client_instance = OpenAI(
            base_url="https://ai-endpoint.example.com/api/openai/deployments/askbosch-prod-farm-openai-gpt-4o-mini-2024-07-18",
            api_key="dummy",
            default_headers={
                "genaiplatform-farm-subscription-key": "REDACTED",
            }
        )
        return _client_instance
    except TypeError:
        import httpx
        _client_instance = OpenAI(
            base_url="https://ai-endpoint.example.com/api/openai/deployments/askbosch-prod-farm-openai-gpt-4o-mini-2024-07-18",
            api_key="dummy",
            default_headers={
                "genaiplatform-farm-subscription-key": "REDACTED",
            },
            http_client=httpx.Client()
        )
        return _client_instance
