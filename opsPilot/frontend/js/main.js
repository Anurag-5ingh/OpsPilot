/**
 * Main Application Entry Point
 * Initializes all modules and sets up event listeners
 */

// Initialize application when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  initializeEventListeners();
});

/**
 * Initialize all event listeners
 */
function initializeEventListeners() {
  // Login screen event listeners
  setupLoginListeners();
  
  // Command mode event listeners
  setupCommandModeListeners();
  
  // Troubleshoot mode event listeners
  setupTroubleshootModeListeners();
  
  // Terminal control listeners
  setupTerminalControlListeners();
  
  // Mode toggle listeners
  setupModeToggleListeners();
}

/**
 * Setup login screen listeners
 */
function setupLoginListeners() {
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
}

/**
 * Setup command mode listeners
 */
function setupCommandModeListeners() {
  const askInput = document.getElementById("user-input");
  if (askInput) {
    askInput.addEventListener("keydown", e => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        submitPrompt();
      }
    });
  }

  const askBtn = document.getElementById("ask");
  if (askBtn) {
    askBtn.addEventListener("click", submitPrompt);
  }
}

/**
 * Setup troubleshoot mode listeners
 */
function setupTroubleshootModeListeners() {
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
}

/**
 * Setup terminal control listeners
 */
function setupTerminalControlListeners() {
  const clearBtn = document.getElementById("clear-terminal");
  if (clearBtn) {
    clearBtn.addEventListener("click", clearTerminal);
  }

  const reconnectBtn = document.getElementById("reconnect-terminal");
  if (reconnectBtn) {
    reconnectBtn.addEventListener("click", reconnectTerminal);
  }
}

/**
 * Setup mode toggle listeners
 */
function setupModeToggleListeners() {
  const modeCommandBtn = document.getElementById("mode-command");
  const modeTroubleshootBtn = document.getElementById("mode-troubleshoot");
  
  if (modeCommandBtn) {
    modeCommandBtn.addEventListener("click", () => toggleMode("command"));
  }
  
  if (modeTroubleshootBtn) {
    modeTroubleshootBtn.addEventListener("click", () => toggleMode("troubleshoot"));
  }
}
