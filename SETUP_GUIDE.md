# OpsPilot Setup Guide

This guide takes you from a fresh machine to a running OpsPilot, one step at a time. For a shorter version, see the Quick start in [README.md](README.md).

## 1. Prerequisites

| Tool | Version | Check with |
|---|---|---|
| Python | 3.9 or newer (3.11 recommended) | `python3 --version` (macOS/Linux) or `python --version` (Windows) |
| git | any recent | `git --version` |

Where to get them:

- **Python**: https://www.python.org/downloads/. On Windows, tick **"Add Python to PATH"** in the installer.
- **git**: https://git-scm.com/downloads

## 2. Get the code

```bash
git clone https://github.com/Anurag-5ingh/OpsPilot.git
cd OpsPilot
```

## 3. Create a virtual environment

A virtual environment keeps OpsPilot's packages separate from the rest of your system.

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell)**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

When it's active, your prompt starts with `(.venv)`. Activate it again in every new terminal before running OpsPilot.

> **Windows: "running scripts is disabled on this system"?** Run this once, then try again:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

## 4. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**If this fails with `401` or "No matching distribution found":** your pip is set to use a private package index. Install from public PyPI instead:

```bash
pip install --index-url https://pypi.org/simple -r requirements.txt
```

Optionally, check that everything imports:

```bash
python tools/smoke_imports.py
```

Every line should say `ok`.

## 5. Configure (optional)

OpsPilot runs without any configuration. To change settings, create a `.env` file in the project root (it's git-ignored):

```bash
# Port to serve on (default 8080)
PORT=8080

# Flask session secret. Change it if anyone else can reach the server.
APP_SECRET=replace-with-a-long-random-string

# Set to false to disable guest mode (the local terminal)
# OPSPILOT_LOCAL_TERMINAL=false
```

The full list of settings is in [README.md](README.md#configuration).

**About the AI:** AI suggestions need an OpenAI-compatible API key. The easiest way is to copy the example file and fill it in:

```bash
cp .env.example .env        # Windows: copy .env.example .env
```

Then set `OPENAI_API_KEY` (and `OPENAI_BASE_URL` if you don't use OpenAI itself). Without a key, everything except the AI suggestions still works.

## 6. Run

```bash
python app.py
```

Wait for this line:

```
 * Running on http://127.0.0.1:8080
```

Then open **http://127.0.0.1:8080/opspilot** in your browser. To stop the server, press `Ctrl+C`.

## 7. Connect a terminal

Pick one of these on the login card.

**Guest mode (no server needed, macOS/Linux)**
- Click **Guest Mode (Local Terminal)**.
- A terminal opens on your own machine, running as your user.

**SSH to a server**
- Enter the host and username, plus a password if you use one, and click **Connect**.
- Or click **Profiles** to save a reusable connection. See [docs/SSH.md](docs/SSH.md).

Then type a request in the chat, for example "show the 5 largest files in my home folder", and run the command it suggests.

## Troubleshooting

| Problem | Fix |
|---|---|
| `python: command not found` | Use `python3` (macOS/Linux) or `py` (Windows), or reinstall Python with "Add to PATH" ticked. |
| `ModuleNotFoundError` when starting | The virtual environment isn't active. Run the activate command from step 3, then run `python app.py` again. |
| `Address already in use` | Port 8080 is taken. Run `PORT=8081 python app.py` (or `$env:PORT=8081; python app.py` on Windows). |
| No **Guest Mode** button | Open the page as `127.0.0.1` or `localhost` from the same machine. Guest mode isn't available on Windows or in Docker. |
| SSH connection fails | Test it outside OpsPilot first: `ssh -v user@host`. |
| AI suggestions fail | Set `OPENAI_API_KEY` in `.env` and restart. For Azure or another provider, also set `OPENAI_BASE_URL` (see the README's AI provider section). |
