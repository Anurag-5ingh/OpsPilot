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

  // Terminal toggle
  setupTerminalToggle();

  // Unified mode selector
  setupUnifiedModeSelect();

  // Split resizer for chat/terminal panels
  setupSplitResizer();

  // If main screen is already visible (e.g., auto-login), ensure split is open
  try {
    const main = document.getElementById('main-screen');
    if (main && !main.classList.contains('hidden')) {
      openTerminalSplit();
    } else if (main) {
      // Observe visibility change to trigger split once when entering main screen
      const obs = new MutationObserver(() => {
        if (!main.classList.contains('hidden')) {
          openTerminalSplit();
          obs.disconnect();
        }
      });
      obs.observe(main, { attributes: true, attributeFilter: ['class'] });
    }
  } catch (_) {}

  // Keep terminal split state in sync with top-level modes
  document.addEventListener('mode:changed', (evt) => {
    const mode = (evt && evt.detail && evt.detail.mode) || 'command';
    if (mode === 'logs') {
      collapseTerminalSplit();
    } else {
      // command or troubleshoot (chat view)
      openTerminalSplit();
    }
  });
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

    const connectHandler = (window.Modules && window.Modules.Terminal && typeof window.Modules.Terminal.connectSSH === 'function')
      ? window.Modules.Terminal.connectSSH
      : (typeof connectSSH === 'function' ? connectSSH : null);
    if (connectHandler) connectBtn.addEventListener("click", connectHandler);
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
    const submitHandler = (window.Modules && window.Modules.Command && typeof window.Modules.Command.submitPrompt === 'function')
      ? window.Modules.Command.submitPrompt
      : (typeof submitPrompt === 'function' ? submitPrompt : null);
    if (submitHandler) askBtn.addEventListener("click", submitHandler);
  }
}

/**
 * Setup troubleshoot mode listeners
 */
function setupTroubleshootModeListeners() {
  const troubleshootBtn = document.getElementById("troubleshoot-btn");
  if (troubleshootBtn) {
    const tHandler = (window.Modules && window.Modules.Troubleshoot && typeof window.Modules.Troubleshoot.submitTroubleshoot === 'function')
      ? window.Modules.Troubleshoot.submitTroubleshoot
      : (typeof submitTroubleshoot === 'function' ? submitTroubleshoot : null);
    if (tHandler) troubleshootBtn.addEventListener("click", tHandler);
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
    const clearHandler = (window.Modules && window.Modules.Terminal && typeof window.Modules.Terminal.clearTerminal === 'function')
      ? window.Modules.Terminal.clearTerminal
      : (typeof clearTerminal === 'function' ? clearTerminal : null);
    if (clearHandler) clearBtn.addEventListener("click", clearHandler);
  }

  const reconnectBtn = document.getElementById("reconnect-terminal");
  if (reconnectBtn) {
    const reconnectHandler = (window.Modules && window.Modules.Terminal && typeof window.Modules.Terminal.reconnectTerminal === 'function')
      ? window.Modules.Terminal.reconnectTerminal
      : (typeof reconnectTerminal === 'function' ? reconnectTerminal : null);
    if (reconnectHandler) reconnectBtn.addEventListener("click", reconnectHandler);
  }

  // Back from full-screen terminal to chat UI
  const closeBtn = document.getElementById("close-terminal");
  if (closeBtn) {
    closeBtn.addEventListener("click", () => {
      const left = document.querySelector('.left-panel');
      const right = document.getElementById('terminal-panel');
      if (right && left) {
        right.classList.add('collapsed');
        right.classList.remove('full');
        left.classList.remove('hidden');
        left.classList.add('expanded');
      }
    });
  }
}

/**
 * Setup mode toggle listeners
 */
function setupModeToggleListeners() {
  const modeChatBtn = document.getElementById("mode-chat");
  const modeLogsBtn = document.getElementById("mode-logs");
  const modeTerminalBtn = document.getElementById("mode-terminal");

  if (modeChatBtn) {
    modeChatBtn.addEventListener("click", () => toggleMode("command"));
  }

  if (modeLogsBtn) {
    modeLogsBtn.addEventListener("click", () => toggleMode("logs"));
  }

  // Terminal tab removed; no handler needed

  // Defensive: delegate clicks (works even if inner spans are clicked or elements re-render)
  document.addEventListener('click', (e) => {
    const btnTerminal = e.target.closest && e.target.closest('#mode-terminal');
    const btnLogs = e.target.closest && e.target.closest('#mode-logs');
    const btnChat = e.target.closest && e.target.closest('#mode-chat');
    if (btnLogs) {
      e.preventDefault();
      toggleMode('logs');
    } else if (btnChat) {
      e.preventDefault();
      toggleMode('command');
    }
  });
}

/**
 * Unified dropdown to switch modes (command/troubleshoot)
 */
function setupUnifiedModeSelect() {
  const select = document.getElementById('mode-select');
  if (!select) return;
  // Initialize from current state
  try { select.value = (window.state && window.state.currentMode) ? window.state.currentMode : 'command'; } catch (_) {}
  select.addEventListener('change', (e) => {
    const v = e.target.value === 'troubleshoot' ? 'troubleshoot' : 'command';
    toggleMode(v);
  });
  // Keep dropdown in sync if mode changed elsewhere (e.g., header buttons)
  document.addEventListener('mode:changed', (evt) => {
    const mode = evt.detail && evt.detail.mode ? evt.detail.mode : 'command';
    if (select.value !== mode) select.value = mode;
  });
}

function setupTerminalToggle() {
  const btn = document.getElementById('toggle-terminal-btn');
  if (!btn) return;
  btn.addEventListener('click', () => {
    const right = document.getElementById('terminal-panel');
    if (!right) return;
    const isCollapsed = right.classList.contains('collapsed');
    if (isCollapsed) openTerminalSplit(); else collapseTerminalSplit();
  });
}

// Open terminal panel full-screen and initialize terminal once
function openTerminalFull() {
  const left = document.querySelector('.left-panel');
  const right = document.getElementById('terminal-panel');
  const resizer = document.getElementById('split-resizer');
  if (!left || !right) return;
  right.classList.add('full');
  right.classList.remove('collapsed');
  left.classList.add('hidden');
  left.classList.remove('expanded');
  if (resizer) resizer.classList.add('hidden');
  // Initialize terminal if needed
  const initTerm = (window.Modules && window.Modules.Terminal && typeof window.Modules.Terminal.initializeTerminal === 'function')
    ? window.Modules.Terminal.initializeTerminal
    : (typeof initializeTerminal === 'function' ? initializeTerminal : null);
  if (initTerm && !window.__terminalInitialized) {
    initTerm();
    window.__terminalInitialized = true;
  }
}

// Expose globally for inline onclick
try { window.openTerminalFull = openTerminalFull; } catch (_) {}

// Open terminal in split view (resizable side-by-side)
function openTerminalSplit() {
  const left = document.querySelector('.left-panel');
  const right = document.getElementById('terminal-panel');
  const resizer = document.getElementById('split-resizer');
  if (!left || !right || !resizer) return;
  // Ensure both panels visible
  right.classList.remove('collapsed');
  right.classList.remove('full');
  left.classList.remove('hidden');
  left.classList.add('expanded');
  resizer.classList.remove('hidden');
  // If widths are not set, set a default split 55/45
  if (!left.style.width && !right.style.width) {
    const container = document.querySelector('.split-container');
    const total = container ? container.clientWidth : window.innerWidth;
    const leftWidth = Math.round(total * 0.55);
    left.style.width = leftWidth + 'px';
    right.style.width = (total - leftWidth - resizer.offsetWidth) + 'px';
  }
  // Initialize terminal if needed
  const initTerm = (window.Modules && window.Modules.Terminal && typeof window.Modules.Terminal.initializeTerminal === 'function')
    ? window.Modules.Terminal.initializeTerminal
    : (typeof initializeTerminal === 'function' ? initializeTerminal : null);
  if (initTerm && !window.__terminalInitialized) {
    initTerm();
    window.__terminalInitialized = true;
  }
}

// Expose globally
try { window.openTerminalSplit = openTerminalSplit; } catch (_) {}

// Collapse/hide the terminal split (mirror of openTerminalSplit)
function collapseTerminalSplit() {
  const left = document.querySelector('.left-panel');
  const right = document.getElementById('terminal-panel');
  const resizer = document.getElementById('split-resizer');
  if (!left || !right) return;

  // Hide terminal panel and resizer, keep left panel expanded to full width
  right.classList.add('collapsed');
  right.classList.remove('full');
  left.classList.remove('hidden');
  left.classList.add('expanded');
  if (resizer) resizer.classList.add('hidden');

  // Reset explicit widths so the left panel can expand naturally
  try {
    left.style.width = '';
    if (right) right.style.width = '';
  } catch (_) {}
}

// Expose globally for inline calls
try { window.collapseTerminalSplit = collapseTerminalSplit; } catch (_) {}

// Draggable vertical resizer between chat and terminal panels
function setupSplitResizer() {
  const resizer = document.getElementById('split-resizer');
  const left = document.querySelector('.left-panel');
  const right = document.getElementById('terminal-panel');
  const container = document.querySelector('.split-container');
  if (!resizer || !left || !right || !container) return;

  let dragging = false;
  let startX = 0;
  let startLeftWidth = 0;

  const minLeft = 240; // px
  const minRight = 320; // px

  resizer.addEventListener('mousedown', (e) => {
    // Only enable if terminal is visible
    if (right.classList.contains('collapsed')) return;
    dragging = true;
    startX = e.clientX;
    startLeftWidth = left.getBoundingClientRect().width;
    resizer.classList.add('active');
    document.body.style.userSelect = 'none';
    document.body.style.cursor = 'col-resize';
  });

  window.addEventListener('mousemove', (e) => {
    if (!dragging) return;
    const dx = e.clientX - startX;
    const containerWidth = container.getBoundingClientRect().width;
    let newLeft = startLeftWidth + dx;
    // Clamp
    if (newLeft < minLeft) newLeft = minLeft;
    if (containerWidth - newLeft - resizer.offsetWidth < minRight) {
      newLeft = containerWidth - resizer.offsetWidth - minRight;
    }
    left.style.width = newLeft + 'px';
    right.style.width = (containerWidth - newLeft - resizer.offsetWidth) + 'px';
  });

  window.addEventListener('mouseup', () => {
    if (!dragging) return;
    dragging = false;
    resizer.classList.remove('active');
    document.body.style.userSelect = '';
    document.body.style.cursor = '';
  });
}
