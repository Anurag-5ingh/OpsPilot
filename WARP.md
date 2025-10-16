# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Common Development Commands

### Setup & Installation
```powershell
# Create virtual environment (Windows)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### Running the Application
```powershell
# Web server (main application)
python app.py
# Runs on http://localhost:8080, UI at http://localhost:8080/opspilot

# CLI interface (alternative)
python main.py
```
- **Flask Web Application** (`app.py`) - Main entry point serving REST API and WebSocket terminal
- **AI Shell Agent** (`ai_shell_agent/`) - Modular backend with intelligent capabilities:
  - **Command Generation** - Converts natural language to system-specific shell commands using GPT-4o-mini
  - **Troubleshooting** - Multi-step error analysis with server-aware diagnostics, fixes, and verification
  - **System Awareness** - Server profiling and context-aware command optimization
  - **SSH Management** - Remote command execution and session management
  - **Shared Utilities** - Conversation memory, common functions
- **Frontend** (`frontend/`) - Vanilla JavaScript SPA with modular components (terminal, command/troubleshoot modes)

**Data Flow:**
1. User submits natural language via web UI or CLI
2. AI modules process requests with server context awareness
3. Commands execute over SSH connections with safety validation
4. Results display in web terminal or return to CLI

## Development Workflow & Testing

### Frontend Development
- Modular JavaScript architecture: `main.js` orchestrates `command-mode.js`, `troubleshoot-mode.js`, `terminal.js`
- Real-time terminal uses Socket.IO + xterm.js + Paramiko SSH backend
- Two primary modes: Command generation and troubleshooting workflows

### Backend Development  
- Modular structure under `ai_shell_agent/modules/` for easy extension
- AI handlers use OpenAI GPT-4o-mini via Bosch internal endpoint with system-aware prompts
- System awareness profiles servers (OS, package managers, services, software) for optimal commands
- Conversation memory limited to 20 entries for performance
- SSH operations with safety validation and risk assessment
- Comprehensive error handling with fallback responses

### System Awareness Architecture
- **ServerProfiler** - Discovers OS, package managers, services, installed software via SSH
- **SystemContextManager** - Caches profiles and enhances AI prompts with server context
- **Context-Aware Commands** - Generates system-specific commands (apt vs yum, systemctl vs service)
- **Intelligent Troubleshooting** - Provides OS-specific diagnostics and solutions

## Environment & Configuration

### Prerequisites
- Python 3.8+ with pip
- Node.js (for testing dependencies)
- SSH access to target servers

### Environment Variables
```powershell
# Optional configuration (PowerShell syntax)
$env:APP_SECRET = "your-flask-secret-key"
$env:REMOTE_HOST = "default-ssh-host"
$env:REMOTE_USER = "default-ssh-username"  
$env:REMOTE_PORT = "22"
```

### Local Development Setup
1. Create Python virtual environment and install dependencies
2. Configure environment variables if needed
3. Start Flask app (`python app.py`)
4. Access web UI at http://localhost:8080/opspilot

## API Surface

### Command Generation
- `POST /ask` - Generate shell command from natural language
- `POST /run` - Execute command via SSH

### Error Troubleshooting
- `POST /troubleshoot` - Analyze error and create remediation plan  
- `POST /troubleshoot/execute` - Execute diagnostic/fix/verification steps

### Command Safety & Recovery
- `POST /analyze-failure` - Analyze failed commands and suggest intelligent alternatives
- Built-in risk analysis with warning popups for dangerous commands
- Intelligent fallback mechanism for command failures

### SSH Management
- `GET /ssh/list` - List saved SSH connections
- `POST /ssh/save` - Save SSH connection
- `DELETE /ssh/delete/<id>` - Delete SSH connection

### System Awareness
- `POST /profile` - Profile server capabilities and configuration
- `GET /profile/summary` - Get current server profile summary
- `GET /profile/suggestions/<category>` - Get server-specific command suggestions


### WebSocket Events (Terminal)
- `start_ssh` - Establish SSH session
- `terminal_input` - Send terminal keystrokes
- `terminal_output` - Receive terminal output
- `resize` - Update terminal dimensions

## Technology Stack & Dependencies

### Backend
- **Python 3.x** - Core runtime
- **Flask + Flask-SocketIO** - Web framework with WebSocket support
- **Paramiko** - SSH client implementation
- **OpenAI API** - AI command generation and troubleshooting
- **Eventlet** - Async execution support

### Frontend  
- **Vanilla JavaScript** - No framework dependencies
- **Socket.IO Client** - WebSocket communication
- **xterm.js** - Terminal emulator component


### Deployment
- **Docker** support via `Dockerfile` (Python 3.11-slim base)

## Module-Specific Notes

### AI Integration
- Uses Bosch internal GPT-4o-mini endpoint (configured in `ai_handler.py` files)
- Temperature settings: 0.3 for commands, 0.2 for troubleshooting
- System-aware prompt enhancement based on server profiles
- Context-driven command optimization for different OS/distributions
- To change AI provider, update `ai_shell_agent/modules/*/ai_handler.py` files

### System Awareness Benefits
- **Precise Commands**: Generates OS-specific commands (Ubuntu: `apt install`, CentOS: `yum install`)
- **Service Management**: Uses correct service manager (systemctl vs service vs rc-service)
- **Software Detection**: Leverages installed tools for better troubleshooting
- **Security Context**: Considers sudo availability and user permissions
- **Error Analysis**: Provides distribution-specific error diagnosis and solutions

### Advanced Safety Features
- **Smart Warning System**: Detects risky commands and shows detailed impact warnings
- **Risk Analysis**: Categorizes commands by risk level (low/medium/high/critical)
- **Collapsible Details**: Click-to-expand detailed risk information and safety recommendations
- **Confirmation Gates**: High-risk commands require explicit user acknowledgment
- **Impact Assessment**: Shows affected areas, potential consequences, and safety measures

### Intelligent Fallback System
- **Failure Analysis**: Automatically analyzes why commands failed
- **Root Cause Detection**: Identifies specific failure categories (permissions, missing packages, etc.)
- **Smart Alternatives**: Suggests system-specific alternative commands with success probability
- **Reasoning**: Explains why alternatives will work and potential side effects
- **One-Click Execution**: Execute suggested alternatives directly from the interface

### SSH Security
- Supports both key-based and password authentication
- User confirmation required for command execution
- Risk-level assessment prevents dangerous operations
