# main.py
from ai_shell_agent.main_runner import main as cli_main
from ai_shell_agent.shell_runner import run_shell  # ✅ fixed function name

def main_with_prompt(prompt: str) -> str:
    return run_shell(prompt)  # ✅ updated call

if __name__ == "__main__":
    cli_main()
