#!/bin/bash
# OpsPilot Dependencies Installation Script for WSL

echo "=== Installing OpsPilot Dependencies ==="

# Method 1: Try using python3 -m pip (most reliable)
echo "Trying python3 -m pip..."
python3 -m pip install eventlet flask flask-socketio paramiko openai python-dotenv

# Alternative method if the above fails
echo "If the above fails, try these commands one by one:"
echo "sudo apt update"
echo "sudo apt install python3-pip -y"
echo "pip3 install eventlet flask flask-socketio paramiko openai python-dotenv"

echo "=== Installation Complete ==="
echo "Now try: python3 app.py"

