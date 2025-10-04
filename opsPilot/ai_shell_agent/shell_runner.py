import os
import paramiko
from dotenv import load_dotenv

load_dotenv()

# Try to import Flask-related helpers; if not available (or no app context),
# we will gracefully skip DB-based connection lookup.
try:
    from flask_login import current_user
    from ai_shell_agent.models import SSHConnection
    HAS_FLASK_LOGIN = True
except Exception:
    HAS_FLASK_LOGIN = False


def create_ssh_client(host: str, user: str, port: int = 22):
    """
    Create and return a connected paramiko.SSHClient or None on failure.
    """
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(host, username=user, port=port)
        print(f"SSH connection established to {user}@{host}:{port}")
        return ssh
    except Exception as e:
        print(f"SSH connection failed: {str(e)}")
        return None


def run_shell(command: str, ssh_client=None) -> tuple:
    """
    Execute a command over SSH.

    - If `ssh_client` (paramiko.SSHClient) is provided, use it directly.
    - Otherwise, try to use current_user's SSHConnection (if available and logged in).
    - Fallback: use REMOTE_HOST / REMOTE_USER from .env.

    Returns:
        (stdout_str, stderr_str)
    """
    created_ssh = False

    if ssh_client is None:
        remote_host = None
        remote_user = None
        remote_port = 22

        # Try to fetch from logged-in user's DB record
        if HAS_FLASK_LOGIN:
            try:
                if current_user.is_authenticated:
                    conn = SSHConnection.query.filter_by(user_id=current_user.id).first()
                    if conn:
                        remote_host = conn.host
                        remote_user = conn.username
                        remote_port = int(conn.port or 22)
            except Exception:
                pass

        # Fallback to environment variables
        if not remote_host or not remote_user:
            remote_host = os.getenv("REMOTE_HOST")
            remote_user = os.getenv("REMOTE_USER")
            try:
                remote_port = int(os.getenv("REMOTE_PORT", 22))
            except Exception:
                remote_port = 22

        if not remote_host or not remote_user:
            return "", "SSH connection failed: no host/user available"

        ssh_client = create_ssh_client(remote_host, remote_user, port=remote_port)
        if ssh_client is None:
            return "", "SSH connection failed: could not establish connection"
        created_ssh = True

    # Execute command
    try:
        stdin, stdout, stderr = ssh_client.exec_command(command)
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
    except Exception as e:
        output, error = "", f"Command execution failed: {str(e)}"

    if created_ssh:
        try:
            ssh_client.close()
        except Exception:
            pass

    return output, error
