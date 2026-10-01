"""
Local (guest mode) terminal.

Spawns the user's shell on a pseudo-terminal and exposes it through the same
small interface the WebSocket handlers use for paramiko channels (send,
recv, recv_ready, resize_pty, close, closed), so SSH and local sessions share
one code path.

POSIX only (macOS / Linux). The shell runs as the user who started the server.
"""
import os
import select
import signal
import subprocess
import sys

IS_SUPPORTED = sys.platform != "win32"

if IS_SUPPORTED:
    import fcntl
    import pty
    import struct
    import termios

LOOPBACK_ADDRS = {"127.0.0.1", "::1", "::ffff:127.0.0.1"}


def availability(remote_addr, forwarded_for=None):
    """Return (allowed, reason). The local shell is only offered to the machine it runs on."""
    if not IS_SUPPORTED:
        return False, "Local terminal is not supported on Windows."
    if os.getenv("OPSPILOT_LOCAL_TERMINAL", "true").lower() == "false":
        return False, "Local terminal is disabled (OPSPILOT_LOCAL_TERMINAL=false)."
    if forwarded_for or remote_addr not in LOOPBACK_ADDRS:
        return False, "Local terminal is only available from the machine running OpsPilot."
    return True, ""


class LocalPty:
    """A shell process attached to a pty, shaped like a paramiko Channel."""

    def __init__(self):
        shell = os.environ.get("SHELL") or "/bin/bash"
        master_fd, slave_fd = pty.openpty()

        def _make_controlling_tty():
            os.setsid()
            fcntl.ioctl(0, termios.TIOCSCTTY, 1)

        env = dict(os.environ, TERM="xterm-256color")
        try:
            self.proc = subprocess.Popen(
                [shell, "-l"],
                stdin=slave_fd, stdout=slave_fd, stderr=slave_fd,
                cwd=os.path.expanduser("~"), env=env,
                preexec_fn=_make_controlling_tty, close_fds=True,
            )
        except Exception:
            os.close(master_fd)
            raise
        finally:
            os.close(slave_fd)
        self._fd = master_fd
        self._closed = False

    @property
    def closed(self):
        return self._closed or self.proc.poll() is not None

    def recv_ready(self):
        if self._closed:
            return False
        try:
            return bool(select.select([self._fd], [], [], 0)[0])
        except (OSError, ValueError):
            return False

    def recv(self, nbytes):
        try:
            return os.read(self._fd, nbytes)
        except OSError:  # EIO once the shell exits
            self._closed = True
            return b""

    def recv_stderr_ready(self):
        return False  # a pty merges stderr into the same stream

    def send(self, text):
        if not self._closed:
            os.write(self._fd, text.encode() if isinstance(text, str) else text)

    def resize_pty(self, width=80, height=24):
        if not self._closed:
            fcntl.ioctl(self._fd, termios.TIOCSWINSZ, struct.pack("HHHH", height, width, 0, 0))

    def close(self):
        if self._closed:
            return
        self._closed = True
        try:
            os.close(self._fd)
        except OSError:
            pass
        if self.proc.poll() is None:
            try:
                os.killpg(self.proc.pid, signal.SIGHUP)
            except (ProcessLookupError, PermissionError):
                pass
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()


class LocalClient:
    """Stands in for the paramiko client in the session registry."""

    def __init__(self, chan):
        self._chan = chan

    def close(self):
        self._chan.close()


def open_local_session():
    """Start a local shell and return (client, chan) like the SSH path does."""
    chan = LocalPty()
    return LocalClient(chan), chan
