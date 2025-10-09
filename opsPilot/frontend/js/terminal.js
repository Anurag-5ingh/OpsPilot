/**
 * Terminal Module
 * Handles SSH terminal connection and interaction
 */

/**
 * Initialize Socket.IO and xterm.js terminal
 */
function initializeTerminal() {
  // Initialize Socket.IO connection
  state.socket = io();
  
  // Initialize xterm.js terminal
  state.terminal = new Terminal({
    cursorBlink: true,
    fontSize: 14,
    theme: { 
      background: "#000000",
      foreground: "#ffffff"
    }
  });
  
  state.terminal.open(document.getElementById('terminal-container'));
  
  // Connect terminal to socket
  state.socket.on("connect", () => {
    state.socket.emit("start_ssh", {
      ip: state.currentHost,
      user: state.currentUser,
      password: ""
    });
  });

  state.terminal.onData(data => {
    state.socket.emit("terminal_input", { input: data });
  });

  state.socket.on("terminal_output", data => {
    state.terminal.write(data.output);
    if (data.output.includes("Connected to")) {
      state.terminalConnected = true;
    }
  });

  // Handle terminal resize
  function sendResize() {
    const cols = state.terminal.cols;
    const rows = state.terminal.rows;
    state.socket.emit("resize", { cols, rows });
  }
  
  state.terminal.onResize(sendResize);
  setTimeout(sendResize, 200);
  window.addEventListener('resize', () => setTimeout(sendResize, 200));
}

/**
 * Clear terminal screen
 */
function clearTerminal() {
  if (state.terminal) {
    state.terminal.clear();
  }
}

/**
 * Reconnect to SSH terminal
 */
function reconnectTerminal() {
  if (state.socket) {
    state.socket.emit("start_ssh", {
      ip: state.currentHost,
      user: state.currentUser,
      password: ""
    });
    appendMessage("Reconnecting to terminal...", "system");
  }
}

/**
 * Connect to SSH server
 */
function connectSSH() {
  const host = document.getElementById("host").value.trim();
  const user = document.getElementById("user").value.trim();
  const password = document.getElementById("password").value.trim();
  const errorMsg = document.getElementById("login-error");
  const connectBtn = document.getElementById("connect-button");

  if (!host || !user) {
    errorMsg.textContent = "Host and username are required.";
    return;
  }

  // Save credentials for later use
  state.currentHost = host;
  state.currentUser = user;
  state.currentPassword = password;

  errorMsg.textContent = "";
  setButtonLoading(connectBtn, true);

  // Test connection first
  fetch("/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      host: state.currentHost,
      username: state.currentUser,
      password: state.currentPassword,
      command: "echo connected"
    }),
  })
    .then(res => res.json())
    .then(data => {
      setButtonLoading(connectBtn, false);
      if ("output" in data) {
        // Switch to main screen
        document.getElementById("login-screen").classList.add("hidden");
        document.getElementById("main-screen").classList.remove("hidden");
        
        // Initialize terminal
        initializeTerminal();
        
        // Profile the server for system awareness
        profileServer(state.currentHost, state.currentUser)
          .then(profile => {
            if (profile) {
              updateSystemAwarenessUI();
              appendMessage("✅ Server profiled successfully! AI is now system-aware.", "system");
            } else {
              appendMessage("⚠️ Server profiling failed. Using generic mode.", "system");
              updateSystemAwarenessUI();
            }
          });
        
        // Focus on chat input
        document.getElementById("user-input").focus();
      } else {
        errorMsg.textContent = data.error || "Connection failed.";
      }
    })
    .catch(() => {
      setButtonLoading(connectBtn, false);
      errorMsg.textContent = "Connection failed due to server error.";
    });
}
