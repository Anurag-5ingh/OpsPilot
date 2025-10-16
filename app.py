# OpsPilot - AI-Powered DevOps Assistant
# Main Flask application serving REST API and WebSocket terminal

# Eventlet setup for async WebSocket support
import eventlet
eventlet.monkey_patch()

# Core imports
import os
from flask import Flask, request, jsonify, send_from_directory, render_template, redirect, url_for
from flask_socketio import SocketIO, emit
import paramiko
import threading

# Import OpsPilot modules
from ai_shell_agent.modules.command_generation import ask_ai_for_command, analyze_command_failure
from ai_shell_agent.modules.troubleshooting import ask_ai_for_troubleshoot, TroubleshootWorkflow
from ai_shell_agent.modules.ssh import create_ssh_client, run_shell, ssh_bp
from ai_shell_agent.modules.shared import ConversationMemory
from ai_shell_agent.modules.system_awareness import SystemContextManager

# ===========================
# Application Configuration
# ===========================
app = Flask(__name__)

# Flask secret key for session management
# Can be overridden with APP_SECRET environment variable
app.config['SECRET_KEY'] = os.environ.get("APP_SECRET", "dev_secret_change_me")

# Initialize conversation memory to maintain context across interactions
# Limited to 20 entries for performance optimization
memory = ConversationMemory(max_entries=20)

# Initialize system context manager for server-aware command generation
system_context = SystemContextManager()

# Register SSH blueprint for SSH connection management endpoints
app.register_blueprint(ssh_bp)

# ===========================
# Frontend Serving Routes
# ===========================

@app.route("/")
def index():
    """Main route - redirect to OpsPilot interface"""
    return redirect(url_for("serve_index"))

@app.route("/opspilot")
def serve_index():
    """Serve the main OpsPilot web interface"""
    return send_from_directory("frontend", "index.html")

@app.route("/<path:path>")
def serve_static(path):
    """Serve static frontend files (CSS, JS, images)"""
    return send_from_directory("frontend", path)

# ===========================
# Command Generation API
# ===========================

@app.route("/ask", methods=["POST"])
def ask():
    """
    Generate a shell command from natural language input.
    
    Request body:
    {
        "prompt": "natural language request (e.g., 'list all files')"
    }
    
    Returns:
    {
        "ai_command": "generated shell command",
        "original_prompt": "original user input"
    }
    """
    data = request.get_json()
    user_input = data.get("prompt")

    # Validate input
    if not user_input:
        return jsonify({"error": "No prompt provided"}), 400

    # Generate a shell command from natural language using AI with system context
    result = ask_ai_for_command(user_input, memory=memory.get(), system_context=system_context)
    if not result:
        return jsonify({"error": "AI failed to respond"}), 500

    # Extract the generated command from AI response
    ai_response = result.get("ai_response", {})
    command = ai_response.get("final_command")

    if not command:
        return jsonify({"error": "No command generated"}), 400

    # Store the interaction in conversation memory for context
    memory.add(user_input, command)

    return jsonify({
        "ai_command": command,
        "original_prompt": user_input
    })

@app.route("/run", methods=["POST"])
def run_command():
    """
    Execute a shell command on the remote server via SSH.
    
    Request body:
    {
        "host": "remote server hostname/IP",
        "username": "SSH username",
        "password": "SSH password (optional if using keys)",
        "command": "shell command to execute",
        "port": 22 (optional, defaults to 22)
    }
    
    Returns:
    {
        "output": "command output",
        "error": "error output (if any)"
    }
    """
    data = request.get_json()
    host = data.get("host")
    username = data.get("username")
    password = data.get("password")
    command = data.get("command")
    port = data.get("port", 22)

    # Validate required parameters
    if not host or not username or not command:
        return jsonify({"error": "host, username, and command are required"}), 400

    # Create SSH client and execute command
    ssh_client = create_ssh_client(host, username, port, password)
    if ssh_client is None:
        return jsonify({"error": f"SSH connection failed for {username}@{host}"}), 500

    # Execute the command and return results
    output, error = run_shell(command, ssh_client=ssh_client)
    return jsonify({"output": output, "error": error})

@app.route("/analyze-failure", methods=["POST"])
def analyze_failure():
    """
    Analyze a failed command execution and suggest intelligent alternatives.
    
    This endpoint examines why a command failed, provides root cause analysis,
    and suggests system-aware alternative solutions with detailed reasoning.
    
    Request body:
    {
        "original_command": "htop",
        "error_output": "bash: htop: command not found",
        "host": "server hostname/IP (optional for context)",
        "username": "SSH username (optional for context)"
    }
    
    Returns:
    {
        "original_command": "htop",
        "failure_analysis": {
            "categories": ["command_not_found"],
            "root_cause": "The command 'htop' is not installed...",
            "confidence_score": 0.85
        },
        "alternative_solutions": [
            {
                "alternative_command": "sudo apt install htop",
                "reasoning": "Install htop package first",
                "success_probability": 0.8,
                "side_effects": ["Downloads and installs package"]
            }
        ],
        "system_specific_fixes": [...]
    }
    """
    data = request.get_json()
    original_command = data.get("original_command")
    error_output = data.get("error_output")
    host = data.get("host")  # Optional for system context
    username = data.get("username")  # Optional for system context
    
    # Validate required parameters
    if not original_command or not error_output:
        return jsonify({"error": "original_command and error_output are required"}), 400
    
    # Use system context if host info provided (optional enhancement)
    context_to_use = system_context
    if host and username:
        # Could enhance to get specific context for this host
        # For now, use the current system context
        pass
    
    try:
        # Analyze the command failure with intelligent alternatives
        analysis_result = analyze_command_failure(
            original_command, error_output, context_to_use
        )
        
        return jsonify(analysis_result)
        
    except Exception as e:
        return jsonify({
            "error": f"Failure analysis failed: {str(e)}",
            "original_command": original_command
        }), 500

# ===========================
# Troubleshooting API
# ===========================

@app.route("/troubleshoot", methods=["POST"])
def troubleshoot():
    """
    Analyze an error and provide multi-step troubleshooting plan.
    This feature generates diagnostic commands, fix commands, and verification steps.
    
    Request body:
    {
        "error_text": "error message or description",
        "host": "remote host",
        "username": "SSH username",
        "port": 22,
        "context": {
            "last_command": "optional - last command that failed",
            "last_output": "optional - output from last command",
            "last_error": "optional - error from last command"
        }
    }
    
    Returns:
    {
        "analysis": "AI analysis of the error",
        "diagnostic_commands": ["list", "of", "diagnostic", "commands"],
        "fix_commands": ["list", "of", "fix", "commands"],
        "verification_commands": ["list", "of", "verification", "commands"],
        "reasoning": "explanation of the troubleshooting approach",
        "risk_level": "low|medium|high",
        "requires_confirmation": boolean
    }
    """
    data = request.get_json()
    error_text = data.get("error_text")
    host = data.get("host")
    username = data.get("username")
    port = int(data.get("port", 22))
    context = data.get("context", {})
    
    # Validate required parameters
    if not error_text:
        return jsonify({"error": "error_text is required"}), 400
    
    if not host or not username:
        return jsonify({"error": "host and username are required"}), 400
    
    # Get troubleshooting plan from AI with system awareness
    result = ask_ai_for_troubleshoot(error_text, context=context, system_context=system_context)
    
    if not result or not result.get("success"):
        return jsonify({
            "error": "Failed to generate troubleshooting plan",
            "details": (result or {}).get("error", "Unknown error")
        }), 500
    
    # Extract troubleshooting plan components
    troubleshoot_plan = result.get("troubleshoot_response", {})
    
    return jsonify({
        "analysis": troubleshoot_plan.get("analysis"),
        "diagnostic_commands": troubleshoot_plan.get("diagnostic_commands", []),
        "fix_commands": troubleshoot_plan.get("fix_commands", []),
        "verification_commands": troubleshoot_plan.get("verification_commands", []),
        "reasoning": troubleshoot_plan.get("reasoning"),
        "risk_level": troubleshoot_plan.get("risk_level"),
        "requires_confirmation": troubleshoot_plan.get("requires_confirmation")
    })

@app.route("/troubleshoot/execute", methods=["POST"])
def troubleshoot_execute():
    """
    Execute troubleshooting commands (diagnostics, fixes, or verification).
    Uses the TroubleshootWorkflow engine to execute commands with appropriate safety measures.
    
    Request body:
    {
        "commands": ["cmd1", "cmd2", "cmd3"],
        "step_type": "diagnostic|fix|verification",
        "host": "remote host",
        "username": "SSH username",
        "password": "SSH password (optional)",
        "port": 22
    }
    
    Returns:
    {
        "results": [
            {
                "command": "executed command",
                "output": "command output",
                "error": "error output",
                "success": boolean,
                "execution_time": float
            }
        ],
        "all_success": boolean,
        "summary": "execution summary"
    }
    """
    data = request.get_json()
    commands = data.get("commands", [])
    step_type = data.get("step_type", "unknown")
    host = data.get("host")
    username = data.get("username")
    password = data.get("password")
    port = int(data.get("port", 22))
    
    # Validate required parameters
    if not commands:
        return jsonify({"error": "No commands provided"}), 400
    
    if not host or not username:
        return jsonify({"error": "host and username are required"}), 400
    
    # Create SSH client for command execution
    ssh_client = create_ssh_client(host, username, port, password)
    if ssh_client is None:
        return jsonify({"error": f"SSH connection failed for {username}@{host}"}), 500
    
    # Execute commands using the troubleshooting workflow engine
    workflow = TroubleshootWorkflow(ssh_client)
    
    # Choose execution method based on step type
    if step_type == "diagnostic":
        results = workflow.run_diagnostics(commands)
    elif step_type == "fix":
        results = workflow.run_fixes(commands)
    elif step_type == "verification":
        results = workflow.run_verification(commands)
    else:
        # Generic command execution
        results = workflow.execute_commands(commands, step_type)
    
    # Clean up SSH connection
    ssh_client.close()
    
    return jsonify(results)

# ===========================
# System Awareness API
# ===========================

@app.route("/profile", methods=["POST"])
def profile_server():
    """
    Profile a server to understand its capabilities and configuration.
    
    This endpoint analyzes the target server to detect:
    - Operating system and version
    - Available package managers (apt, yum, dnf, apk, etc.)
    - Service manager (systemd, sysvinit, openrc)
    - Installed software and tools
    - Security context (sudo availability, firewall)
    
    Request body:
    {
        "host": "server hostname/IP",
        "username": "SSH username",
        "password": "SSH password (optional)",
        "port": 22,
        "force_refresh": false
    }
    
    Returns:
    {
        "success": true,
        "profile": {
            "os_info": {"distribution": "ubuntu", "version": "20.04"},
            "package_managers": ["apt"],
            "service_manager": "systemd",
            "installed_software": {...},
            "capabilities": [...],
            "confidence_score": 0.85
        },
        "summary": "OS: Ubuntu 20.04 | Package Manager: apt | Service Manager: systemd"
    }
    """
    data = request.get_json()
    host = data.get("host")
    username = data.get("username")
    password = data.get("password")
    port = int(data.get("port", 22))
    force_refresh = data.get("force_refresh", False)
    
    # Validate required parameters
    if not host or not username:
        return jsonify({"error": "host and username are required"}), 400
    
    # Create SSH client for server profiling
    ssh_client = create_ssh_client(host, username, port, password)
    if ssh_client is None:
        return jsonify({"error": f"SSH connection failed for {username}@{host}"}), 500
    
    try:
        # Initialize system context with this connection
        profile = system_context.initialize_context(ssh_client, host, force_refresh)
        
        return jsonify({
            "success": True,
            "profile": profile,
            "summary": system_context.get_system_summary()
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Server profiling failed: {str(e)}"
        }), 500
    finally:
        ssh_client.close()

@app.route("/profile/summary", methods=["GET"])
def get_profile_summary():
    """
    Get a summary of the currently active server profile.
    
    Returns:
    {
        "summary": "OS: Ubuntu 20.04 | Package Manager: apt | Service Manager: systemd",
        "has_profile": true,
        "confidence": 0.85
    }
    """
    summary = system_context.get_system_summary()
    profile = system_context.get_current_profile()
    
    return jsonify({
        "summary": summary,
        "has_profile": profile is not None,
        "confidence": profile.get("confidence_score", 0) if profile else 0
    })

@app.route("/profile/suggestions/<category>", methods=["GET"])
def get_command_suggestions(category):
    """
    Get server-specific command suggestions for a category.
    
    Categories: 'package', 'service', 'network', 'monitoring'
    
    Returns:
    {
        "category": "package",
        "suggestions": [
            "sudo apt update && sudo apt upgrade",
            "apt search <package>",
            "sudo apt install <package>"
        ],
        "server_aware": true
    }
    """
    suggestions = system_context.get_command_suggestions(category)
    
    return jsonify({
        "category": category,
        "suggestions": suggestions,
        "server_aware": system_context.get_current_profile() is not None
    })

# ===========================
# WebSocket Terminal Support
# ===========================

# Initialize SocketIO for real-time terminal communication
socketio = SocketIO(app, cors_allowed_origins="*")

# Dictionary to store active SSH sessions by session ID
ssh_sessions = {}

@app.route("/terminal")
def terminal():
    """
    Serve terminal interface (legacy route with hardcoded values).
    Note: This route contains hardcoded connection details and should be updated
    to use dynamic parameters or removed if not needed.
    """
    # TODO: Remove hardcoded values or make this route dynamic
    ip = "10.4.5.70" 
    user = "root"
    password = ""
    return render_template("terminal.html", ip=ip, user=user, password=password)

def _reader_thread(sid: str):
    """
    Background thread to read SSH output and send to WebSocket client.
    
    Args:
        sid (str): Socket.IO session ID
    """
    session = ssh_sessions.get(sid)
    
    if not session:
        return
    
    chan = session["chan"]
    
    try:
        while True:
            # Check if channel is closed or session was removed
            if chan.closed or sid not in ssh_sessions:
                break
            
            # Read stdout data if available
            if chan.recv_ready():
                data = chan.recv(4096).decode(errors="ignore")
                socketio.emit("terminal_output", {"output": data}, room=sid)
            
            # Read stderr data if available
            if chan.recv_stderr_ready():
                data = chan.recv_stderr(4096).decode(errors="ignore")
                socketio.emit("terminal_output", {"output": data}, room=sid)
            
            # Small delay to prevent CPU spinning
            eventlet.sleep(0.01)
            
    except Exception as e:
        # Send error message to client
        socketio.emit("terminal_output", {"output": f"\r\n[reader error] {e}\r\n"}, room=sid)
    finally:
        # Clean up session on thread exit
        session = ssh_sessions.pop(sid, None)
        if session:
            try: 
                session["chan"].close()
            except Exception: 
                pass
            try: 
                session["client"].close()
            except Exception: 
                pass

@socketio.on("start_ssh")
def start_ssh(data):
    """
    Initialize SSH connection for WebSocket terminal.
    
    Expected data:
    {
        "ip": "server IP/hostname",
        "user": "SSH username", 
        "password": "SSH password (optional)"
    }
    """
    sid = request.sid
    ip = (data or {}).get("ip")
    user = (data or {}).get("user")
    password = (data or {}).get("password", "")
    
    # Validate required parameters
    if not ip or not user:
        emit("terminal_output", {"output": "\r\nMissing IP or Username.\r\n"})
        return
    
    # Close existing session if any
    old = ssh_sessions.pop(sid, None)
    if old:
        try: 
            old["chan"].close()
        except Exception: 
            pass
        try: 
            old["client"].close()
        except Exception: 
            pass
    
    try:
        # Create new SSH client
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Connect with appropriate authentication method
        client.connect(
            hostname=str(ip),
            username=str(user),
            password=password if password else None,
            look_for_keys=not password,  # Only use keys if password not provided
            allow_agent=not password,    # Allow agent if no password
            timeout=10
        )
        
        # Create interactive shell channel
        chan = client.invoke_shell(term="xterm")
        chan.settimeout(0.0)
        
        # Store session and start reader thread
        ssh_sessions[sid] = {"client": client, "chan": chan}
        threading.Thread(target=_reader_thread, args=(sid,), daemon=True).start()
        
        emit("terminal_output", {"output": f"Connected to {ip} as {user}\r\n"})
        
    except Exception as e:
        emit("terminal_output", {"output": f"\r\nSSH Connection Failed: {e}\r\n"})

@socketio.on("terminal_input")
def handle_terminal_input(data):
    """
    Handle keyboard input from WebSocket terminal client.
    
    Expected data:
    {
        "input": "text to send to terminal"
    }
    """
    sid = request.sid
    session = ssh_sessions.get(sid)
    
    if not session:
        emit("terminal_output", {"output": "\r\n[Error] No SSH session. Refresh and try again.\r\n"})
        return
    
    try:
        text = (data or {}).get("input", "")
        if text:
            session["chan"].send(text)
    except Exception as e:
        emit("terminal_output", {"output": f"\r\n[send error] {e}\r\n"})

@socketio.on("resize")
def handle_resize(data):
    """
    Handle terminal resize events from client.
    
    Expected data:
    {
        "cols": terminal_columns,
        "rows": terminal_rows
    }
    """
    sid = request.sid
    session = ssh_sessions.get(sid)
    
    if not session:
        return
    
    try:
        cols = int((data or {}).get("cols", 80))
        rows = int((data or {}).get("rows", 24))
        session["chan"].resize_pty(width=cols, height=rows)
    except Exception:
        pass

@socketio.on("disconnect")
def on_disconnect():
    """
    Clean up SSH session when WebSocket client disconnects.
    """
    sid = request.sid
    session = ssh_sessions.pop(sid, None)
    
    if session:
        try: 
            session["chan"].close()
        except Exception: 
            pass
        try: 
            session["client"].close()
        except Exception: 
            pass

# ===========================
# Application Entry Point
# ===========================

if __name__ == "__main__":
    # Get port from environment variable or default to 8080
    port = int(os.environ.get("PORT", 8080))
    
    # Run the Flask application with SocketIO support
    # Set debug=False for production use
    socketio.run(app, host="0.0.0.0", port=port, debug=False)