/**
 * Utility Functions
 * Shared utilities used across different modules
 */

// Global state
const state = {
  currentCommand: "",
  currentHost: "",
  currentUser: "",
  currentPassword: "",
  socket: null,
  terminal: null,
  terminalConnected: false,
  currentMode: "command", // "command" or "troubleshoot"
  troubleshootPlan: null,
  serverProfile: null,
  systemAware: false
};

/**
 * Set button loading state
 */
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

/**
 * Append message to chat container
 */
function appendMessage(text, role) {
  const container = document.getElementById("chat-container");
  const msg = document.createElement("div");
  msg.className = `message ${role}`;
  msg.textContent = text;
  container.appendChild(msg);
  container.scrollTop = container.scrollHeight;
}

/**
 * Toggle between Command and Troubleshoot modes
 */
function toggleMode(mode) {
  state.currentMode = mode;
  
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

/**
 * Profile the server and update system awareness
 */
async function profileServer(host, username, port = 22, forceRefresh = false, password = "") {
  try {
    const response = await fetch("/profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        host: host,
        username: username,
        port: port,
        force_refresh: forceRefresh,
        password: password
      })
    });

    const result = await response.json();
    
    if (result.success) {
      state.serverProfile = result.profile;
      state.systemAware = true;
      
      // Show system summary in UI
      showSystemSummary(result.summary);
      
      return result;
    } else {
      console.error("Server profiling failed:", result.error);
      return null;
    }
  } catch (error) {
    console.error("Error profiling server:", error);
    return null;
  }
}

/**
 * Profile the server for system awareness
 * Show system summary in the UI
 */
function showSystemSummary(summary) {
  const container = document.getElementById("chat-container");
  const msg = document.createElement("div");
  msg.className = "message system-info";
  msg.innerHTML = `
    <div class="system-summary">
      <h4>🔍 Server Profile Discovered</h4>
      <pre>${summary}</pre>
    </div>
  `;
  container.appendChild(msg);
  container.scrollTop = container.scrollHeight;
}

/**
 * Get command suggestions for a category
 */
async function getCommandSuggestions(category) {
  try {
    const response = await fetch(`/profile/suggestions/${category}`);
    const result = await response.json();
    return result.suggestions || [];
  } catch (error) {
    console.error("Error getting suggestions:", error);
    return [];
  }
}

/**
 * Update UI to show system awareness status
 */
function updateSystemAwarenessUI() {
  const header = document.querySelector(".chat-header");
  let statusIndicator = header.querySelector(".system-status");
  
  if (!statusIndicator) {
    statusIndicator = document.createElement("div");
    statusIndicator.className = "system-status";
    header.appendChild(statusIndicator);
  }
  
  if (state.systemAware) {
    statusIndicator.innerHTML = `
      <span class="status-indicator online">🟢</span>
      <span class="status-text">System Aware</span>
    `;
  } else {
    statusIndicator.innerHTML = `
      <span class="status-indicator offline">🔴</span>
      <span class="status-text">Generic Mode</span>
    `;
  }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { 
    state, 
    setButtonLoading, 
    appendMessage, 
    toggleMode, 
    profileServer, 
    showSystemSummary, 
    getCommandSuggestions,
    updateSystemAwarenessUI
  };
}
