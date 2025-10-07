# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

Project overview
- Python Flask app with Socket.IO for a real-time SSH terminal and an AI-powered command generator.
- Backend in Python under ai_shell_agent/ and app.py; minimal frontend assets in frontend/.
- No existing WARP.md, CLAUDE/Cursor/Copilot rule files, or test suite found.

Commands (Windows PowerShell)
- Create and activate a virtualenv, then install dependencies
```powershell path=null start=null
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

- Run the web server (dev)
```powershell path=null start=null
python app.py
# Serve at http://localhost:8080 ; UI at http://localhost:8080/opspilot
```

- Run the local CLI (interactive flow that generates and executes commands over SSH)
```powershell path=null start=null
python main.py
```

- Optional environment variables (used by server/SSH helpers)
```powershell path=null start=null
$env:APP_SECRET = "dev_secret_change_me"         # Flask secret key (server-side sessions)
$env:REMOTE_HOST = "10.0.0.1"                    # Fallback host for run_shell when no client passed
$env:REMOTE_USER = "ubuntu"                      # Fallback user for run_shell when no client passed
$env:REMOTE_PORT = "22"                          # Optional (defaults to 22)
```

- One-off remote command via HTTP (backend /run)
```powershell path=null start=null
# Replace values as needed
curl -s -X POST http://localhost:8080/run -H "Content-Type: application/json" -d '{
  "host": "10.0.0.1",
  "username": "ubuntu",
  "command": "echo connected"
}'
```

- Generate a command from the AI endpoint (/ask) — returns JSON with ai_command
```powershell path=null start=null
curl -s -X POST http://localhost:8080/ask -H "Content-Type: application/json" -d '{
  "prompt": "list files in home"
}'
```

Notes on build, lint, and tests
- Build: Not required for Python runtime; no build system configured.
- Lint/format: No linters/configs detected in the repo.
- Tests: No test suite/configuration detected; no single-test command available.

High-level architecture
- Web app (app.py)
  - Flask app with routes:
    - / redirects to /opspilot (static UI served from frontend/).
    - /opspilot and /<path> serve static assets (expects frontend/index.html and related assets; app.js is present).
    - POST /ask: accepts { prompt }, calls the AI to produce a structured JSON with final_command, and returns the command.
    - POST /run: executes a one-off SSH command using create_ssh_client and run_shell; returns { output, error }.
    - /dashboard: simple informational page.
  - Socket.IO events for interactive SSH terminal:
    - start_ssh initializes a Paramiko client and invokes a shell channel; associates session by Socket.IO sid; spawns a reader thread that streams stdout/stderr to the client.
    - terminal_input sends keystrokes to the SSH channel; resize adjusts channel pty size; disconnect cleans up.
  - Session management: in-memory dict ssh_sessions keyed by Socket.IO sid; reader thread relays data to the browser.

- AI command generation (ai_shell_agent/ai_command.py)
  - Loads environment via python-dotenv.
  - Uses an OpenAI-compatible client to request a JSON-only response guided by prompt_config.get_system_prompt().
  - Normalizes responses to ensure ai_response.final_command exists; returns both parsed JSON and raw output.

- Prompt config (ai_shell_agent/prompt_config.py)
  - System prompt forces assistants to return a single JSON object with fields like steps, action, filename, directory, final_command, requires_directory_resolution.

- SSH helpers (ai_shell_agent/shell_runner.py)
  - create_ssh_client(host, user, port=22): establishes a Paramiko SSHClient.
  - run_shell(command, ssh_client=None): executes a command via exec_command; if ssh_client is None, falls back to REMOTE_HOST/REMOTE_USER/REMOTE_PORT from environment, creates a client, and closes it after execution.

- Conversation memory (ai_shell_agent/conversation_memory.py)
  - Simple ring buffer (max_entries configurable) storing (user_prompt, ai_response) tuples; used to provide context for the AI.

- CLI entrypoints
  - ai_shell_agent/main_runner.py: interactive loop prompting for remote host/user, generating a command via ask_ai_for_command, asking for confirmation, executing via run_shell, and persisting the interaction in memory.
  - main.py: exposes main_with_prompt(prompt) and runs the CLI main() when executed directly.

- Frontend (frontend/app.js)
  - Minimal SPA-like behavior:
    - Login/connect step: uses POST /run to test SSH, then initializes Socket.IO and xterm.js for a live terminal.
    - Chat input calls POST /ask, displays the AI-suggested command, and on confirmation streams it to the terminal via terminal_input.

Operational assumptions and caveats
- The server runs on port 8080 by default (see app.py). The Socket.IO integration is initialized, and endpoints assume availability of frontend assets in frontend/ (index.html should exist for /opspilot).
- The AI client is configured in code; if you need to point to a different provider or credentials, adjust ai_shell_agent/ai_command.py appropriately.
- For non-interactive, single-command execution, prefer POST /run. For interactive sessions, use the UI’s terminal which relies on Socket.IO start_ssh/terminal_input.
