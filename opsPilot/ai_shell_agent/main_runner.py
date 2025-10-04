# main_runner.py
from ai_shell_agent.ai_command import ask_ai_for_command
from ai_shell_agent.shell_runner import run_shell, create_ssh_client
from ai_shell_agent.conversation_memory import ConversationMemory
import paramiko

def main():
    print("AI Local Shell — type 'exit' to quit\n")

    # Initialize conversation memory
    memory = ConversationMemory(max_entries=20)

    # Prompt for SSH details
    remote_host = input("Enter REMOTE_HOST (e.g., 10.0.0.1): ").strip()
    remote_user = input("Enter REMOTE_USER (e.g., ubuntu): ").strip()

    # Try to establish SSH connection
    ssh = create_ssh_client(remote_host, remote_user)
    if not isinstance(ssh, paramiko.SSHClient):
        print("SSH client was not properly initialized. Exiting.")
        return

    while True:
        user_input = input("What do you want to do? ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break

        result = ask_ai_for_command(user_input, memory.get())
        if not result:
            print("Failed to get a valid response from AI.")
            continue

        ai_response = result["ai_response"]
        raw_ai_output = result.get("raw_ai_output", "")
        command = ai_response.get("final_command")

        if not command:
            print("No command was generated.")
            continue

        print(f"AI Suggested command:\n{command}\n")
        confirm = input("Run this command? (yes/no): ").strip().lower()
        
        if confirm == "yes":
            print(f"Running: {command}")
            output, error = run_shell(command, ssh)

            if error:
                print("Error:\n", error)
            elif output:
                print("Output:\n", output)
            else:
                print("ℹ️ Output:\n(No output)")

        # Add interaction to memory
        memory.add(user_input, raw_ai_output)

    ssh.close()

if __name__ == "__main__":
    main()
