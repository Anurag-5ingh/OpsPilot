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
      password: state.currentPassword || undefined,
      port: state.currentPort || 22
    })
  })
    .then(res => res.json())
    .then(data => {
      setButtonLoading(troubleshootBtn, false);

      // Show analysis summary first
      if (data.analysis || data.reasoning) {
        appendMessage(`Analysis: ${data.analysis || data.reasoning}`, 'ai');
      }

      // Show analysis first
      if (data.analysis || data.reasoning) {
        appendMessage(`Analysis: ${data.analysis || data.reasoning}`, 'ai');
      }
      
      const fixes = data.fix_commands || data.suggested_commands || [];
      if (fixes && fixes.length > 0) {
        // Create a container for fix cards
        const container = document.getElementById('chat-container');
        const block = document.createElement('div');
        block.className = 'ai-command-block fixes-container';

        // Add header text showing number of fixes
        const desc = document.createElement('p');
        desc.className = 'ai-command-desc';
        desc.textContent = `${fixes.length} potential ${fixes.length === 1 ? 'fix' : 'fixes'} suggested:`;
        block.appendChild(desc);

        // Create a card for each fix command
        fixes.forEach((fixCmd, index) => {
          const card = document.createElement('div');
          card.className = 'code-card fix-card';
          
          const header = document.createElement('div');
          header.className = 'code-card-header';
          
          // Left side: language + fix number
          const leftHeader = document.createElement('div');
          leftHeader.className = 'code-card-left';
          const lang = document.createElement('span');
          lang.className = 'code-card-lang';
          lang.textContent = 'bash';
          const fixNum = document.createElement('span');
          fixNum.className = 'fix-number';
          fixNum.textContent = `Fix #${index + 1}`;
          leftHeader.appendChild(lang);
          leftHeader.appendChild(fixNum);

          // Right side: copy + execute buttons
          const actions = document.createElement('div');
          actions.className = 'code-card-actions';
          const copyBtn = document.createElement('button');
          copyBtn.className = 'code-card-copy';
          copyBtn.innerHTML = '<span class="btn-icon">📋</span> Copy';
          copyBtn.onclick = () => {
            if (window.Modules && window.Modules.Command) {
              window.Modules.Command.copyCommandToClipboard(fixCmd);
            }
          };
          const execBtn = document.createElement('button');
          execBtn.className = 'code-card-execute';
          execBtn.innerHTML = '<span class="btn-icon">▶️</span> Execute';
          execBtn.onclick = () => {
            // Use command mode's execute function
            const cmdData = { 
              final_command: fixCmd, 
              action_text: `Fix #${index + 1}`, 
              risk_analysis: data.risk_analysis || {} 
            };
            if (window.Modules && window.Modules.Command) {
              window.Modules.Command.showConfirmButtons(cmdData);
            }
          };
          actions.appendChild(copyBtn);
          actions.appendChild(execBtn);

          header.appendChild(leftHeader);
          header.appendChild(actions);

          const body = document.createElement('div');
          body.className = 'code-card-body';
          const pre = document.createElement('pre');
          const code = document.createElement('code');
          code.textContent = fixCmd;
          pre.appendChild(code);
          body.appendChild(pre);

          card.appendChild(header);
          card.appendChild(body);
          block.appendChild(card);
        });

        container.appendChild(block);
        container.scrollTop = container.scrollHeight;
      } else {
        appendMessage('No suggested fixes returned from analysis.', 'system');
      }
    })
    .catch(err => {
      setButtonLoading(troubleshootBtn, false);
      appendMessage(`Backend error: ${err.message || 'Unknown error occurred'}`, "system");
    });
}

// Namespacing for modular access
(function(){
  try {
    window.Modules = window.Modules || {};
    window.Modules.Troubleshoot = { submitTroubleshoot };
  } catch (_) { /* ignore if window not available */ }
})();
