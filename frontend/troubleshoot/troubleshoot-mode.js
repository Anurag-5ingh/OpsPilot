/**
 * Troubleshooting Mode Module
 * Handles error analysis and multi-step remediation
 */

function appendTroubleshootPlan(plan) {
  const container = document.getElementById("chat-container");
  
  const analysisDiv = document.createElement("div");
  analysisDiv.className = "message ai troubleshoot-analysis";
  analysisDiv.innerHTML = `<strong>Analysis:</strong> ${plan.analysis}`;
  container.appendChild(analysisDiv);
  
  const riskDiv = document.createElement("div");
  riskDiv.className = `message system risk-${plan.risk_level}`;
  riskDiv.textContent = `Risk Level: ${plan.risk_level.toUpperCase()}`;
  container.appendChild(riskDiv);
  
  if (plan.reasoning) {
    const reasonDiv = document.createElement("div");
    reasonDiv.className = "message ai";
    reasonDiv.innerHTML = `<strong>Reasoning:</strong> ${plan.reasoning}`;
    container.appendChild(reasonDiv);
  }
  
  if (plan.diagnostic_commands && plan.diagnostic_commands.length > 0) {
    const diagDiv = document.createElement("div");
    diagDiv.className = "message ai troubleshoot-step";
    diagDiv.innerHTML = `<strong>Diagnostic Commands:</strong><br>${plan.diagnostic_commands.map(cmd => `• ${cmd}`).join('<br>')}`;
    container.appendChild(diagDiv);
  }
  // Initially, do NOT show fixes or verification steps; these will be suggested after diagnostics run
  
  container.scrollTop = container.scrollHeight;
}

function showTroubleshootButtons(plan) {
  const container = document.getElementById("chat-container");
  const btnGroup = document.createElement("div");
  btnGroup.className = "confirm-buttons troubleshoot-buttons";
  
  if (plan.diagnostic_commands && plan.diagnostic_commands.length > 0) {
    const diagBtn = document.createElement("button");
    diagBtn.textContent = "Run Diagnostics";
    diagBtn.className = "troubleshoot-action-btn";
    diagBtn.onclick = () => startDiagnostics(plan, btnGroup);
    btnGroup.appendChild(diagBtn);
  }
  // Do NOT show fixes yet; only after diagnostics are analyzed

  const cancelBtn = document.createElement("button");
  cancelBtn.textContent = "Cancel";
  cancelBtn.className = "troubleshoot-cancel-btn";
  cancelBtn.onclick = () => { appendMessage("Troubleshooting cancelled.", "system"); btnGroup.remove(); };
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
      host: state.currentHost,
      username: state.currentUser,
      port: 22
    })
  })
    .then(res => res.json())
    .then(data => {
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
      // Note: iterative diagnostics use startDiagnostics; here we handle fix/verification
      if (stepType === "fix" && state.troubleshootPlan && state.troubleshootPlan.verification_commands.length > 0) {
        appendMessage("Fixes applied. Running verification...", "system");
        setTimeout(() => { executeTroubleshootStep("verification", state.troubleshootPlan.verification_commands, document.createElement("div")); }, 1000);
      }
      if (stepType === "verification") {
        const allSuccess = data.all_success;
        const statusMsg = allSuccess ? "✅ Troubleshooting complete! Issue resolved." : "⚠️ Verification failed. Issue may not be fully resolved.";
        appendMessage(statusMsg, "system");
        // Simple iteration: if failed and we have not exceeded attempts, offer to re-run diagnostics
        state.troubleshootAttempts = (state.troubleshootAttempts || 0) + 1;
        if (!allSuccess && state.troubleshootAttempts < 3) {
          const retryGroup = document.createElement('div');
          retryGroup.className = 'confirm-buttons';
          const retryBtn = document.createElement('button');
          retryBtn.textContent = 'Re-run Diagnostics';
          retryBtn.onclick = () => startDiagnostics(state.troubleshootPlan, retryGroup);
          const cancelBtn = document.createElement('button');
          cancelBtn.textContent = 'Stop';
          cancelBtn.onclick = () => { appendMessage('Stopped after failed verification.', 'system'); retryGroup.remove(); };
          retryGroup.append(retryBtn, cancelBtn);
          document.getElementById('chat-container').appendChild(retryGroup);
        } else if (!allSuccess) {
          appendMessage('Reached maximum attempts. Consider providing more details or checking logs.', 'system');
        }
      }
      document.getElementById('chat-container').scrollTop = document.getElementById('chat-container').scrollHeight;
    })
    .catch(err => { appendMessage(`Error executing ${stepType}: ${err.message}`, "system"); });
}

// Iterative diagnostics: run one command at a time and analyze after each
function startDiagnostics(plan, buttonContainer) {
  appendMessage('Starting diagnostics...', 'system');
  if (buttonContainer && typeof buttonContainer.remove === 'function') buttonContainer.remove();
  const cmds = Array.isArray(plan.diagnostic_commands) ? plan.diagnostic_commands.slice() : [];
  if (cmds.length === 0) { appendMessage('No diagnostic commands available.', 'system'); return; }
  const outputs = [];

  const runNext = () => {
    if (cmds.length === 0) {
      // Exhausted diagnostics; propose safe fixes if available
      appendMessage('Diagnostics inconclusive. You may try fixes or provide more details.', 'ai');
      return offerFixes(plan);
    }
    const cmd = cmds.shift();
    const tmpGroup = document.createElement('div');
    tmpGroup.className = 'hidden'; // not shown; just placeholder for API compat
    fetch('/troubleshoot/execute', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ commands: [cmd], step_type: 'diagnostic', host: state.currentHost, username: state.currentUser, port: 22 })
    })
      .then(r => r.json())
      .then(data => {
        const res = (data.results && data.results[0]) || { command: cmd, output: '', error: '' };
        const resultDiv = document.createElement('div');
        resultDiv.className = 'message system troubleshoot-result';
        resultDiv.innerHTML = `
          <strong>Command:</strong> ${res.command}<br>
          <strong>Output:</strong> <pre>${res.output || '(no output)'}</pre>
          ${res.error ? `<strong>Error:</strong> <pre>${res.error}</pre>` : ''}
        `;
        document.getElementById('chat-container').appendChild(resultDiv);
        outputs.push((res.output || '') + '\n' + (res.error || ''));

        // Analyze this step
        const decision = analyzeDiagnostic(outputs.join('\n'));
        if (decision.confident) {
          appendMessage(`Diagnosis: ${decision.summary} Proceeding to propose fixes.`, 'ai');
          return offerFixes(plan);
        }
        // Continue with next diagnostic
        runNext();
      })
      .catch(err => {
        appendMessage(`Diagnostic step error: ${err.message}`, 'system');
        // Try next diagnostic even if one fails
        runNext();
      });
  };

  runNext();
}

function analyzeDiagnostic(text) {
  const t = (text || '').toLowerCase();
  const signals = [
    { k: 'inactive', s: 'Service is inactive' },
    { k: 'failed', s: 'Service failed' },
    { k: 'not running', s: 'Service not running' },
    { k: 'connection refused', s: 'Connection refused' },
    { k: 'no space left', s: 'Disk full' },
    { k: 'permission denied', s: 'Permission issue' },
    { k: 'down', s: 'Service down' },
    { k: 'error', s: 'Error detected' }
  ];
  const hit = signals.find(sig => t.includes(sig.k));
  return { confident: !!hit, summary: hit ? hit.s : 'No definitive signal yet' };
}

function offerFixes(plan) {
  if (!plan || !Array.isArray(plan.fix_commands) || plan.fix_commands.length === 0) {
    appendMessage('No fix commands available from plan.', 'system');
    return;
  }
  const fixBtnGroup = document.createElement('div');
  fixBtnGroup.className = 'confirm-buttons';
  const runFixBtn = document.createElement('button');
  runFixBtn.textContent = 'Run Fixes';
  runFixBtn.onclick = () => executeTroubleshootStep('fix', plan.fix_commands, fixBtnGroup);
  const cancelBtn = document.createElement('button');
  cancelBtn.textContent = 'Cancel';
  cancelBtn.onclick = () => { appendMessage('Cancelled.', 'system'); fixBtnGroup.remove(); };
  fixBtnGroup.append(runFixBtn, cancelBtn);
  document.getElementById('chat-container').appendChild(fixBtnGroup);
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
      host: state.currentHost,
      username: state.currentUser,
      port: 22,
      context: {}
    })
  })
    .then(res => res.json())
    .then(data => {
      setButtonLoading(troubleshootBtn, false);
      
      if (data.analysis) {
        state.troubleshootPlan = data;
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
/*
 * Troubleshooting Mode Module (renamed to camelCase)
 * Copied from troubleshoot-mode.js
 */

/* ORIGINAL content copied from troubleshoot-mode.js */

// Namespacing shim for modularity (non-breaking)
(function(){
  try {
    window.Modules = window.Modules || {};
    window.Modules.Troubleshoot = {
      submitTroubleshoot,
      executeTroubleshootStep,
      appendTroubleshootPlan,
      showTroubleshootButtons
    };
  } catch (_) { /* ignore if window not available */ }
})();
