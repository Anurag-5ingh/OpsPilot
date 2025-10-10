# OpsPilot - AI-Powered DevOps Assistant

OpsPilot is an intelligent DevOps assistant with two powerful features:

## 🚀 Features

### 1. **Command Generation** 
AI-powered command generator that turns natural language into shell commands.

### 2. **Error Troubleshooting**
Multi-step error analysis and remediation with diagnostics, fixes, and verification.

### 3. **Real-Time SSH Terminal**
Web-based SSH terminal using Socket.IO and Paramiko for live server interaction.

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

## 📁 Project Structure

```
opsPilot/
├── ai_shell_agent/              # Backend (All backend code)
│   ├── modules/                 # Modular organization
│   │   ├── command_generation/  # Feature 1: Command generation
│   │   ├── troubleshooting/     # Feature 2: Error troubleshooting
│   │   ├── ssh/                 # SSH connection module
│   │   └── shared/              # Shared utilities
│   └── main_runner.py           # CLI entry point
├── frontend/                    # Frontend
│   ├── js/                      # JavaScript modules
│   ├── css/                     # Stylesheets
│   ├── assets/                  # Images and icons
│   └── index.html               # Main HTML
├── app.py                       # Flask application
├── main.py                      # CLI entrypoint
└── requirements.txt             # Dependencies
```

## 📡 API Endpoints

### Command Generation
- **POST /ask** - Generate command from natural language
  - Body: `{ "prompt": "list all files" }`
  - Returns: `{ "ai_command": "ls -la", ... }`

- **POST /run** - Execute command via SSH
  - Body: `{ "host": "10.0.0.1", "username": "ubuntu", "command": "ls" }`
  - Returns: `{ "output": "...", "error": "..." }`

### Troubleshooting
- **POST /troubleshoot** - Analyze error and create remediation plan
  - Body: `{ "error_text": "nginx failed", "host": "...", "username": "..." }`
  - Returns: `{ "analysis": "...", "diagnostic_commands": [...], "fix_commands": [...], ... }`

- **POST /troubleshoot/execute** - Execute troubleshooting workflow steps
  - Body: `{ "commands": [...], "step_type": "diagnostic|fix|verification", ... }`
  - Returns: `{ "results": [...], "all_success": true }`

### SSH Management
- **GET /ssh/list** - List saved SSH connections
- **POST /ssh/save** - Save SSH connection info
- **DELETE /ssh/delete/<id>** - Delete SSH connection

### WebSocket Events (Terminal)
- `start_ssh` - Open SSH session
- `terminal_input` - Send keystrokes
- `terminal_output` - Receive output
- `resize` - Update terminal size
- `disconnect` - Close session

## 🏗️ Architecture

### Backend Modules

**Command Generation** (`ai_shell_agent/modules/command_generation/`)
- Converts natural language to shell commands
- Uses GPT-4o-mini with temperature 0.3
- Returns structured JSON with command and explanation

**Troubleshooting** (`ai_shell_agent/modules/troubleshooting/`)
- Analyzes errors and creates multi-step remediation plans
- Uses GPT-4o-mini with temperature 0.2
- Workflow: Diagnostics → Fixes → Verification
- Risk assessment (low/medium/high)

**SSH** (`ai_shell_agent/modules/ssh/`)
- SSH client creation and management
- Command execution over SSH
- Session management endpoints

**Shared** (`ai_shell_agent/modules/shared/`)
- Conversation memory (max 20 entries)
- Utility functions (path normalization, etc.)

### Frontend Modules

- **main.js** - Application entry point and event listeners
- **utils.js** - Shared state and utilities
- **terminal.js** - SSH terminal functionality
- **command-mode.js** - Command generation UI
- **troubleshoot-mode.js** - Troubleshooting UI

## 🔧 Technology Stack

**Backend:**
- Python 3.x
- Flask - Web framework
- Flask-SocketIO - WebSocket support
- Paramiko - SSH client
- OpenAI API - AI capabilities
- Eventlet - Async support

**Frontend:**
- HTML5, CSS3, Vanilla JavaScript
- Socket.IO Client - WebSocket
- xterm.js - Terminal emulator

## 🎯 Usage

### Web Interface

1. Navigate to `http://localhost:8080/opspilot`
2. Enter SSH credentials (host, username)
3. Choose mode:
   - **Command Mode**: Generate commands from natural language
   - **Troubleshoot Mode**: Analyze and fix errors

### Command Mode
1. Type natural language request: "list all files"
2. AI generates command: `ls -la`
3. Confirm to execute in terminal

### Troubleshoot Mode
1. Paste error message: "nginx: bind() failed"
2. AI analyzes and creates plan:
   - Analysis of root cause
   - Diagnostic commands
   - Fix commands
   - Verification commands
3. Execute steps with confirmation

## 🔐 Security

- SSH key-based or password authentication
- User confirmation required for command execution
- Risk level assessment for troubleshooting
- API key protection for OpenAI
- Flask secret key configuration

## 📝 Notes

- AI provider: OpenAI GPT-4o-mini (Bosch internal endpoint)
- To change AI provider, update `ai_shell_agent/modules/*/ai_handler.py`
- Conversation memory limited to 20 entries for performance
- All features work independently without conflicts
