# OpsPilot Setup Guide

## Prerequisites
### 1. Install Python 3.8 or higher
   - Download from: https://www.python.org/downloads/
   - Make sure to check "Add Python to PATH" during installation
   - Verify installation: `python --version`

### 2. Install Git (if not already installed)
   - Download from: https://git-scm.com/downloads

## Installation Instructions

### Step 1: Install Python Dependencies

Run these commands in your terminal:

```bash
# Navigate to the project directory
cd path/to/OpsPilot-main

# Install required packages
pip install -r requirements.txt
```

If pip doesn't work, try:
```bash
python -m pip install -r requirements.txt
```

### Step 2: Environment Setup

Create a `.env` file in the `opsPilot` directory:

```bash
# SSH Configuration
REMOTE_HOST=your-ssh-host
REMOTE_USER=your-ssh-username
REMOTE_PORT=22

# OpenAI Configuration (Required for AI functionality)
OPENAI_API_KEY=your-openai-api-key-missing-from-code

# Optional: Change secret key for production
APP_SECRET=your-secret-key-for-flask-sessions
```

### Step 3: Run the Application

#### Web Interface:
```bash
cd opsPilot
python app.py
```
Then visit: http://localhost:8080

#### CLI Interface:
```bash
cd opsPilot
python main.py
```

## Required Environment Variables

Your code is configured to use Bosch internal AI API, but you need these environment variables:

1. **SSH Credentials**: SSH connection details for the target server
2. **OpenAI API Key**: Based on your ai_command.py, you're using Bosch internal GPT-4o-mini
3. **Secret Key**: Flask secret key for sessions

## Important Notes

1. **SSH Requirements**: Your application requires SSH key-based authentication or password
2. **Network Access**: Ensure your network allows SSH connections to target servers
3. **Port**: Default web interface runs on port 8080
4. **No Database Required**: Application runs without database dependencies

## Troubleshooting

### Python Not Found
- Ensure Python is added to your PATH environment variable
- Try `python3` instead of `python`
- On Windows, try `py` command

### SSH Connection Issues
- Verify SSH credentials
- Check SSH key permissions (should be readable)
- Test SSH connection manually: `ssh username@host`

### Package Installation Issues
- Try upgrading pip: `python -m pip install --upgrade pip`
- Use virtual environment: `python -m venv venv` then `venv\Scripts\activate` (Windows)

## Features Available After Installation

✅ Web-based SSH terminal interface
✅ AI-powered command generation
✅ SSH connection management
✅ Real-time terminal via WebSocket
✅ CLI interface for direct SSH access

## Missing/Dependencies Issues

If you encounter import errors, install missing packages:

```bash
pip install flask flask-socketio eventlet paramiko openai python-dotenv
```

