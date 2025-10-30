/**
 * Troubleshooting Mode Module
 * Handles error analysis with command generation backend
 */

window.state = window.state || {};

// Main submission handler that integrates with command-mode UI
function submitTroubleshoot() {
  const input = document.getElementById("error-input");
  const troubleshootBtn = document.getElementById("troubleshoot-btn");
  
  const errorText = input.value.trim();
  if (!errorText) return;
  
  appendMessage(`Error: ${errorText}`, "user");
  input.value = "";
  setButtonLoading(troubleshootBtn, true);
  
  // Use command-mode UI for fixes, just change backend endpoint
  fetch("/troubleshoot/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      error_text: errorText,
      host: state.currentHost,
      username: state.currentUser,
      port: 22
    })
  })
    .then(res => res.json())
    .then(data => {
      setButtonLoading(troubleshootBtn, false);

      // Show analysis summary first
      if (data.analysis || data.reasoning) {
        appendMessage(`Analysis: ${data.analysis || data.reasoning}`, 'ai');
      }

      // Prepare command data for command-mode UI
      const fixes = data.fix_commands || data.suggested_commands || [];
      if (fixes && fixes.length > 0) {
        // For each fix command, create a command data structure and show via command-mode UI
        fixes.forEach((cmd, index) => {
          const commandData = {
            final_command: cmd,
            action_text: data.analysis || `Fix #${index + 1}`,
            risk_analysis: data.risk_analysis || {}
          };
          // Use command-mode's UI for consistent experience
          if (window.Modules && window.Modules.Command) {
            window.Modules.Command.showConfirmButtons(commandData);
          } else {
            appendMessage(`Fix #${index + 1}: ${cmd}`, 'ai');
          }
        });
      } else {
        appendMessage('No suggested fixes returned from analysis.', 'system');
      }
    })
    .catch(err => {
      setButtonLoading(troubleshootBtn, false);
      appendMessage(`Backend error: ${err.message}`, "system");
    });
}

// Namespacing for modular access
(function(){
  try {
    window.Modules = window.Modules || {};
    window.Modules.Troubleshoot = { submitTroubleshoot };
  } catch (_) { /* ignore if window not available */ }
})();
