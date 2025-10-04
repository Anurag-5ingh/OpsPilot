# ai_command.py
import json
from dotenv import load_dotenv
from openai import OpenAI
from ai_shell_agent.prompt_config import get_system_prompt

# Load environment variables
load_dotenv()

# GPT-4o-mini client setup (Bosch internal)
client = OpenAI(
    base_url="https://aoai-farm.bosch-temp.com/api/openai/deployments/askbosch-prod-farm-openai-gpt-4o-mini-2024-07-18",
    api_key="dummy",
    default_headers={
        "genaiplatform-farm-subscription-key": "73620a9fe1d04540b9aabe89a2657a61",
    },
)

# Ask GPT to understand the user instruction and generate a shell command
# ai_shell_agent/ai_command.py
def ask_ai_for_command(user_input: str, memory: list = None) -> dict:
    system_prompt = get_system_prompt()

    # Prepare message history
    messages = [{"role": "system", "content": system_prompt}]
    
    if memory:
        for user_msg, ai_msg in memory:
            messages.append({"role": "user", "content": user_msg})
            messages.append({"role": "assistant", "content": ai_msg})
    
    messages.append({"role": "user", "content": user_input})

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            extra_query={"api-version": "2024-08-01-preview"},
            temperature=0.3,
            response_format={"type": "json_object"}  # ✅ Force JSON response
        )

        content = response.choices[0].message.content.strip()
        
        # Parse JSON response
        ai_response = json.loads(content)
        
        # Validate required fields
        if "final_command" not in ai_response:
            ai_response["final_command"] = ai_response.get("command", content)
        
        return {
            "ai_response": ai_response,
            "raw_ai_output": content
        }

    except json.JSONDecodeError as e:
        # Fallback: treat raw response as command
        print(f"JSON parsing failed: {e}")
        print(f"Raw response: {content}")
        
        # Create JSON structure from plain command
        fallback_response = {
            "final_command": content,
            "explanation": "Command generated (JSON parsing failed)"
        }
        
        return {
            "ai_response": fallback_response,
            "raw_ai_output": content
        }
        
    except Exception as e:
        print(f"AI API call failed: {e}")
        return None