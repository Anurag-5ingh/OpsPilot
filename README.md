# OpsPilot

[![CI](https://github.com/Anurag-5ingh/OpsPilot/actions/workflows/ci.yml/badge.svg)](https://github.com/Anurag-5ingh/OpsPilot/actions/workflows/ci.yml)

**Live demo:** https://anurag-5ingh.github.io/OpsPilot/app/ (the real UI with a simulated terminal and sample AI answers, runs entirely in your browser)

**Project page:** https://anurag-5ingh.github.io/OpsPilot/

OpsPilot is an AI DevOps assistant in your browser. It gives you a live terminal next to an AI chat: describe what you want in plain English, get a shell command back, and run it in the terminal. It also walks you through troubleshooting errors and analyzes Jenkins build logs.

The terminal can connect two ways:

- **SSH mode** connects to a remote server, either directly or through a saved profile.
- **Guest mode** opens a shell on your own machine, with no SSH or server needed.

---

## Quick start

You need **Python 3.9+** (3.11 recommended) and **git**.

### macOS / Linux

```bash
git clone https://github.com/Anurag-5ingh/OpsPilot.git
cd OpsPilot

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env      # then set OPENAI_API_KEY in .env (optional)
python app.py
```

### Windows (PowerShell)

```powershell
git clone https://github.com/Anurag-5ingh/OpsPilot.git
cd OpsPilot

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

copy .env.example .env    # then set OPENAI_API_KEY in .env (optional)
python app.py
```

When you see `Running on http://127.0.0.1:8080`, open:

**http://127.0.0.1:8080/opspilot**

To stop the server, press `Ctrl+C`.

The UI and terminals (including guest mode) work without an AI key. You only need `OPENAI_API_KEY` for AI command suggestions and troubleshooting. See [AI provider](#ai-provider).

> **Install fails with `401` or "No matching distribution"?** Your pip is probably set to use a private package index. Install from public PyPI instead:
> `pip install --index-url https://pypi.org/simple -r requirements.txt`

---

## Using OpsPilot

### Guest mode (local terminal)

Use this to try OpsPilot without a server.

1. Open http://127.0.0.1:8080/opspilot.
2. On the login card, click **Guest Mode (Local Terminal)**.
3. A terminal opens on the right, running your own shell. Type in it directly, or ask the AI chat for a command.

Things to know:

- The shell runs **as the user who started `app.py`**, in your home directory. Anything you run there, or approve from the AI, runs on your machine.
- The button only appears when the browser is on the **same machine** as the server. Requests from other machines, or through a reverse proxy, are refused.
- It works on **macOS and Linux** only. On Windows the button is hidden, but SSH mode still works.
- AI suggestions are generic in guest mode, because server profiling only works over SSH.
- To turn it off, set `OPSPILOT_LOCAL_TERMINAL=false`.

### SSH mode (remote server)

**Quick connect:** on the login card, enter the host, username and (optionally) a password, then click **Connect**. If you leave the password empty, your SSH keys and agent are used.

**Saved profiles** are the better choice for servers you use often:

1. Click **Profiles**, then **Add Profile**.
2. Fill in the name, host, port, username and auth method (SSH agent, key file, password, or keyboard-interactive for MFA). A bastion/jump host is optional.
3. Click **Test Connection**, then **Save Profile**.
4. Back on the login card, pick the profile and click **Connect with Profile**.

Profile details are saved to `ai_shell_agent/data/ssh_profiles.json`. Passwords and passphrases are stored separately, in your OS keyring or an encrypted file. See **[docs/SSH.md](docs/SSH.md)** for keys, agents, MFA and bastion hosts.

After you connect, OpsPilot profiles the server (OS, package manager, service manager) so the AI suggests commands that fit it.

### Chat modes

- **Command**: describe a task (for example "show disk usage by folder"). The AI suggests a command with a risk analysis, and you can run it in the terminal.
- **Troubleshoot**: paste an error. The AI proposes diagnostic commands, then fixes and verification steps based on the output.
- **Logs** (header tab): connect Jenkins and analyze a build's console log. See **[docs/CICD_INTEGRATION.md](docs/CICD_INTEGRATION.md)**.

### CLI (optional)

```bash
python main.py
```

This is a text-only version. It asks for a host and username, then lets you request and run commands over SSH.

---

## Configuration

All settings are optional environment variables. You can also put them in a `.env` file in the project root (start from `.env.example`). That file is git-ignored.

| Variable | Default | What it does |
|---|---|---|
| `OPENAI_API_KEY` | *(unset)* | API key for AI features. Without it the app runs, but AI requests fail. |
| `OPENAI_BASE_URL` | OpenAI's API | Use any OpenAI-compatible endpoint (Azure OpenAI, a gateway, a local model server). |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model name to request. |
| `OPENAI_API_VERSION` | *(unset)* | Azure OpenAI only: sent as the `api-version` query parameter. |
| `OPENAI_EXTRA_HEADERS` | *(unset)* | Extra request headers as JSON, e.g. `{"my-gateway-key": "..."}`. |
| `PORT` | `8080` | Port the server listens on. |
| `HOST` | `127.0.0.1` | Address to bind. Use `0.0.0.0` to expose it on your network (see Security). |
| `OPSPILOT_LOCAL_TERMINAL` | `true` | Set to `false` to disable guest mode. |
| `OPSPILOT_CORS_ORIGINS` | *(empty)* | Comma-separated list of extra origins allowed to call the API. By default only the app's own page can. |
| `OSPILOT_SSH_ENHANCED` | `true` | Profile-based SSH with host key handling and secure secrets. |
| `OSPILOT_MASTER_KEY` | *(auto)* | Encryption key for stored secrets when no OS keyring is available. |
| `APP_SECRET` | `dev_secret_change_me` | Flask session secret. **Change this** if anyone else can reach the server. |
| `REMOTE_HOST`, `REMOTE_USER`, `REMOTE_PASSWORD`, `REMOTE_PORT` | *(unset)* | Legacy fallback SSH target, used only when no host or profile is given. |

Examples:

```bash
PORT=9000 python app.py                       # macOS / Linux
```
```powershell
$env:PORT=9000; python app.py                 # Windows PowerShell
```

### AI provider

OpsPilot works with any OpenAI-compatible API. Set it up in `.env`:

```bash
# OpenAI
OPENAI_API_KEY=sk-...

# Azure OpenAI (example)
OPENAI_API_KEY=your-azure-key
OPENAI_BASE_URL=https://YOUR-RESOURCE.openai.azure.com/openai/deployments/YOUR-DEPLOYMENT
OPENAI_API_VERSION=2024-08-01-preview
```

Without a key, or if the endpoint isn't reachable, the UI and terminals still work, but AI suggestions fail. The client is set up in `ai_shell_agent/modules/shared/ai_client.py`.

---

## Docker

```bash
docker build -t opspilot .
docker run --rm -p 8080:8080 opspilot
```

Then open http://127.0.0.1:8080/opspilot. The image sets `HOST=0.0.0.0` so the port mapping works.

Guest mode isn't available inside Docker. The browser's connection reaches the container from the Docker network, not from loopback, so it's refused. Use SSH mode instead.

---

## Security

OpsPilot runs real shell commands, so treat it like an open terminal.

- **Keep it local.** The server binds to `127.0.0.1` by default. Only set `HOST=0.0.0.0` on a network you trust: the API has **no login**, and anyone who can reach it can run commands over SSH.
- **Guest mode** gives a full shell as your user, but only to browsers on the same machine.
- **Review AI commands before running them.** The risk analysis is a guide, not a guarantee.
- **SSH host keys**: quick connect auto-accepts unknown host keys. For servers you care about, use a profile with host key verification set to `ask` or `yes`.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `pip install` fails with 401 / no matching distribution | Use public PyPI: `pip install --index-url https://pypi.org/simple -r requirements.txt` |
| Page doesn't load | Check the terminal running `app.py` says `Running on http://127.0.0.1:8080`, and use that exact host and port. |
| `Address already in use` | Another process has port 8080. Start with a different port, e.g. `PORT=8081 python app.py`. |
| No **Guest Mode** button | Open the page as `127.0.0.1` or `localhost` on the same machine. Guest mode isn't available on Windows, in Docker, or with `OPSPILOT_LOCAL_TERMINAL=false`. |
| SSH connect fails | Test from your shell first with `ssh -v user@host`. With key auth, the server process must be able to read the key file. |
| AI requests fail | Set `OPENAI_API_KEY` (and `OPENAI_BASE_URL` for non-OpenAI endpoints) in `.env`, then restart. See [AI provider](#ai-provider). |
| `NotOpenSSLWarning` / `TripleDES` warnings at startup | Harmless. They come from the system Python and from paramiko. |

---

## Project layout

```
OpsPilot/
├── app.py                      # Flask + Socket.IO server: REST API, web UI, terminal sessions
├── main.py                     # CLI entry point
├── requirements.txt
├── Dockerfile
├── ai_shell_agent/
│   ├── api/endpoints/
│   │   └── troubleshooting.py  # /troubleshoot/analyze, /suggest-fix, /verify
│   ├── modules/
│   │   ├── ssh/                # SSH client, profiles, secrets, host keys, local_terminal.py (guest mode)
│   │   ├── command_generation/ # AI command generation, risk analysis, ML risk scorer
│   │   ├── troubleshooting/    # AI troubleshooting and the step workflow
│   │   ├── system_awareness/   # Server profiling (OS, package/service manager)
│   │   ├── cicd/               # Jenkins / Ansible integration, build log analysis
│   │   ├── security/           # Command compliance checks (CIS / NIST / custom)
│   │   ├── documentation/      # Runbook and guide generation
│   │   └── shared/             # AI client, conversation memory
│   ├── utils/prompt_helpers.py
│   └── data/                   # Created at runtime: profiles, secrets, known_hosts, cicd.db
├── frontend/                   # Static web UI (no build step; refresh to see edits)
│   ├── index.html
│   ├── terminal/terminal.js    # xterm.js terminal over Socket.IO (SSH and guest mode)
│   ├── chat/                   # Command / troubleshoot chat
│   ├── cicd/                   # Logs mode
│   └── shared/                 # Styles, profiles UI, shared state
├── docs/                       # SSH and CI/CD guides
└── tools/smoke_imports.py      # Checks that all dependencies and modules import
```

---

## API reference

The web UI uses these endpoints. They're also handy for scripting.

**Terminal (Socket.IO events)**
- `start_local` starts a guest-mode local shell.
- `start_ssh` starts an SSH session: `{ip, user, password}` or `{profileId}`.
- `terminal_input` sends keystrokes: `{input}`.
- `resize` resizes the terminal: `{cols, rows}`.
- The server emits `terminal_output` with `{output}`.

**Commands**
- `POST /ask` turns a description into a command: `{prompt}`.
- `POST /run` runs one command over SSH: `{host, username, password?, port?, command}`.
- `POST /analyze-failure` analyzes a failed command.
- `GET /guest/status` reports whether guest mode is available to this browser.

**Troubleshooting**
- `POST /troubleshoot` builds a multi-step plan from `{error_text, host, username, context?}`.
- `POST /troubleshoot/execute` runs diagnostic, fix or verification commands.
- `POST /troubleshoot/analyze`, `/troubleshoot/suggest-fix` and `/troubleshoot/verify` are used by the chat UI.

**SSH profiles**
- `GET /ssh/list`
- `POST /ssh/save`
- `POST /ssh/test`
- `DELETE /ssh/delete/<id>`

**Server profiling**
- `POST /profile`
- `GET /profile/summary`
- `GET /profile/suggestions/<category>`

**CI/CD**: Jenkins and Ansible config, console fetch and AI analysis are under `/cicd/*`. See [docs/CICD_INTEGRATION.md](docs/CICD_INTEGRATION.md).

**Other**
- `/ml/train`, `/ml/status` and `/ml/feedback` for the risk-scoring model (see [ML_DATA_FLOW.md](ML_DATA_FLOW.md)).
- `/security/*` for compliance checks.
- `/documentation/*` for generated runbooks.

---

## Development

- Edits to `frontend/` show up when you refresh the browser. Python changes need a server restart.
- Smoke-test imports after changing dependencies: `python tools/smoke_imports.py`
- More docs: [SETUP_GUIDE.md](SETUP_GUIDE.md) (step-by-step setup), [docs/SSH.md](docs/SSH.md), [docs/CICD_INTEGRATION.md](docs/CICD_INTEGRATION.md), [CICD_SETUP_GUIDE.md](CICD_SETUP_GUIDE.md), [ML_DATA_FLOW.md](ML_DATA_FLOW.md).
