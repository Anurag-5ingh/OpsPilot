/**
 * Terminal Module
 * Handles SSH terminal connection and interaction
 */

/**
 * Initialize Socket.IO and xterm.js terminal
 */
function initializeTerminal() {
  // Show loading indicator
  const terminalContainer = document.getElementById('terminal-container');
  terminalContainer.innerHTML = '<div style="color: white; text-align: center; padding: 20px;">🔄 Initializing terminal...</div>';
  
  // Initialize Socket.IO connection with robust reconnection
  state.socket = io({
    timeout: 10000,
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionAttempts: Infinity,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 5000,
  });
  
  // Initialize xterm.js terminal with optimized settings
  state.terminal = new Terminal({
    cursorBlink: true,
    fontSize: 14,
    theme: { 
      background: "#000000",
      foreground: "#ffffff"
    },
    // Optimize for performance
    scrollback: 1000, // Reduce scrollback buffer
    fastScrollModifier: 'alt',
    macOptionIsMeta: true
  });
  
  // Clear loading indicator and open terminal
  terminalContainer.innerHTML = '';
  state.terminal.open(terminalContainer);
  
  // Set up connection timeout
  let connectionTimeout;
  
  // Connect terminal to socket
  state.socket.on("connect", () => {
    clearTimeout(connectionTimeout);
    appendMessage("🔄 Connecting to SSH server...", "system");
    
    state.socket.emit("start_ssh", {
      ip: state.currentHost,
      user: state.currentUser,
      password: state.currentPassword || ""
    });
    
    // Set connection timeout
    connectionTimeout = setTimeout(() => {
      if (!state.terminalConnected) {
        appendMessage("❌ Connection timeout. Please check your credentials and try again.", "system");
      }
    }, 10000);
  });

  state.socket.on("connect_error", (error) => {
    clearTimeout(connectionTimeout);
    appendMessage(`❌ Connection failed: ${error.message}`, "system");
  });

  // Auto re-authenticate on reconnects
  state.socket.on('reconnect', () => {
    appendMessage("♻️ Reconnected to server. Restoring SSH session...", 'system');
    if (state.currentHost && state.currentUser) {
      state.socket.emit('start_ssh', {
        ip: state.currentHost,
        user: state.currentUser,
        password: state.currentPassword || ""
      });
    }
  });

  // Handle disconnects and keep trying
  state.socket.on('disconnect', (reason) => {
    state.terminalConnected = false;
    appendMessage(`⚠️ Terminal disconnected (${reason}). Will keep trying to reconnect...`, 'system');
    // If server forced disconnect, we must manually connect
    if (reason === 'io server disconnect' && state.socket && typeof state.socket.connect === 'function') {
      try { state.socket.connect(); } catch (_) {}
    }
  });

  state.terminal.onData(data => {
    if (state.socket && state.socket.connected) {
      state.socket.emit("terminal_input", { input: data });
    }
  });

  state.socket.on("terminal_output", data => {
    if (state.terminal) {
      state.terminal.write(data.output);
      if (data.output.includes("Connected to")) {
        state.terminalConnected = true;
        clearTimeout(connectionTimeout);
        appendMessage("✅ Terminal connected successfully!", "system");
      }
    }
  });

  // Handle terminal resize with debouncing
  let resizeTimeout;
  function sendResize() {
    if (resizeTimeout) clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
      if (state.terminal && state.socket && state.socket.connected) {
        const cols = state.terminal.cols;
        const rows = state.terminal.rows;
        state.socket.emit("resize", { cols, rows });
      }
    }, 100);
  }
  
  state.terminal.onResize(sendResize);
  setTimeout(sendResize, 200);
  window.addEventListener('resize', sendResize);
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
      password: state.currentPassword || ""
    });
    appendMessage("Reconnecting to terminal...", "system");
  }
}

// Namespacing shim for modularity (non-breaking)
(function(){
  try {
    window.Modules = window.Modules || {};
    window.Modules.Terminal = {
      initializeTerminal,
      clearTerminal,
      reconnectTerminal,
      connectSSH
    };
  } catch (_) { /* ignore if window not available */ }
})();

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
