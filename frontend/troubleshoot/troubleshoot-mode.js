/**
 * Troubleshooting Mode Module
 * Handles error analysis and multi-step remediation
 */

// Initialize state
window.state = window.state || {};
state.troubleshootPlan = null;

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

// Ensure terminal panel is visible and socket is connected (match Command mode behavior)
async function ensureTerminalReady(timeoutMs = 5000) {
  try { if (window.openTerminalSplit) window.openTerminalSplit(); } catch(_){ }
  if (state && state.socket && state.socket.connected) return true;
  // Attempt reconnect
  try {
    if (window.Modules && window.Modules.Terminal && typeof window.Modules.Terminal.reconnectTerminal === 'function') {
      window.Modules.Terminal.reconnectTerminal();
    } else if (state && state.socket && typeof state.socket.connect === 'function') {
      state.socket.connect();
    }
  } catch(_){ }
  // Wait for connection
  return new Promise((resolve) => {
    const start = Date.now();
    const iv = setInterval(() => {
      const ok = state && state.socket && state.socket.connected;
      if (ok) { clearInterval(iv); resolve(true); }
      else if (Date.now() - start > timeoutMs) { clearInterval(iv); resolve(false); }
    }, 150);
  });
}

// Execute a single command in terminal and collect a short output snapshot
async function runCommandInTerminal(command, idleMs = 800, maxMs = 5000) {
  return new Promise((resolve) => {
    const chunks = [];
    let done = false;
    let idleTimer = null;
    const finish = () => {
      if (done) return; done = true;
      try { state.socket.off('terminal_output', onChunk); } catch(_){}
      resolve({ command, output: chunks.join('') });
    };
    const onChunk = (data) => {
      try {
        if (data && typeof data.output === 'string') {
          chunks.push(data.output);
        } else if (typeof data === 'string') {
          chunks.push(data);
        }
      } catch(_){}
      if (idleTimer) clearTimeout(idleTimer);
      idleTimer = setTimeout(finish, idleMs);
    };
    try { state.socket.on('terminal_output', onChunk); } catch(_){ }
    try { if (window.openTerminalSplit) window.openTerminalSplit(); } catch(_){ }
    // Use the exact same path as Command mode for execution when available
    try {
      if (window.Modules && window.Modules.Command && typeof window.Modules.Command.executeCommand === 'function') {
        window.Modules.Command.executeCommand(command);
      } else if (state && state.socket) {
        state.socket.emit('terminal_input', { input: command + "\n" });
      }
    } catch(_){ }
    setTimeout(finish, maxMs);
  });
}

// Execute a list of commands sequentially in terminal
async function runCommandsInTerminal(commands) {
  const results = [];
  for (const cmd of (commands || [])) {
    const r = await runCommandInTerminal(cmd);
    results.push(r);
  }
  return results;
}

function summarizeResults(results) {
  if (!Array.isArray(results) || results.length === 0) return 'No output.';
  const lines = [];
  results.forEach(r => {
    const out = (r.output || '').trim().split('\n').slice(-3).join(' ');
    lines.push(`• ${r.command} → ${out ? out : '(no output)'}`);
  });
  return `Summary of results:\n${lines.join('\n')}`;
}

function verificationSucceeded(results) {
  const all = (results || []).map(r => (r.output || '').toLowerCase()).join('\n');
  return all.includes('active (running)') || all.includes('success') || all.includes('ok');
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
  if (buttonContainer && typeof buttonContainer.remove === 'function') buttonContainer.remove();

  // Prefer terminal execution to show output in terminal; fallback to API if terminal not connected
  const canUseTerminal = state && state.socket && state.socket.connected && state.terminal;
  const runAllInTerminal = async () => {
    const ready = await ensureTerminalReady();
    if (!ready) throw new Error('Terminal not ready');
    try { if (window.openTerminalSplit) window.openTerminalSplit(); } catch(_){}
    const results = await runCommandsInTerminal(commands);
    // Summarize in chat (do not dump full output)
    const summary = summarizeResults(results);
    appendMessage(summary, 'ai');
    if (stepType === 'fix' && state.troubleshootPlan && state.troubleshootPlan.verification_commands.length > 0) {
      appendMessage('Fixes applied. Running verification...', 'system');
      setTimeout(() => executeTroubleshootStep('verification', state.troubleshootPlan.verification_commands, document.createElement('div')), 600);
      return;
    }
    if (stepType === 'verification') {
      const ok = verificationSucceeded(results);
      const statusMsg = ok ? '✅ Troubleshooting complete! Issue resolved.' : '⚠️ Verification failed. Issue may not be fully resolved.';
      appendMessage(statusMsg, 'system');
      state.troubleshootAttempts = (state.troubleshootAttempts || 0) + 1;
      if (!ok && state.troubleshootAttempts < 3) {
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
      } else if (!ok) {
        appendMessage('Reached maximum attempts. Consider providing more details or checking logs.', 'system');
      }
    }
    document.getElementById('chat-container').scrollTop = document.getElementById('chat-container').scrollHeight;
  };

  if (canUseTerminal) {
    runAllInTerminal().catch(err => appendMessage(`Terminal execution error: ${err.message}`, 'system'));
    return;
  }

  // Fallback to API-based execution if terminal unavailable
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
      const results = (data && data.results) ? data.results.map(r => ({ command: r.command, output: (r.output || '') + (r.error ? ('\n' + r.error) : '') })) : [];
      const summary = summarizeResults(results);
      appendMessage(summary, 'ai');
      if (stepType === 'fix' && state.troubleshootPlan && state.troubleshootPlan.verification_commands.length > 0) {
        appendMessage('Fixes applied. Running verification...', 'system');
        setTimeout(() => executeTroubleshootStep('verification', state.troubleshootPlan.verification_commands, document.createElement('div')), 600);
        return;
      }
      if (stepType === 'verification') {
        const ok = !!(data && data.all_success);
        const statusMsg = ok ? '✅ Troubleshooting complete! Issue resolved.' : '⚠️ Verification failed. Issue may not be fully resolved.';
        appendMessage(statusMsg, 'system');
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
    // Prefer terminal execution so outputs appear in terminal window
    const canUseTerminal = state && state.socket && state.socket.connected && state.terminal;
    const doOne = async () => {
      const ready = await ensureTerminalReady();
      if (!ready) throw new Error('Terminal not ready');
      try { if (window.openTerminalSplit) window.openTerminalSplit(); } catch(_){ }
      const res = await runCommandInTerminal(cmd);
      outputs.push(res.output || '');
      const decision = analyzeDiagnostic(outputs.join('\n'));
      if (decision.confident) {
        appendMessage(`Diagnosis: ${decision.summary}. Proposing fixes.`, 'ai');
        return offerFixes(plan);
      }
      runNext();
    };
    if (canUseTerminal) doOne().catch(() => runNext());
    else {
      // Fallback to API for this step
      fetch('/troubleshoot/execute', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ commands: [cmd], step_type: 'diagnostic', host: state.currentHost, username: state.currentUser, port: 22 }) })
        .then(r => r.json())
        .then(data => {
          const r0 = (data.results && data.results[0]) || { command: cmd, output: '', error: '' };
          appendMessage(`Ran diagnostic: ${cmd}`, 'system');
          outputs.push(((r0.output || '') + '\n' + (r0.error || '')).trim());
          const decision = analyzeDiagnostic(outputs.join('\n'));
          if (decision.confident) { appendMessage(`Diagnosis: ${decision.summary}. Proposing fixes.`, 'ai'); return offerFixes(plan); }
          runNext();
        })
        .catch(() => runNext());
    }
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
