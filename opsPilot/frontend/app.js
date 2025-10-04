let currentCommand = "";
let currentHost = "";
let currentUser = "";
let socket = null;
let terminal = null;
let terminalConnected = false;

function setButtonLoading(button, loading) {
  const textEl = button.querySelector(".btn-text");
  const spinnerEl = button.querySelector(".spinner");

  if (loading) {
    textEl.classList.add("hidden");
    spinnerEl.classList.remove("hidden");
    button.disabled = true;
  } else {
    textEl.classList.remove("hidden");
    spinnerEl.classList.add("hidden");
    button.disabled = false;
  }
}

function connectSSH() {
  const host = document.getElementById("host").value.trim();
  const user = document.getElementById("user").value.trim();
  const errorMsg = document.getElementById("login-error");
  const connectBtn = document.getElementById("connect-button");

  if (!host || !user) {
    errorMsg.textContent = "Both fields are required.";
    return;
  }

  // Save credentials for later use
  currentHost = host;
  currentUser = user;

  errorMsg.textContent = "";
  setButtonLoading(connectBtn, true);

  // Test connection first
  fetch("/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      host: currentHost,
      username: currentUser,
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

function initializeTerminal() {
  // Initialize Socket.IO connection
  socket = io();
  
  // Initialize xterm.js terminal
  terminal = new Terminal({
    cursorBlink: true,
    fontSize: 14,
    theme: { 
      background: "#000000",
      foreground: "#ffffff"
    }
  });
  
  terminal.open(document.getElementById('terminal-container'));
  
  // Connect terminal to socket
  socket.on("connect", () => {
    socket.emit("start_ssh", {
      ip: currentHost,
      user: currentUser,
      password: ""
    });
  });

  terminal.onData(data => {
    socket.emit("terminal_input", { input: data });
  });

  socket.on("terminal_output", data => {
    terminal.write(data.output);
    if (data.output.includes("Connected to")) {
      terminalConnected = true;
    }
  });

  // Handle terminal resize
  function sendResize() {
    const cols = terminal.cols;
    const rows = terminal.rows;
    socket.emit("resize", { cols, rows });
  }
  
  terminal.onResize(sendResize);
  setTimeout(sendResize, 200);
  window.addEventListener('resize', () => setTimeout(sendResize, 200));
}

function appendMessage(text, role) {
  const container = document.getElementById("chat-container");
  const msg = document.createElement("div");
  msg.className = `message ${role}`;
  msg.textContent = text;
  container.appendChild(msg);
  container.scrollTop = container.scrollHeight;
}

function showConfirmButtons() {
  const container = document.getElementById("chat-container");
  const btnGroup = document.createElement("div");
  btnGroup.className = "confirm-buttons";

  const yesBtn = document.createElement("button");
  yesBtn.textContent = "Yes";
  yesBtn.onclick = () => confirmCommand("yes", btnGroup);

  const noBtn = document.createElement("button");
  noBtn.textContent = "No";
  noBtn.onclick = () => confirmCommand("no", btnGroup);

  btnGroup.append(yesBtn, noBtn);
  container.appendChild(btnGroup);
  container.scrollTop = container.scrollHeight;
}

function confirmCommand(choice, container) {
  appendMessage(`You chose: ${choice.toUpperCase()}`, "user");
  container.remove();

  if (choice === "yes") {
    // Paste and run in terminal
    if (terminal && terminalConnected) {
      socket.emit("terminal_input", { input: currentCommand + "\n" });
      appendMessage(`Executed in terminal: ${currentCommand}`, "system");
    } else {
      appendMessage("Terminal not connected. Please check connection.", "system");
    }
  }
}

function submitPrompt() {
  const input = document.getElementById("user-input");
  const askBtn = document.getElementById("ask");

  const prompt = input.value.trim();
  if (!prompt) return;

  appendMessage(prompt, "user");
  input.value = "";
  setButtonLoading(askBtn, true);

  fetch("/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
  })
    .then(res => res.json())
    .then(data => {
      setButtonLoading(askBtn, false);

      if (data.ai_command) {
        currentCommand = data.ai_command;
        appendMessage(`${data.ai_command}`, "ai");
        showConfirmButtons();
      } else {
        appendMessage("Failed to generate command.", "system");
      }
    })
    .catch(() => {
      setButtonLoading(askBtn, false);
      appendMessage("Backend error.", "system");
    });
}

function clearTerminal() {
  if (terminal) {
    terminal.clear();
  }
}

function reconnectTerminal() {
  if (socket) {
    socket.emit("start_ssh", {
      ip: currentHost,
      user: currentUser,
      password: ""
    });
    appendMessage("Reconnecting to terminal...", "system");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  // Login screen event listeners
  const host = document.getElementById("host");
  const user = document.getElementById("user");
  const connectBtn = document.getElementById("connect-button");

  if (host && user && connectBtn) {
    host.addEventListener("keydown", e => {
      if (e.key === "Enter") {
        e.preventDefault();
        user.focus();
      }
    });

    user.addEventListener("keydown", e => {
      if (e.key === "Enter") {
        e.preventDefault();
        connectBtn.click();
      }
    });

    connectBtn.addEventListener("click", connectSSH);
  }

  // Chat input event listener
  const askInput = document.getElementById("user-input");
  if (askInput) {
    askInput.addEventListener("keydown", e => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        submitPrompt();
      }
    });
  }

  // Button event listeners
  const askBtn = document.getElementById("ask");
  if (askBtn) {
    askBtn.addEventListener("click", submitPrompt);
  }

  const clearBtn = document.getElementById("clear-terminal");
  if (clearBtn) {
    clearBtn.addEventListener("click", clearTerminal);
  }

  const reconnectBtn = document.getElementById("reconnect-terminal");
  if (reconnectBtn) {
    reconnectBtn.addEventListener("click", reconnectTerminal);
  }
});