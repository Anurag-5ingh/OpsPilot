"""
Shared prompt helper fragments used across module-specific prompts.

Keep the helpers minimal and stable to avoid changing semantics of module prompts.
"""

def json_only_instruction() -> str:
    """Return the common instruction that the model must respond only with JSON."""
    return (
        "IMPORTANT: You must respond with ONLY a valid JSON object (no markdown, no explanation outside JSON).\n\n"
    )

def json_format_note() -> str:
    """Generic note about the expected JSON format placeholder."""
    return "The JSON must have this exact format:\n"
