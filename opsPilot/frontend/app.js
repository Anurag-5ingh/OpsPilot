let currentCommand = "";
let currentHost = "";
let currentUser = "";
let socket = null;
let terminal = null;
let terminalConnected = false;
let currentMode = "command"; // "command" or "troubleshoot"
let troubleshootPlan = null; // Store current troubleshooting plan

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

// ==========================================
// TROUBLESHOOTING FEATURE (NEW)
// ==========================================

function toggleMode(mode) {
  currentMode = mode;
  
  const commandBtn = document.getElementById("mode-command");
  const troubleshootBtn = document.getElementById("mode-troubleshoot");
  const commandContainer = document.getElementById("command-input-container");
  const troubleshootContainer = document.getElementById("troubleshoot-input-container");
  
  if (mode === "command") {
    commandBtn.classList.add("active");
    troubleshootBtn.classList.remove("active");
    commandContainer.classList.remove("hidden");
    troubleshootContainer.classList.add("hidden");
    document.getElementById("user-input").focus();
  } else {
    troubleshootBtn.classList.add("active");
    commandBtn.classList.remove("active");
    troubleshootContainer.classList.remove("hidden");
    commandContainer.classList.add("hidden");
    document.getElementById("error-input").focus();
  }
}

function appendTroubleshootPlan(plan) {
  const container = document.getElementById("chat-container");
  
  // Analysis
  const analysisDiv = document.createElement("div");
  analysisDiv.className = "message ai troubleshoot-analysis";
  analysisDiv.innerHTML = `<strong>Analysis:</strong> ${plan.analysis}`;
  container.appendChild(analysisDiv);
  
  // Risk level indicator
  const riskDiv = document.createElement("div");
  riskDiv.className = `message system risk-${plan.risk_level}`;
  riskDiv.textContent = `Risk Level: ${plan.risk_level.toUpperCase()}`;
  container.appendChild(riskDiv);
  
  // Reasoning
  if (plan.reasoning) {
    const reasonDiv = document.createElement("div");
    reasonDiv.className = "message ai";
    reasonDiv.innerHTML = `<strong>Reasoning:</strong> ${plan.reasoning}`;
    container.appendChild(reasonDiv);
  }
  
  // Diagnostic commands (if any)
  if (plan.diagnostic_commands && plan.diagnostic_commands.length > 0) {
    const diagDiv = document.createElement("div");
    diagDiv.className = "message ai troubleshoot-step";
    diagDiv.innerHTML = `<strong>Diagnostic Commands:</strong><br>${plan.diagnostic_commands.map(cmd => `• ${cmd}`).join('<br>')}`;
    container.appendChild(diagDiv);
  }
  
  // Fix commands
  if (plan.fix_commands && plan.fix_commands.length > 0) {
    const fixDiv = document.createElement("div");
    fixDiv.className = "message ai troubleshoot-step";
    fixDiv.innerHTML = `<strong>Fix Commands:</strong><br>${plan.fix_commands.map(cmd => `• ${cmd}`).join('<br>')}`;
    container.appendChild(fixDiv);
  }
  
  // Verification commands
  if (plan.verification_commands && plan.verification_commands.length > 0) {
    const verifyDiv = document.createElement("div");
    verifyDiv.className = "message ai troubleshoot-step";
    verifyDiv.innerHTML = `<strong>Verification Commands:</strong><br>${plan.verification_commands.map(cmd => `• ${cmd}`).join('<br>')}`;
    container.appendChild(verifyDiv);
  }
  
  container.scrollTop = container.scrollHeight;
}

function showTroubleshootButtons(plan) {
  const container = document.getElementById("chat-container");
  const btnGroup = document.createElement("div");
  btnGroup.className = "confirm-buttons troubleshoot-buttons";
  
  // Run Diagnostics button (if diagnostics exist)
  if (plan.diagnostic_commands && plan.diagnostic_commands.length > 0) {
    const diagBtn = document.createElement("button");
    diagBtn.textContent = "Run Diagnostics";
    diagBtn.className = "troubleshoot-action-btn";
    diagBtn.onclick = () => executeTroubleshootStep("diagnostic", plan.diagnostic_commands, btnGroup);
    btnGroup.appendChild(diagBtn);
  }
  
  // Run Fixes button
  const fixBtn = document.createElement("button");
  fixBtn.textContent = "Run Fixes";
  fixBtn.className = "troubleshoot-action-btn";
  fixBtn.onclick = () => executeTroubleshootStep("fix", plan.fix_commands, btnGroup);
  btnGroup.appendChild(fixBtn);
  
  // Cancel button
  const cancelBtn = document.createElement("button");
  cancelBtn.textContent = "Cancel";
  cancelBtn.className = "troubleshoot-cancel-btn";
  cancelBtn.onclick = () => {
    appendMessage("Troubleshooting cancelled.", "system");
    btnGroup.remove();
  };
  btnGroup.appendChild(cancelBtn);
  
  container.appendChild(btnGroup);
  container.scrollTop = container.scrollHeight;
}

function executeTroubleshootStep(stepType, commands, buttonContainer) {
  appendMessage(`Executing ${stepType} commands...`, "system");
  buttonContainer.remove();
  
  fetch("/troubleshoot/execute", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      commands: commands,
      step_type: stepType,
      host: currentHost,
      username: currentUser,
      port: 22
    })
  })
    .then(res => res.json())
    .then(data => {
      // Display results
      if (data.results) {
        data.results.forEach(result => {
          const resultDiv = document.createElement("div");
          resultDiv.className = "message system troubleshoot-result";
          resultDiv.innerHTML = `
            <strong>Command:</strong> ${result.command}<br>
            <strong>Output:</strong> <pre>${result.output || '(no output)'}</pre>
            ${result.error ? `<strong>Error:</strong> <pre>${result.error}</pre>` : ''}
          `;
          document.getElementById("chat-container").appendChild(resultDiv);
        });
      }
      
      // If this was diagnostics, offer to run fixes
      if (stepType === "diagnostic" && troubleshootPlan) {
        appendMessage("Diagnostics complete. Ready to run fixes?", "system");
        const fixBtnGroup = document.createElement("div");
        fixBtnGroup.className = "confirm-buttons";
        
        const runFixBtn = document.createElement("button");
        runFixBtn.textContent = "Run Fixes";
        runFixBtn.onclick = () => executeTroubleshootStep("fix", troubleshootPlan.fix_commands, fixBtnGroup);
        
        const cancelBtn = document.createElement("button");
        cancelBtn.textContent = "Cancel";
        cancelBtn.onclick = () => {
          appendMessage("Cancelled.", "system");
          fixBtnGroup.remove();
        };
        
        fixBtnGroup.append(runFixBtn, cancelBtn);
        document.getElementById("chat-container").appendChild(fixBtnGroup);
      }
      
      // If this was fixes, run verification
      if (stepType === "fix" && troubleshootPlan && troubleshootPlan.verification_commands.length > 0) {
        appendMessage("Fixes applied. Running verification...", "system");
        setTimeout(() => {
          executeTroubleshootStep("verification", troubleshootPlan.verification_commands, document.createElement("div"));
        }, 1000);
      }
      
      // If verification, show final status
      if (stepType === "verification") {
        const allSuccess = data.all_success;
        const statusMsg = allSuccess 
          ? "✅ Troubleshooting complete! Issue resolved." 
          : "⚠️ Verification failed. Issue may not be fully resolved.";
        appendMessage(statusMsg, "system");
      }
      
      document.getElementById("chat-container").scrollTop = document.getElementById("chat-container").scrollHeight;
    })
    .catch(err => {
      appendMessage(`Error executing ${stepType}: ${err.message}`, "system");
    });
}

function submitTroubleshoot() {
  const input = document.getElementById("error-input");
  const troubleshootBtn = document.getElementById("troubleshoot-btn");
  
  const errorText = input.value.trim();
  if (!errorText) return;
  
  appendMessage(`Error: ${errorText}`, "user");
  input.value = "";
  setButtonLoading(troubleshootBtn, true);
  
  fetch("/troubleshoot", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      error_text: errorText,
      host: currentHost,
      username: currentUser,
      port: 22,
      context: {}
    })
  })
    .then(res => res.json())
    .then(data => {
      setButtonLoading(troubleshootBtn, false);
      
      if (data.analysis) {
        troubleshootPlan = data;
        appendTroubleshootPlan(data);
        showTroubleshootButtons(data);
      } else {
        appendMessage(`Error: ${data.error || 'Failed to generate troubleshooting plan'}`, "system");
      }
    })
    .catch(err => {
      setButtonLoading(troubleshootBtn, false);
      appendMessage(`Backend error: ${err.message}`, "system");
    });
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

  // Mode toggle buttons
  const modeCommandBtn = document.getElementById("mode-command");
  const modeTroubleshootBtn = document.getElementById("mode-troubleshoot");
  
  if (modeCommandBtn) {
    modeCommandBtn.addEventListener("click", () => toggleMode("command"));
  }
  
  if (modeTroubleshootBtn) {
    modeTroubleshootBtn.addEventListener("click", () => toggleMode("troubleshoot"));
  }

  // Troubleshoot button and input
  const troubleshootBtn = document.getElementById("troubleshoot-btn");
  if (troubleshootBtn) {
    troubleshootBtn.addEventListener("click", submitTroubleshoot);
  }

  const errorInput = document.getElementById("error-input");
  if (errorInput) {
    errorInput.addEventListener("keydown", e => {
      if (e.key === "Enter" && e.ctrlKey) {
        e.preventDefault();
        submitTroubleshoot();
      }
    });
  }
});