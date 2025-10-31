// Deprecated shim: delegate to the unified chat module
// This file is kept as a compatibility shim and delegates behavior to the
// new `frontend/chat/chat-mode.js`. It will be removed in a cleanup pass.

try {
  // If unified module already loaded, re-expose functions under the old name
  if (window.Modules && window.Modules.Command) {
    // no-op: Modules.Command already available
  } else {
    // Ensure shim functions exist in case code references them before chat-mode loads
    window.Modules = window.Modules || {};
    window.Modules.Command = window.Modules.Command || {};
  }
} catch (_) {}

// Provide backwards-compatible named exports when running under CommonJS in tests
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {};
}
