import eventlet
eventlet.monkey_patch()

import os
import time
from flask import Flask, request, jsonify, send_from_directory
# Import from modular structure inside ai_shell_agent
from ai_shell_agent.modules.command_generation import ask_ai_for_command
from ai_shell_agent.modules.troubleshooting import ask_ai_for_troubleshoot, TroubleshootWorkflow
from ai_shell_agent.modules.ssh import create_ssh_client, run_shell, ssh_bp
from ai_shell_agent.modules.shared import ConversationMemory
from ai_shell_agent.modules.system_awareness import SystemContextManager
from ai_shell_agent.modules.pipeline_healing import PipelineMonitor, AutonomousHealer

from flask import render_template, redirect, url_for
from flask_socketio import SocketIO, emit
import paramiko
import threading
# -------------------------
# App setup
# -------------------------
app = Flask(__name__)

# Keep your existing memory logic
memory = ConversationMemory(max_entries=20)

# Initialize system context manager
system_context = SystemContextManager()

# Initialize pipeline healing system
pipeline_healer = AutonomousHealer(system_context)
pipeline_monitor = PipelineMonitor(healer=pipeline_healer)

# Secret key config
app.config['SECRET_KEY'] = os.environ.get("APP_SECRET", "dev_secret_change_me")

# -------------------------
# Register blueprints
# -------------------------
app.register_blueprint(ssh_bp)

@app.route("/")
def index():
    """Main route - redirect to opspilot interface"""
    return redirect(url_for("serve_index"))

# -------------------------
# Existing routes (unchanged)
# -------------------------
@app.route("/opspilot")
def serve_index():
    return send_from_directory("frontend", "index.html")

@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory("frontend", path)

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    user_input = data.get("prompt")

    if not user_input:
        return jsonify({"error": "No prompt provided"}), 400

    result = ask_ai_for_command(user_input, memory=memory.get(), system_context=system_context)
    if not result:
        return jsonify({"error": "AI failed to respond"}), 500

    ai_response = result.get("ai_response", {})
    command = ai_response.get("final_command")

    if not command:
        return jsonify({"error": "No command generated"}), 400

    memory.add(user_input, command)

    return jsonify({
        "ai_command": command,
        "original_prompt": user_input
    })

@app.route("/run", methods=["POST"])
def run_command():
    """
    Execute a shell command on the remote server.
    Accepts `host`, `username`, `port` (optional, default 22), and `command`.
    """
    data = request.get_json()
    host = data.get("host")
    username = data.get("username")
    password = data.get("password")
    command = data.get("command")
    port = data.get("port", 22)

    if not host or not username or not command:
        return jsonify({"error": "host, username, and command are required"}), 400

    # Create SSH client and execute command
    ssh_client = create_ssh_client(host, username, port, password)
    if ssh_client is None:
        return jsonify({"error": f"SSH connection failed for {username}@{host}"}), 500

    output, error = run_shell(command, ssh_client=ssh_client)
    return jsonify({"output": output, "error": error})

# -------------------------
# NEW: Troubleshooting Feature (Separate from /ask)
# -------------------------
@app.route("/troubleshoot", methods=["POST"])
def troubleshoot():
    """
    Analyze an error and provide troubleshooting steps.
    This is a separate feature from single-command generation.
    
    Request body:
    {
        "error_text": "error message or description",
        "host": "remote host",
        "username": "ssh user",
        "port": 22,
        "context": {
            "last_command": "optional",
            "last_output": "optional",
            "last_error": "optional"
        }
    }
    """
    data = request.get_json()
    error_text = data.get("error_text")
    host = data.get("host")
    username = data.get("username")
    port = int(data.get("port", 22))
    context = data.get("context", {})
    
    if not error_text:
        return jsonify({"error": "error_text is required"}), 400
    
    if not host or not username:
        return jsonify({"error": "host and username are required"}), 400
    
    # Get troubleshooting plan from AI
    result = ask_ai_for_troubleshoot(error_text, context=context, system_context=system_context)
    
    if not result or not result.get("success"):
        return jsonify({
            "error": "Failed to generate troubleshooting plan",
            "details": result.get("error", "Unknown error")
        }), 500
    
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
    
    Request body:
    {
        "commands": ["cmd1", "cmd2"],
        "step_type": "diagnostic|fix|verification",
        "host": "remote host",
        "username": "ssh user",
        "port": 22
    }
    """
    data = request.get_json()
    commands = data.get("commands", [])
    step_type = data.get("step_type", "unknown")
    host = data.get("host")
    username = data.get("username")
    password = data.get("password")
    port = int(data.get("port", 22))
    
    if not commands:
        return jsonify({"error": "No commands provided"}), 400
    
    if not host or not username:
        return jsonify({"error": "host and username are required"}), 400
    
    # Create SSH client
    ssh_client = create_ssh_client(host, username, port, password)
    if ssh_client is None:
        return jsonify({"error": f"SSH connection failed for {username}@{host}"}), 500
    
    # Execute commands using workflow engine
    workflow = TroubleshootWorkflow(ssh_client)
    
    if step_type == "diagnostic":
        results = workflow.run_diagnostics(commands)
    elif step_type == "fix":
        results = workflow.run_fixes(commands)
    elif step_type == "verification":
        results = workflow.run_verification(commands)
    else:
        results = workflow.execute_commands(commands, step_type)
    
    ssh_client.close()
    
    return jsonify(results)

# -------------------------
# NEW: System Awareness Endpoints
# -------------------------
@app.route("/profile", methods=["POST"])
def profile_server():
    """
    Profile the server to understand its capabilities and configuration.
    
    Request body:
    {
        "host": "remote host",
        "username": "ssh user", 
        "port": 22,
        "force_refresh": false
    }
    """
    data = request.get_json()
    host = data.get("host")
    username = data.get("username")
    password = data.get("password")
    port = int(data.get("port", 22))
    force_refresh = data.get("force_refresh", False)
    
    if not host or not username:
        return jsonify({"error": "host and username are required"}), 400
    
    # Create SSH client
    ssh_client = create_ssh_client(host, username, port, password)
    if ssh_client is None:
        return jsonify({"error": f"SSH connection failed for {username}@{host}"}), 500
    
    try:
        # Initialize system context with this connection
        profile = system_context.initialize_context(ssh_client, force_refresh=force_refresh)
        
        return jsonify({
            "success": True,
            "profile": profile,
            "summary": system_context.get_system_summary()
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
    finally:
        ssh_client.close()

@app.route("/profile/summary", methods=["GET"])
def get_profile_summary():
    """Get a summary of the current server profile"""
    summary = system_context.get_system_summary()
    profile = system_context.get_current_profile()
    
    return jsonify({
        "summary": summary,
        "has_profile": profile is not None,
        "confidence": profile.get("confidence_score", 0) if profile else 0
    })

@app.route("/profile/suggestions/<category>", methods=["GET"])
def get_command_suggestions(category):
    """Get server-specific command suggestions for a category"""
    suggestions = system_context.get_command_suggestions(category)
    
    return jsonify({
        "category": category,
        "suggestions": suggestions,
        "server_aware": system_context.get_current_profile() is not None
    })

# -------------------------
# NEW: Pipeline Healing Endpoints
# -------------------------
@app.route("/pipeline/webhook", methods=["POST"])
def pipeline_webhook():
    """
    Receive pipeline failure webhooks and trigger healing
    
    Request body:
    {
        "source": "jenkins/ansible/gitlab",
        "job_name": "web-app-deployment",
        "build_number": 123,
        "stage": "Deploy",
        "error_message": "Package installation failed",
        "console_output": "...",
        "target_hosts": ["web-server-01"]
    }
    """
    try:
        webhook_data = request.get_json()
        
        if not webhook_data:
            return jsonify({"error": "No webhook data provided"}), 400
        
        # Handle the webhook through pipeline monitor
        result = pipeline_monitor.handle_webhook_failure(webhook_data)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": time.time()
        }), 500

@app.route("/pipeline/status", methods=["GET"])
def pipeline_status():
    """Get pipeline healing system status"""
    stats = pipeline_monitor.get_monitoring_stats()
    
    return jsonify({
        "pipeline_healing": stats,
        "system_context": {
            "has_profile": system_context.get_current_profile() is not None,
            "summary": system_context.get_system_summary() if system_context.get_current_profile() else "No profile"
        }
    })

@app.route("/pipeline/healing/history", methods=["GET"])
def healing_history():
    """Get healing history"""
    limit = request.args.get("limit", 20, type=int)
    history = pipeline_healer.get_healing_history(limit)
    
    return jsonify({
        "healing_history": history,
        "success_rate": pipeline_healer.get_success_rate(),
        "total_sessions": len(history)
    })

@app.route("/pipeline/test/trigger", methods=["POST"])
def test_trigger_healing():
    """
    Test endpoint to trigger healing manually
    
    Request body:
    {
        "error_type": "package_failure",
        "host": "test-server",
        "error_message": "Package not found"
    }
    """
    try:
        test_data = request.get_json()
        
        # Create test error info
        error_info = {
            "timestamp": time.time(),
            "source": "test",
            "task_name": "Test Healing",
            "host": test_data.get("host", "test-server"),
            "module": "test",
            "raw_error": test_data.get("error_message", "Test error"),
            "error_category": test_data.get("error_type", "unknown"),
            "severity": "medium"
        }
        
        # Trigger healing
        healing_result = pipeline_healer.heal_error(
            error_info=error_info,
            target_hosts=[error_info["host"]]
        )
        
        return jsonify({
            "test_triggered": True,
            "error_info": error_info,
            "healing_result": healing_result
        })
        
    except Exception as e:
        return jsonify({
            "test_triggered": False,
            "error": str(e)
        }), 500

# -------------------------
# Simple dashboard
# -------------------------
@app.route("/dashboard")
def dashboard():
    return (
        "<h2>Welcome to OpsPilot Dashboard</h2>"
        "<p>This is your dashboard. Your app's original endpoints are unchanged.</p>"
        "<p><a href='/'>Back to app</a></p>"
    )

socketio = SocketIO(app, cors_allowed_origins="*")
ssh_sessions = {}
@app.route("/terminal")

def terminal():

    ip = "10.4.5.70" 
    # request.args.get("ip")

    user = "root"
    # request.args.get("user")

    password = ""
    # request.args.get("password", "")

    return render_template("terminal.html", ip=ip, user=user, password=password)



def _reader_thread(sid: str):

    session = ssh_sessions.get(sid)

    if not session:

        return

    chan = session["chan"]



    try:

        while True:

            if chan.closed or sid not in ssh_sessions:

                break



            if chan.recv_ready():

                data = chan.recv(4096).decode(errors="ignore")

                socketio.emit("terminal_output", {"output": data}, room=sid)



            if chan.recv_stderr_ready():

                data = chan.recv_stderr(4096).decode(errors="ignore")

                socketio.emit("terminal_output", {"output": data}, room=sid)



            eventlet.sleep(0.01)

    except Exception as e:

        socketio.emit("terminal_output", {"output": f"\r\n[reader error] {e}\r\n"}, room=sid)

    finally:

        session = ssh_sessions.pop(sid, None)

        if session:

            try: session["chan"].close()

            except Exception: pass

            try: session["client"].close()

            except Exception: pass



@socketio.on("start_ssh")

def start_ssh(data):

    sid = request.sid

    ip = (data or {}).get("ip")

    user = (data or {}).get("user")

    password = (data or {}).get("password", "")



    if not ip or not user:

        emit("terminal_output", {"output": "\r\nMissing IP or Username.\r\n"})

        return



    # Close old session if exists

    old = ssh_sessions.pop(sid, None)

    if old:

        try: old["chan"].close()

        except Exception: pass

        try: old["client"].close()

        except Exception: pass



    try:

        client = paramiko.SSHClient()

        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())



        # Key part: no local ssh_config aliasing

        client.connect(

            hostname=str(ip),

            username=str(user),

            password=password if password else None,

            look_for_keys=not password,  # only use keys if password not provided

            allow_agent=not password,    # allow agent if no password

            timeout=10

        )



        chan = client.invoke_shell(term="xterm")

        chan.settimeout(0.0)



        ssh_sessions[sid] = {"client": client, "chan": chan}

        threading.Thread(target=_reader_thread, args=(sid,), daemon=True).start()



        emit("terminal_output", {"output": f"Connected to {ip} as {user}\r\n"})



    except Exception as e:

        emit("terminal_output", {"output": f"\r\nSSH Connection Failed: {e}\r\n"})



@socketio.on("terminal_input")

def handle_terminal_input(data):

    sid = request.sid
    print(data)
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

    sid = request.sid

    session = ssh_sessions.pop(sid, None)

    if session:

        try: session["chan"].close()

        except Exception: pass

        try: session["client"].close()

        except Exception: pass

# -------------------------
# App runner
# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
