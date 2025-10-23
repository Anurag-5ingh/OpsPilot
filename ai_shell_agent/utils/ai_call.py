"""
Utility wrapper around the OpenAI/AOAI chat completions call.

Provides a safe helper that calls the configured client, extracts the
assistant message content, attempts to parse JSON and returns a structured
result dict: {'parsed': obj|None, 'raw': str, 'error': str|None}

This mirrors the parsing/fallback behavior already present in multiple
ai_handler modules but centralizes it in one place for maintainability.
"""
from typing import Any, Dict, Optional
from .ai_client import get_openai_client


def call_ai_chat(messages: list, temperature: float = 0.2, extra_query: dict = None, response_format: dict = None) -> Dict[str, Any]:
    """Call AOAI/OpenAI chat completions and attempt to parse JSON result.

    Args:
        messages: list of message dicts for chat API
        temperature: sampling temperature
        extra_query: optional dict to pass as extra_query
        response_format: optional response_format dict

    Returns:
        dict with keys: parsed (dict or None), raw (str), error (None or message)
    """
    client = get_openai_client()

    try:
        create_args = {
            'model': 'gpt-4o-mini',
            'messages': messages,
            'temperature': temperature
        }
        if extra_query:
            create_args['extra_query'] = extra_query
        if response_format:
            create_args['response_format'] = response_format

        response = client.chat.completions.create(**create_args)
        content = ''
        try:
            content = response.choices[0].message.content.strip()
        except Exception:
            # Fallback: try other shapes
            content = str(response)

        # Try parse JSON
        try:
            import json
            parsed = json.loads(content)
            return {'parsed': parsed, 'raw': content, 'error': None}
        except Exception as e:
            return {'parsed': None, 'raw': content, 'error': f'JSON parse failed: {e}'}

    except Exception as e:
        return {'parsed': None, 'raw': '', 'error': f'API call failed: {e}'}
