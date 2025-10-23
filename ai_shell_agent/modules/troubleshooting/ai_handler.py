"""
AI Handler for Troubleshooting Module
Handles error analysis and multi-step remediation
"""
import json
from dotenv import load_dotenv
from ...utils.ai_client import get_openai_client
from ...utils.ai_call import call_ai_chat
from .prompts import get_troubleshoot_prompt


load_dotenv()

# GPT-4o-mini client setup (centralized)
client = get_openai_client()

def ask_ai_for_troubleshoot(error_text: str, context: dict = None, history: list = None, system_context=None) -> dict:
    """
    Analyze an error and generate multi-step troubleshooting plan using AI.
    
    This function takes an error message and creates a comprehensive troubleshooting
    workflow including diagnostic commands, fix commands, and verification steps.
    
    Args:
        error_text (str): The error message or description to troubleshoot
        context (dict, optional): Additional context information:
            - last_command: The command that failed
            - last_output: stdout from the failed command
            - last_error: stderr from the failed command
            - diagnostic_results: Output from previous diagnostic commands
        history (list, optional): Previous troubleshooting steps for iterative analysis
        system_context (SystemContextManager, optional): Server context for system-aware troubleshooting
    
    Returns:
        dict: Contains troubleshooting analysis and commands:
            - troubleshoot_response: Structured JSON with analysis, commands, and metadata
            - raw_output: Raw AI response text
            - success: Boolean indicating if parsing succeeded
            - error: Error message if parsing failed
    
    Example:
        >>> result = ask_ai_for_troubleshoot("nginx: bind() failed")
        >>> print(result['troubleshoot_response']['fix_commands'])
        ['sudo systemctl stop apache2', 'sudo systemctl start nginx']
    """
    # Get base troubleshooting prompt
    base_prompt = get_troubleshoot_prompt()
    
    # Enhance prompt with server context if available
    if system_context and hasattr(system_context, 'enhance_ai_prompt'):
        system_prompt = system_context.enhance_ai_prompt(
            base_prompt,
            "troubleshooting",
            error_text=error_text,
            additional_context=context
        )
    else:
        system_prompt = base_prompt
    
    # Build comprehensive user message with error details and context
    user_message = f"Error to troubleshoot:\n{error_text}\n"
    
    # Add contextual information if available to improve troubleshooting accuracy
    if context:
        if context.get("last_command"):
            user_message += f"\nCommand that failed: {context['last_command']}"
        if context.get("last_output"):
            user_message += f"\nCommand output: {context['last_output']}"
        if context.get("last_error"):
            user_message += f"\nError output: {context['last_error']}"
        if context.get("diagnostic_results"):
            user_message += f"\nDiagnostic results:\n{context['diagnostic_results']}"
    
    # Initialize conversation with system prompt
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add conversation history for iterative troubleshooting sessions
    if history:
        for entry in history:
            if entry.get("user_msg"):
                messages.append({"role": "user", "content": entry["user_msg"]})
            if entry.get("ai_msg"):
                messages.append({"role": "assistant", "content": entry["ai_msg"]})
    
    # Add current troubleshooting request
    messages.append({"role": "user", "content": user_message})
    
    # Use centralized helper to call AI and parse JSON with fallback
    call_result = call_ai_chat(
        messages=messages,
        temperature=0.2,
        extra_query={"api-version": "2024-08-01-preview"},
        response_format={"type": "json_object"}
    )

    content = call_result.get('raw', '')
    parsed = call_result.get('parsed')
    error = call_result.get('error')

    if parsed is None:
        # Attempt to fallback to parsing raw content if present
        try:
            parsed = json.loads(content) if content else None
        except Exception as e:
            # Return safe error structure for troubleshooting workflow
            return {
                "troubleshoot_response": {
                    "analysis": "Failed to parse AI response",
                    "diagnostic_commands": [],
                    "fix_commands": [],
                    "verification_commands": [],
                    "reasoning": f"JSON parsing error: {str(e)}",
                    "risk_level": "high",
                    "requires_confirmation": True
                },
                "raw_output": content,
                "success": False,
                "error": str(e)
            }

    troubleshoot_response = parsed or {}

    # Validate that essential troubleshooting fields are present
    required_fields = ["analysis", "fix_commands", "verification_commands"]
    missing_fields = [field for field in required_fields if field not in troubleshoot_response]

    if missing_fields:
        print(f"Warning: Missing required fields: {missing_fields}")
        if "analysis" not in troubleshoot_response:
            troubleshoot_response["analysis"] = "Unable to analyze error"
        if "fix_commands" not in troubleshoot_response:
            troubleshoot_response["fix_commands"] = []
        if "verification_commands" not in troubleshoot_response:
            troubleshoot_response["verification_commands"] = []

    # Provide default values for optional troubleshooting fields
    if "diagnostic_commands" not in troubleshoot_response:
        troubleshoot_response["diagnostic_commands"] = []
    if "reasoning" not in troubleshoot_response:
        troubleshoot_response["reasoning"] = ""
    if "risk_level" not in troubleshoot_response:
        troubleshoot_response["risk_level"] = "medium"
    if "requires_confirmation" not in troubleshoot_response:
        troubleshoot_response["requires_confirmation"] = True

    success = error is None

    return {
        "troubleshoot_response": troubleshoot_response,
        "raw_output": content,
        "success": success,
        "error": error
    }
