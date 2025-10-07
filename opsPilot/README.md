# OpsPilot

OpsPilot is a Python Flask application that provides:
- An AI-powered command generator that turns natural language into shell commands.
- A real-time, web-based SSH terminal using Socket.IO and Paramiko.
- A simple CLI for interactive AI-assisted remote command execution.

Frontend assets live under frontend/ (served from /opspilot). Backend code is primarily in ai_shell_agent/ and app.py.

## Quickstart (Windows PowerShell)

1) Create a virtual environment and install dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2) Run the web server

```powershell
python app.py
```

- App runs at http://localhost:8080
- UI is available at http://localhost:8080/opspilot

3) Run the interactive CLI (optional)

```powershell
python main.py
```

## Configuration

Environment variables (optional):
- APP_SECRET: Flask secret key (default: dev_secret_change_me)
- REMOTE_HOST: Default host for non-interactive command execution
- REMOTE_USER: Default user for non-interactive command execution
- REMOTE_PORT: Default port (22 if unset)

Example (PowerShell):
```powershell
$env:APP_SECRET = "dev_secret_change_me"
$env:REMOTE_HOST = "10.0.0.1"
$env:REMOTE_USER = "ubuntu"
$env:REMOTE_PORT = "22"
```

## API

- POST /ask
  - Body: { "prompt": "your instruction" }
  - Returns: { "ai_command": "generated shell command", "original_prompt": "..." }

- POST /run
  - Body: { "host": "x.x.x.x", "username": "user", "command": "echo hello" }
  - Returns: { "output": "...", "error": "..." }

## Real-time SSH terminal

The web UI uses Socket.IO to establish a live SSH session:
- start_ssh: opens the SSH session and pty
- terminal_input: streams keystrokes to the remote shell
- resize: updates terminal dimensions
- disconnect: cleans up the session

## Project structure (high level)

- app.py: Flask app, HTTP routes, Socket.IO events for SSH terminal
- ai_shell_agent/: AI integration, SSH helpers, CLI loop, conversation memory
- frontend/: Static assets (index.html expected, app.js provided)
- main.py: CLI entrypoint

## Notes
- No test suite or lint configuration is included yet.
- If you change AI provider or credentials, update ai_shell_agent/ai_command.py accordingly.
