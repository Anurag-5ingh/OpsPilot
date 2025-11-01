# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

Project overview
- Backend: Flask app with Flask-SocketIO in app.py serving REST endpoints and a WebSocket-powered SSH terminal. Blueprints: SSH profile/session management (ai_shell_agent/modules/ssh/session_manager.py, registered as ssh_bp) and troubleshooting (ai_shell_agent/api/endpoints/troubleshooting.py).
- Core modules (ai_shell_agent/modules):
  - command_generation: AI command generation with risk analysis (ask_ai_for_command) and failure analysis.
  - ssh: SSH client creation, host key policy, secrets storage, connection profiles, and WebSocket session management.
  - troubleshooting: AI-assisted error analysis and a workflow engine.
  - cicd: Jenkins/Ansible config helpers, build log ingestion, background worker.
  - documentation: Smart runbook/troubleshooting/reference generation.
  - security: Compliance checking (CIS/NIST/custom).
  - system_awareness: SystemContextManager for server profiling.
- Frontend: Static vanilla JS served from frontend/ (no bundler/build step). chat/chat-mode.js unifies “command” and “troubleshoot” flows; terminal/terminal.js manages Socket.IO + xterm.js terminal.

Key URLs and WebSocket events
- UI: http://127.0.0.1:8080/opspilot (served by send_from_directory("frontend", "index.html")).
- REST (selected):
  - /ask (POST) → AI command generation
  - /run (POST) → one-off SSH command
  - /analyze-failure (POST) → analyze failed command output
  - /troubleshoot/analyze (POST) → diagnostics/fixes; /troubleshoot/suggest-fix; /troubleshoot/verify
  - /ssh/list, /ssh/test, /ssh/save, /ssh/delete/<id>
  - /ml/train, /ml/status, /ml/feedback
  - /security/check-compliance, /security/frameworks
  - /documentation/generate-* , /documentation/list , /documentation/<id>?format=*
  - CI/CD helpers under /cicd/* (Jenkins/Ansible, logs, builds)
- WebSocket (Socket.IO): start_ssh, terminal_input, resize, disconnect; server emits terminal_output (and auth/hostkey prompts in enhanced mode).

Environment configuration
- PORT (default 8080) controls server port.
- OSPILOT_SSH_ENHANCED=true enables profile-based SSH with host key handling and OS keyring-backed secrets (non-sensitive profile data stored at ai_shell_agent/data/ssh_profiles.json).
- Optional: APP_SECRET (Flask session secret), LOG_LEVEL.

Common commands
- Python setup (recommended virtualenv):
  - Windows PowerShell
    - python -m venv .venv; .\.venv\Scripts\Activate.ps1
    - pip install -r requirements.txt
  - Unix-like shells
    - python -m venv .venv; source .venv/bin/activate
    - pip install -r requirements.txt
- Run server
  - python app.py
  - Change port: $env:PORT=8081; python app.py  (PowerShell)  |  PORT=8081 python app.py  (bash/zsh)
- Open UI: http://127.0.0.1:8080/opspilot
- Quick API smoke checks (PowerShell examples from README)
  - Test SSH (key auth):
    - Invoke-RestMethod -Uri 'http://127.0.0.1:8080/ssh/test' -Method Post -Body (ConvertTo-Json @{ host='your.host'; username='ubuntu'; port=22; auth_method='key'; key_path='C:\\Users\\you\\.ssh\\id_ed25519' }) -ContentType 'application/json'
- Docker
  - docker build -t opspilot .
  - docker run --rm -p 8080:8080 -e PORT=8080 opspilot

Frontend tests (Jest)
- Install deps: npm ci  (or npm install)
- Run all: npm test
- Run a single test file: npx jest frontend/path/to/file.test.js
- Run by name pattern: npx jest -t "pattern"

Linting/formatting
- No linters or formatters are configured in this repo for Python or JS. If needed, run ad-hoc tools locally (e.g., ruff/black or prettier) but there are no project scripts/configs.

High-level architecture map (how pieces fit)
- app.py initializes:
  - ConversationMemory (bounded context window), SystemContextManager (server profiling), MLRiskScorer, SecurityComplianceChecker, SmartDocumentationGenerator, CI/CD analyzer + background worker.
  - Registers ssh_bp and troubleshooting_bp; serves static frontend and index route.
  - WebSocket server (SocketIO in threading mode) that brokers SSH interactive sessions; per-connection reader thread streams SSH stdout/stderr to terminal_output.
- SSH profiles and secrets:
  - Non-sensitive profile data persisted in ai_shell_agent/data/ssh_profiles.json.
  - Sensitive secrets stored via ai_shell_agent/modules/ssh/secrets.py (OS keyring integration); endpoints abstract this away.
- Command generation and safety:
  - ask_ai_for_command composes a final_command with risk analysis; compliance checker can score/flag actions; /ml/* endpoints train and feed back into MLRiskScorer.
- Troubleshooting:
  - AI-assisted analysis returns diagnostics/fixes/verification; frontend can execute diagnostics, capture terminal output, then request suggested fixes.
- CI/CD helpers:
  - Jenkins/Ansible config endpoints store secrets securely, test connections, fetch and analyze logs; a background worker performs periodic tasks.
- Documentation module:
  - Generates runbooks/troubleshooting/reference docs from observed patterns; query via /documentation/*.

Notes for future agents
- Frontend has no build step; edits under frontend/ are picked up live when the Flask server serves static assets.
- Some API blueprints (e.g., orchestration in ai_shell_agent/api/endpoints/orchestration.py) exist but are not currently registered in app.py; expose or wire them up if you need those routes.
- requirements.txt contains a malformed line (pip install -r requirements.txtFlask-CORS==4.0.0). If pip install fails, fix that line locally by splitting Flask-CORS to its own line.
