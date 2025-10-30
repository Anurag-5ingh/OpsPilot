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

// Backwards-compatibility: expose legacy globals that proxy to state
try {
  Object.defineProperty(window, 'currentHost', {
    get() { return state.currentHost; },
    set(v) { state.currentHost = v; }
  });
  Object.defineProperty(window, 'currentUser', {
    get() { return state.currentUser; },
    set(v) { state.currentUser = v; }
  });
  Object.defineProperty(window, 'currentPassword', {
    get() { return state.currentPassword; },
    set(v) { state.currentPassword = v; }
  });
} catch (_) { /* no-op for non-browser envs */ }

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
 * Append message to chat container (command mode only)
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

  const chatTab = document.getElementById("mode-chat");
  const logsTab = document.getElementById("mode-logs");

  const commandContainer = document.getElementById("command-input-container");
  const troubleshootContainer = document.getElementById("troubleshoot-input-container");
  const logsContainer = document.getElementById("logs-input-container");

  // Remove active class from top tabs
  [chatTab, logsTab].forEach(btn => { if (btn) btn.classList.remove("active"); });

  // Keep chat stream visible for command and troubleshoot; hide only in logs
  const chatStream = document.getElementById("chat-container");
  if (chatStream) chatStream.classList.toggle('hidden', mode === 'logs');

  // Hide all bottom input containers
  [commandContainer, troubleshootContainer, logsContainer].forEach(container => {
    if (container) container.classList.add("hidden");
  });

  // Show selected bottom container and set active tab
  if (mode === 'command') {
    // Ensure split for chat modes
    try { if (window.openTerminalSplit) window.openTerminalSplit(); } catch (_) {}
    if (chatTab) chatTab.classList.add('active');
    if (commandContainer) commandContainer.classList.remove('hidden');
    const userInput = document.getElementById('user-input');
    if (userInput) userInput.focus();
  } else if (mode === 'troubleshoot') {
    // For troubleshoot mode, reuse the Command editor UI (frontend unified). Backend behavior will differ.
    try { if (window.openTerminalSplit) window.openTerminalSplit(); } catch (_) {}
    if (chatTab) chatTab.classList.add('active');
    // Show command input container (same editor as command mode)
    if (commandContainer) commandContainer.classList.remove('hidden');
    // Ensure the dedicated troubleshoot input is hidden
    if (troubleshootContainer) troubleshootContainer.classList.add('hidden');
    const userInput = document.getElementById('user-input');
    if (userInput) userInput.focus();
  } else if (mode === 'logs') {
    // Collapse split on logs
    try { if (window.collapseTerminalSplit) window.collapseTerminalSplit(); } catch (_) {}
    if (logsTab) logsTab.classList.add('active');
    if (logsContainer) logsContainer.classList.remove('hidden');
  }

  // Notify listeners
  document.dispatchEvent(new CustomEvent('mode:changed', { detail: { mode } }));
}

// Expose for inline/global usage (defensive)
try { window.toggleMode = toggleMode; } catch (_) {}

/**
 * Profile the server and update system awareness
 */
async function profileServer(host, username, port = 22, forceRefresh = false, password = "") {
  try {
    const payload = { host: host, username: username, port: port, force_refresh: forceRefresh, password: password };
    const result = (window.Core && window.Core.api && window.Core.api.post)
      ? await window.Core.api.post("/profile", payload)
      : await (await fetch("/profile", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) })).json();
    
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
    const result = (window.Core && window.Core.api && window.Core.api.get)
      ? await window.Core.api.get(`/profile/suggestions/${category}`)
      : await (await fetch(`/profile/suggestions/${category}`)).json();
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

/**
 * Toast notifications
 */
function showToast(message, type = 'info', duration = 3500) {
  if (window.Core && window.Core.dom && typeof window.Core.dom.toast === 'function') {
    window.Core.dom.toast(message, type, duration);
    return;
  }
  try {
    const container = document.getElementById('toast-container');
    if (!container) return;
    if (type === 'error') container.innerHTML = '';
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.textContent = message;
    container.appendChild(el);
    setTimeout(() => el.remove(), duration);
  } catch (_) {}
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
    updateSystemAwarenessUI,
    showToast
  };
}
