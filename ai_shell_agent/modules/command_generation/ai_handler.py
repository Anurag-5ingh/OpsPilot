"""
AI Handler for Command Generation
Generates single commands from natural language input with server awareness
"""
import json
from dotenv import load_dotenv
from openai import OpenAI
from .prompts import get_system_prompt
from .risk_analyzer import CommandRiskAnalyzer, RiskLevel
from .fallback_analyzer import CommandFallbackAnalyzer

# Load environment variables
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

# Initialize analysis components
risk_analyzer = CommandRiskAnalyzer()
fallback_analyzer = CommandFallbackAnalyzer()


def ask_ai_for_command(user_input: str, memory: list = None, system_context=None) -> dict:
    """
    Generate a system-aware shell command from natural language input using AI.
    
    This function sends a natural language request to GPT-4o-mini and receives
    a structured JSON response containing an optimized shell command based on
    the target server's configuration (OS, package managers, services, etc.).
    
    Args:
        user_input (str): Natural language command request (e.g., "install nginx")
        memory (list, optional): Conversation history as list of (user_msg, ai_msg) tuples
        system_context (SystemContextManager, optional): Server context for system-aware commands
        
    Returns:
        dict: Contains 'ai_response' (parsed JSON) and 'raw_ai_output' (raw response)
              ai_response includes:
              - 'final_command': Optimized command for the target system
              - 'explanation': Brief explanation of what the command does
              - 'requires_sudo': Whether sudo privileges are needed
              - 'risk_level': Safety assessment (low/medium/high)
              - 'alternative_commands': Alternative ways to achieve the same goal
              Returns None if API call fails
    
    Example:
        >>> context_manager = SystemContextManager()
        >>> result = ask_ai_for_command("install web server", system_context=context_manager)
        >>> print(result['ai_response']['final_command'])
        'sudo apt update && sudo apt install -y nginx'  # Ubuntu system
        'sudo yum install -y httpd'                     # CentOS system
    """
    # Get base system prompt for command generation
    base_prompt = get_system_prompt()
    
    # Enhance prompt with server context if available
    if system_context and hasattr(system_context, 'enhance_ai_prompt'):
        system_prompt = system_context.enhance_ai_prompt(
            base_prompt,
            "command_generation",
            user_request=user_input
        )
    else:
        system_prompt = base_prompt

    # Build conversation history for context-aware responses
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add conversation history to maintain context across interactions
    if memory:
        for user_msg, ai_msg in memory:
            messages.append({"role": "user", "content": user_msg})
            messages.append({"role": "assistant", "content": ai_msg})
    
    # Add current user request
    messages.append({"role": "user", "content": user_input})

    try:
        # Call GPT-4o-mini via Bosch internal endpoint
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            extra_query={"api-version": "2024-08-01-preview"},
            temperature=0.3,  # Low temperature for consistent command generation
            response_format={"type": "json_object"}  # Ensure structured JSON response
        )

        content = response.choices[0].message.content.strip()
        
        # Parse JSON response from AI
        ai_response = json.loads(content)
        
        # Ensure required 'final_command' field exists
        if "final_command" not in ai_response:
            ai_response["final_command"] = ai_response.get("command", content)
        
        # Analyze command risks and add safety information
        final_command = ai_response.get("final_command", "")
        if final_command:
            current_profile = system_context.get_current_profile() if system_context else None
            risk_analysis = risk_analyzer.analyze_command(final_command, current_profile)
            
            # Add risk analysis to AI response
            ai_response.update({
                "risk_analysis": {
                    "risk_level": risk_analysis['risk_level'].value,
                    "requires_confirmation": risk_analysis['requires_confirmation'],
                    "warning_message": risk_analysis.get('warning_message', ''),
                    "detailed_impacts": risk_analysis.get('detailed_impacts', []),
                    "affected_areas": risk_analysis.get('affected_areas', []),
                    "safety_recommendations": risk_analysis.get('safety_recommendations', [])
                }
            })
        
        return {
            "ai_response": ai_response,
            "raw_ai_output": content
        }

    except json.JSONDecodeError as e:
        # Fallback: Handle cases where AI returns plain text instead of JSON
        print(f"JSON parsing failed: {e}")
        print(f"Raw response: {content}")
        
        # Create structured response from plain text command
        fallback_response = {
            "final_command": content,
            "explanation": "Command generated (JSON parsing failed)"
        }
        
        return {
            "ai_response": fallback_response,
            "raw_ai_output": content
        }
        
    except Exception as e:
        # Handle API failures, network issues, or other unexpected errors
        print(f"AI API call failed: {e}")
        return None


def analyze_command_failure(original_command: str, error_output: str, system_context=None) -> dict:
    """
    Analyze a failed command execution and provide intelligent alternatives.
    
    This function examines why a command failed and suggests better alternatives
    with detailed reasoning and system-aware solutions.
    
    Args:
        original_command (str): The command that failed to execute
        error_output (str): Error output/stderr from the failed command
        system_context (SystemContextManager, optional): Server context for better alternatives
        
    Returns:
        dict: Contains failure analysis and alternative command suggestions:
            - 'failure_analysis': Detailed analysis of why the command failed
            - 'alternative_solutions': List of alternative commands with reasoning
            - 'confidence_score': Confidence in the analysis (0.0 to 1.0)
            - 'system_specific_fixes': System-aware fixes if context available
    
    Example:
        >>> error = "bash: htop: command not found"
        >>> result = analyze_command_failure("htop", error, context_manager)
        >>> print(result['alternative_solutions'][0]['alternative_command'])
        'sudo apt install htop'  # Ubuntu system
        'sudo yum install htop'  # CentOS system
    """
    current_profile = system_context.get_current_profile() if system_context else None
    
    # Analyze the failure using the fallback analyzer
    failure_analysis = fallback_analyzer.analyze_failure(
        original_command, error_output, current_profile
    )
    
    # Structure the response for API consumption
    return {
        'original_command': original_command,
        'error_output': error_output,
        'failure_analysis': {
            'categories': [cat.value for cat in failure_analysis['failure_categories']],
            'root_cause': failure_analysis['root_cause_analysis'],
            'confidence_score': failure_analysis['confidence_score']
        },
        'alternative_solutions': failure_analysis['alternative_solutions'],
        'system_specific_fixes': failure_analysis.get('system_specific_fixes', []),
        'requires_system_changes': failure_analysis.get('requires_system_changes', False)
    }
