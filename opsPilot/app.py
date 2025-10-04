import eventlet
eventlet.monkey_patch()

import os
from flask import Flask, request, jsonify, send_from_directory
from ai_shell_agent.ai_command import ask_ai_for_command
from ai_shell_agent.shell_runner import run_shell, create_ssh_client
from ai_shell_agent.conversation_memory import ConversationMemory
from ai_shell_agent.ssh import ssh_bp  # Import SSH blueprint

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

    result = ask_ai_for_command(user_input, memory=memory.get())
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
def run():
    """
    Execute a shell command on the remote server.
    Accepts `host`, `username`, `port` (optional, default 22), and `command`.
    """
    data = request.get_json()
    command = data.get("command")
    host = data.get("host")
    username = data.get("username")
    port = int(data.get("port", 22))

    if not command or not host or not username:
        return jsonify({"error": "host, username, and command are required"}), 400

    # Create SSH client and execute command
    ssh_client = create_ssh_client(host, username, port)
    if ssh_client is None:
        return jsonify({"error": f"SSH connection failed for {username}@{host}"}), 500

    output, error = run_shell(command, ssh_client=ssh_client)
    return jsonify({"output": output, "error": error})

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
    app.run(host="0.0.0.0", port=8080, debug=True)
