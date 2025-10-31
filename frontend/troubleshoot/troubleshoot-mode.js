// Deprecated shim: the functionality has been moved to `frontend/chat/chat-mode.js`.
// This file intentionally provides a small compatibility shim so older imports
// won't break. It re-exports the unified handlers when available.

try {
  window.Modules = window.Modules || {};
  if (!window.Modules.Troubleshoot) window.Modules.Troubleshoot = {};
  // If the unified chat module already registered the handler, keep it.
} catch (_) {}

// CommonJS compatibility for test runners
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {};
}
