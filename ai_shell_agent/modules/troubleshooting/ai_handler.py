"""
AI Handler for Troubleshooting Module
Handles error analysis and multi-step remediation
"""
import json
from dotenv import load_dotenv
from openai import OpenAI
from .prompts import get_troubleshoot_prompt

load_dotenv()

# GPT-4o-mini client setup
try:
    client = OpenAI(
        base_url="https://aoai-farm.bosch-temp.com/api/openai/deployments/askbosch-prod-farm-openai-gpt-4o-mini-2024-07-18",
        api_key="dummy",
        default_headers={
            "genaiplatform-farm-subscription-key": "73620a9fe1d04540b9aabe89a2657a61",
        }
    )
except TypeError:
    # Fallback for older OpenAI library versions
    import httpx
    client = OpenAI(
        base_url="https://aoai-farm.bosch-temp.com/api/openai/deployments/askbosch-prod-farm-openai-gpt-4o-mini-2024-07-18",
        api_key="dummy",
        default_headers={
            "genaiplatform-farm-subscription-key": "73620a9fe1d04540b9aabe89a2657a61",
        },
        http_client=httpx.Client()
    )


def ask_ai_for_troubleshoot(error_text: str, context: dict = None, history: list = None, system_context=None) -> dict:
    """
    Ask AI to troubleshoot an error and provide diagnostic/fix commands.
    
    Args:
        error_text: The error message or description from the user
        context: Optional dict with additional context:
            - last_command: The command that failed
            - last_output: stdout from the command
            - last_error: stderr from the command
            - diagnostic_results: Output from previous diagnostic commands
        history: Optional list of previous troubleshooting steps
        system_context: Optional SystemContextManager for server awareness
    
    Returns:
        dict with:
            - troubleshoot_response: Parsed JSON from AI
            - raw_output: Raw AI response
            - success: Boolean indicating if parsing succeeded
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
    
    # Build user message with context
    user_message = f"Error to troubleshoot:\n{error_text}\n"
    
    if context:
        if context.get("last_command"):
            user_message += f"\nCommand that failed: {context['last_command']}"
        if context.get("last_output"):
            user_message += f"\nCommand output: {context['last_output']}"
        if context.get("last_error"):
            user_message += f"\nError output: {context['last_error']}"
        if context.get("diagnostic_results"):
            user_message += f"\nDiagnostic results:\n{context['diagnostic_results']}"
    
    # Prepare messages
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add history if provided (for iterative troubleshooting)
    if history:
        for entry in history:
            if entry.get("user_msg"):
                messages.append({"role": "user", "content": entry["user_msg"]})
            if entry.get("ai_msg"):
                messages.append({"role": "assistant", "content": entry["ai_msg"]})
    
    messages.append({"role": "user", "content": user_message})
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            extra_query={"api-version": "2024-08-01-preview"},
            temperature=0.2,  # Lower temperature for more consistent troubleshooting
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content.strip()
        
        # Parse JSON response
        troubleshoot_response = json.loads(content)
        
        # Validate required fields
        required_fields = ["analysis", "fix_commands", "verification_commands"]
        missing_fields = [field for field in required_fields if field not in troubleshoot_response]
        
        if missing_fields:
            print(f"Warning: Missing required fields: {missing_fields}")
            # Add defaults
            if "analysis" not in troubleshoot_response:
                troubleshoot_response["analysis"] = "Unable to analyze error"
            if "fix_commands" not in troubleshoot_response:
                troubleshoot_response["fix_commands"] = []
            if "verification_commands" not in troubleshoot_response:
                troubleshoot_response["verification_commands"] = []
        
        # Add defaults for optional fields
        if "diagnostic_commands" not in troubleshoot_response:
            troubleshoot_response["diagnostic_commands"] = []
        if "reasoning" not in troubleshoot_response:
            troubleshoot_response["reasoning"] = ""
        if "risk_level" not in troubleshoot_response:
            troubleshoot_response["risk_level"] = "medium"
        if "requires_confirmation" not in troubleshoot_response:
            troubleshoot_response["requires_confirmation"] = True
        
        return {
            "troubleshoot_response": troubleshoot_response,
            "raw_output": content,
            "success": True
        }
    
    except json.JSONDecodeError as e:
        print(f"JSON parsing failed: {e}")
        print(f"Raw response: {content}")
        
        # Return error structure
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
    
    except Exception as e:
        print(f"AI API call failed: {e}")
        return {
            "troubleshoot_response": {
                "analysis": "AI service unavailable",
                "diagnostic_commands": [],
                "fix_commands": [],
                "verification_commands": [],
                "reasoning": f"API error: {str(e)}",
                "risk_level": "high",
                "requires_confirmation": True
            },
            "raw_output": "",
            "success": False,
            "error": str(e)
        }
