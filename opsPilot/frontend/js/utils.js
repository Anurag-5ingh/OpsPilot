/**
 * Utility Functions
 * Shared utilities used across different modules
 */

// Global state
const state = {
  currentCommand: "",
  currentHost: "",
  currentUser: "",
  socket: null,
  terminal: null,
  terminalConnected: false,
  currentMode: "command", // "command" or "troubleshoot"
  troubleshootPlan: null
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

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { state, setButtonLoading, appendMessage, toggleMode };
}
