/**
 * Unified Chat Mode Module
 * Consolidates Command and Troubleshoot frontend logic so both modes share the
 * same Command UI and execution flow. Exposes Modules.Command and
 * Modules.Troubleshoot facades to keep other code compatible.
 */

// --- Command-related functions (mostly copied from the old command-mode.js) ---

function showConfirmButtons(commandData) {
  const container = document.getElementById("chat-container");
  
  if (commandData.risk_analysis && commandData.risk_analysis.requires_confirmation) {
    showRiskWarning(commandData, () => {
      createConfirmationButtons(container, commandData.final_command);
    });
  } else {
    createConfirmationButtons(container, commandData.final_command);
  }
}

function createConfirmationButtons(container, command) {
  const btnGroup = document.createElement("div");
  btnGroup.className = "confirm-buttons";

  const yesBtn = document.createElement("button");
  yesBtn.textContent = "Execute";
  yesBtn.className = "btn-execute";
  yesBtn.onclick = () => confirmCommand("yes", btnGroup, command);

  const noBtn = document.createElement("button");
  noBtn.textContent = "Cancel";
  noBtn.className = "btn-cancel";
  noBtn.onclick = () => confirmCommand("no", btnGroup, command);

  btnGroup.append(yesBtn, noBtn);
  container.appendChild(btnGroup);
  container.scrollTop = container.scrollHeight;
}

function showRiskWarning(commandData, onAccept) {
  const riskAnalysis = commandData.risk_analysis || {};
  const overlay = document.createElement('div');
  overlay.className = 'warning-overlay';
  const modal = document.createElement('div');
  modal.className = `warning-modal risk-${riskAnalysis.risk_level || 'low'}`;

  const header = document.createElement('div');
  header.className = 'warning-header';
  const riskIcon = getRiskIcon(riskAnalysis.risk_level);
  const title = document.createElement('h3');
  title.textContent = 'Command Risk Warning';
  header.appendChild(riskIcon);
  header.appendChild(title);

  const message = document.createElement('div');
  message.className = 'warning-message';
  message.textContent = riskAnalysis.warning_message || 'This command may have unintended consequences.';

  const commandDisplay = document.createElement('div');
  commandDisplay.className = 'command-display';
  commandDisplay.innerHTML = `<code>${commandData.final_command}</code>`;

  const detailsSection = createDetailsSection(riskAnalysis);

  const buttonGroup = document.createElement('div');
  buttonGroup.className = 'warning-buttons';

  const proceedBtn = document.createElement('button');
  proceedBtn.textContent = 'I Understand, Proceed';
  proceedBtn.className = 'btn-proceed';
  proceedBtn.onclick = () => { overlay.remove(); onAccept(); };

  const cancelBtn = document.createElement('button');
  cancelBtn.textContent = 'Cancel';
  cancelBtn.className = 'btn-cancel-warning';
  cancelBtn.onclick = () => { overlay.remove(); appendMessage('Command execution cancelled for safety.', 'system'); };

  buttonGroup.appendChild(cancelBtn);
  buttonGroup.appendChild(proceedBtn);

  modal.appendChild(header);
  modal.appendChild(message);
  modal.appendChild(commandDisplay);
  modal.appendChild(detailsSection);
  modal.appendChild(buttonGroup);
  overlay.appendChild(modal);
  document.body.appendChild(overlay);

  overlay.onclick = (e) => { if (e.target === overlay) { overlay.remove(); appendMessage('Command execution cancelled.', 'system'); } };
}

function createDetailsSection(riskAnalysis) {
  const detailsContainer = document.createElement('div');
  detailsContainer.className = 'details-container';
  const toggleButton = document.createElement('button');
  toggleButton.className = 'details-toggle';
  toggleButton.textContent = '▼ View Detailed Risk Information';
  const detailsContent = document.createElement('div');
  detailsContent.className = 'details-content';
  detailsContent.style.display = 'none';

  if (riskAnalysis.affected_areas && riskAnalysis.affected_areas.length > 0) {
    const affectedSection = document.createElement('div');
    affectedSection.className = 'risk-section';
    affectedSection.innerHTML = `
      <h4>🎯 Areas Affected:</h4>
      <ul>${riskAnalysis.affected_areas.map(area => `<li>${area}</li>`).join('')}</ul>
    `;
    detailsContent.appendChild(affectedSection);
  }

  if (riskAnalysis.detailed_impacts && riskAnalysis.detailed_impacts.length > 0) {
    const impactsSection = document.createElement('div');
    impactsSection.className = 'risk-section';
    impactsSection.innerHTML = `
      <h4>⚡ Potential Impacts:</h4>
      <ul>${riskAnalysis.detailed_impacts.map(impact => `<li>${impact}</li>`).join('')}</ul>
    `;
    detailsContent.appendChild(impactsSection);
  }

  if (riskAnalysis.safety_recommendations && riskAnalysis.safety_recommendations.length > 0) {
    const recommendationsSection = document.createElement('div');
    recommendationsSection.className = 'risk-section';
    recommendationsSection.innerHTML = `
      <h4>🛡️ Safety Recommendations:</h4>
      <ul>${riskAnalysis.safety_recommendations.map(rec => `<li>${rec}</li>`).join('')}</ul>
    `;
    detailsContent.appendChild(recommendationsSection);
  }

  let isExpanded = false;
  toggleButton.onclick = () => {
    isExpanded = !isExpanded;
    detailsContent.style.display = isExpanded ? 'block' : 'none';
    toggleButton.textContent = isExpanded ? '▲ Hide Detailed Information' : '▼ View Detailed Risk Information';
  };

  detailsContainer.appendChild(toggleButton);
  detailsContainer.appendChild(detailsContent);
  return detailsContainer;
}

function getRiskIcon(riskLevel) {
  const icon = document.createElement('span');
  icon.className = 'risk-icon';
  switch (riskLevel) {
    case 'critical': icon.textContent = '🚨'; break;
    case 'high': icon.textContent = '⚠️'; break;
    case 'medium': icon.textContent = '⚡'; break;
    default: icon.textContent = 'ℹ️';
  }
  return icon;
}

function confirmCommand(choice, container, command) {
  container.remove();
  if (choice === "yes") {
    if (typeof showToast === 'function') showToast(`Executing: ${command}`, 'info');
    executeCommand(command);
  } else {
    appendMessage("Command execution cancelled.", "user");
  }
}

function executeCommand(command) {
  if (state.terminal && state.terminalConnected) {
    state.lastExecutedCommand = command;
    state.commandStartTime = Date.now();
    state.socket.emit("terminal_input", { input: command + "\n" });
    setTimeout(() => {}, 5000);
  } else {
    appendMessage("❌ Terminal not connected. Please check connection.", "system");
    showConnectionAlternatives();
  }
}

function showConnectionAlternatives() {
  const container = document.getElementById("chat-container");
  const alternativesDiv = document.createElement('div');
  alternativesDiv.className = 'alternatives-container';
  alternativesDiv.innerHTML = `
    <div class="alternatives-header">🔧 Connection Issue - Try These Alternatives:</div>
    <div class="alternative-item">
      <button class="alt-btn" onclick="reconnectTerminal()">🔄 Reconnect Terminal</button>
      <span class="alt-description">Attempt to reconnect the SSH terminal</span>
    </div>
    <div class="alternative-item">
      <button class="alt-btn" onclick="copyCommandToClipboard('${state.lastExecutedCommand || state.currentCommand}')">📋 Copy Command</button>
      <span class="alt-description">Copy command to clipboard for manual execution</span>
    </div>
  `;
  container.appendChild(alternativesDiv);
  container.scrollTop = container.scrollHeight;
}

function handleCommandFailure(command, errorOutput) {
  fetch('/analyze-failure', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ original_command: command, error_output: errorOutput })
  })
  .then(res => res.json())
  .then(data => showFailureAnalysis(data))
  .catch(error => { console.error('Failure analysis failed:', error); appendMessage('❌ Command failed. Unable to analyze the error.', 'system'); });
}

function showFailureAnalysis(analysisData) {
  const container = document.getElementById('chat-container');
  const analysisDiv = document.createElement('div');
  analysisDiv.className = 'failure-analysis';
  const header = document.createElement('div');
  header.className = 'analysis-header';
  header.innerHTML = `
    <h4>🔍 Command Failure Analysis</h4>
    <p class="root-cause">${analysisData.failure_analysis?.root_cause || ''}</p>
  `;

  if (analysisData.alternative_solutions && analysisData.alternative_solutions.length > 0) {
    const alternativesSection = document.createElement('div');
    alternativesSection.className = 'alternatives-section';
    alternativesSection.innerHTML = '<h5>💡 Suggested Alternatives:</h5>';
    analysisData.alternative_solutions.forEach((alt) => {
      const altDiv = document.createElement('div');
      altDiv.className = 'alternative-solution';
      const probability = Math.round((alt.success_probability || 0) * 100);
      const probabilityClass = probability >= 80 ? 'high' : probability >= 60 ? 'medium' : 'low';
      altDiv.innerHTML = `
        <div class="alt-header">
          <button class="alt-execute-btn" onclick="executeAlternative('${alt.alternative_command}')">▶️ Execute</button>
          <code class="alt-command">${alt.alternative_command}</code>
          <span class="success-probability ${probabilityClass}">${probability}%</span>
        </div>
        <div class="alt-reasoning">${alt.reasoning || ''}</div>
        ${alt.side_effects && alt.side_effects.length > 0 ? `<div class="alt-side-effects">⚠️ ${alt.side_effects.join(', ')}</div>` : ''}
      `;
      alternativesSection.appendChild(altDiv);
    });
    analysisDiv.appendChild(alternativesSection);
  }

  analysisDiv.appendChild(header);
  container.appendChild(analysisDiv);
  container.scrollTop = container.scrollHeight;
}

function executeAlternative(command) {
  appendMessage(`Trying alternative: ${command}`, 'user');
  executeCommand(command);
}

function copyCommandToClipboard(command) {
  navigator.clipboard.writeText(command).then(() => { if (typeof showToast === 'function') showToast('Command copied to clipboard', 'success'); }).catch(() => { if (typeof showToast === 'function') showToast('Copy failed', 'error'); });
}

function reconnectTerminal() {
  if (typeof showToast === 'function') showToast('Reconnecting terminal…', 'info');
  if (window.Modules && window.Modules.Terminal && typeof window.Modules.Terminal.reconnectTerminal === 'function') {
    window.Modules.Terminal.reconnectTerminal();
    return;
  }
  if (state.socket) {
    state.socket.emit('start_ssh', { ip: state.currentHost, user: state.currentUser, password: state.currentPassword });
  }
}

// Submit prompt handler used for Command mode (also supports troubleshoot routing when state.currentMode === 'troubleshoot')
function submitPrompt() {
  const input = document.getElementById("user-input");
  const askBtn = document.getElementById("ask");
  const prompt = input.value.trim();
  if (!prompt) return;
  appendMessage(prompt, "user");
  input.value = "";
  setButtonLoading(askBtn, true);
  if (state.currentMode === 'troubleshoot') {
    fetch('/troubleshoot/analyze', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ error_text: prompt })
    })
    .then(res => res.json())
    .then(data => {
      setButtonLoading(askBtn, false);
      const analysisText = data.analysis || data.analysis_text || data.reasoning || '';
      if (analysisText) appendMessage(`Analysis: ${analysisText}`, 'ai');
      const fixes = data.fix_commands || data.suggested_commands || [];
      if (fixes && fixes.length > 0) {
        const container = document.getElementById('chat-container');
        const block = document.createElement('div');
        block.className = 'ai-command-block fixes-container';
        const desc = document.createElement('p');
        desc.className = 'ai-command-desc';
        desc.textContent = `${fixes.length} potential ${fixes.length === 1 ? 'fix' : 'fixes'} suggested:`;
        block.appendChild(desc);
        fixes.forEach((fixCmd, index) => {
          const card = document.createElement('div');
          card.className = 'code-card fix-card';
          const header = document.createElement('div'); header.className = 'code-card-header';
          const leftHeader = document.createElement('div'); leftHeader.className = 'code-card-left';
          const lang = document.createElement('span'); lang.className = 'code-card-lang'; lang.textContent = 'bash';
          const fixNum = document.createElement('span'); fixNum.className = 'fix-number'; fixNum.textContent = `Fix #${index + 1}`;
          leftHeader.appendChild(lang); leftHeader.appendChild(fixNum);
          const actions = document.createElement('div'); actions.className = 'code-card-actions';
          const copyBtn = document.createElement('button'); copyBtn.className = 'code-card-copy'; copyBtn.innerHTML = '<span class="btn-icon">📋</span> Copy'; copyBtn.onclick = () => copyCommandToClipboard(fixCmd);
          const execBtn = document.createElement('button'); execBtn.className = 'code-card-execute'; execBtn.innerHTML = '<span class="btn-icon">▶️</span> Execute';
          execBtn.onclick = () => { state.currentCommand = fixCmd; const cmdData = { final_command: fixCmd, action_text: `Fix #${index + 1}`, risk_analysis: data.risk_analysis || {} }; showConfirmButtons(cmdData); };
          actions.appendChild(copyBtn); actions.appendChild(execBtn);
          header.appendChild(leftHeader); header.appendChild(actions);
          const body = document.createElement('div'); body.className = 'code-card-body'; const pre = document.createElement('pre'); const code = document.createElement('code'); code.textContent = fixCmd; pre.appendChild(code); body.appendChild(pre);
          card.appendChild(header); card.appendChild(body); block.appendChild(card);
        });
        container.appendChild(block);
        container.scrollTop = container.scrollHeight;
      } else {
        appendMessage('No suggested fixes returned from analysis.', 'system');
      }
    })
    .catch(err => { setButtonLoading(askBtn, false); appendMessage(`Troubleshoot backend error: ${err.message || err}`, 'system'); });
    return;
  }

  // Default command generation flow
  fetch('/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ prompt }) })
  .then(res => res.json())
  .then(data => {
    setButtonLoading(askBtn, false);
    if (data.ai_command || data.ai_response?.final_command) {
      const commandData = data.ai_response || { final_command: data.ai_command };
      state.currentCommand = commandData.final_command;
      const container = document.getElementById('chat-container');
      const block = document.createElement('div'); block.className = 'ai-command-block';
      const desc = document.createElement('p'); desc.className = 'ai-command-desc';
      let smartText = (commandData.action_text && commandData.action_text.trim()) ? commandData.action_text.trim() : (prompt || '').trim();
      if (smartText.toLowerCase().startsWith('to ')) smartText = smartText.slice(3);
      desc.textContent = smartText.endsWith(':') ? smartText : `${smartText}:`;
      block.appendChild(desc);
      const card = document.createElement('div'); card.className = 'code-card';
      const header = document.createElement('div'); header.className = 'code-card-header';
      const lang = document.createElement('span'); lang.className = 'code-card-lang'; lang.textContent = 'bash';
      const copyBtn = document.createElement('button'); copyBtn.className = 'code-card-copy'; copyBtn.textContent = 'Copy code'; copyBtn.onclick = () => copyCommandToClipboard(commandData.final_command);
      header.appendChild(lang); header.appendChild(copyBtn);
      const body = document.createElement('div'); body.className = 'code-card-body'; const pre = document.createElement('pre'); const code = document.createElement('code'); code.textContent = commandData.final_command; pre.appendChild(code); body.appendChild(pre);
      card.appendChild(header); card.appendChild(body); block.appendChild(card); container.appendChild(block); container.scrollTop = container.scrollHeight; showConfirmButtons(commandData);
    } else {
      appendMessage('Failed to generate command.', 'system');
    }
  })
  .catch(() => { setButtonLoading(askBtn, false); appendMessage('Backend error.', 'system'); });
}

// --- Troubleshoot facade to preserve API used by tests and other modules ---
function submitTroubleshoot() {
  const input = document.getElementById("error-input");
  const troubleshootBtn = document.getElementById("troubleshoot-btn");
  const errorText = input.value.trim();
  if (!errorText) return Promise.resolve();
  appendMessage(`Error: ${errorText}`, "user");
  input.value = "";
  setButtonLoading(troubleshootBtn, true);

  return fetch("/troubleshoot/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ error_text: errorText, host: state.currentHost, username: state.currentUser, password: state.currentPassword || undefined, port: state.currentPort || 22 })
  })
  .then(res => res.json())
  .then(data => {
    setButtonLoading(troubleshootBtn, false);
    if (data.analysis || data.reasoning) appendMessage(`Analysis: ${data.analysis || data.reasoning}`, 'ai');
    const fixes = data.fix_commands || data.suggested_commands || [];
    if (fixes && fixes.length > 0) {
      const container = document.getElementById('chat-container');
      const block = document.createElement('div'); block.className = 'ai-command-block fixes-container';
      const desc = document.createElement('p'); desc.className = 'ai-command-desc'; desc.textContent = `${fixes.length} potential ${fixes.length === 1 ? 'fix' : 'fixes'} suggested:`; block.appendChild(desc);
      fixes.forEach((fixCmd, index) => {
        const card = document.createElement('div'); card.className = 'code-card fix-card';
        const header = document.createElement('div'); header.className = 'code-card-header';
        const leftHeader = document.createElement('div'); leftHeader.className = 'code-card-left';
        const lang = document.createElement('span'); lang.className = 'code-card-lang'; lang.textContent = 'bash';
        const fixNum = document.createElement('span'); fixNum.className = 'fix-number'; fixNum.textContent = `Fix #${index + 1}`; leftHeader.appendChild(lang); leftHeader.appendChild(fixNum);
        const actions = document.createElement('div'); actions.className = 'code-card-actions';
        const copyBtn = document.createElement('button'); copyBtn.className = 'code-card-copy'; copyBtn.innerHTML = '<span class="btn-icon">📋</span> Copy'; copyBtn.onclick = () => copyCommandToClipboard(fixCmd);
        const execBtn = document.createElement('button'); execBtn.className = 'code-card-execute'; execBtn.innerHTML = '<span class="btn-icon">▶️</span> Execute';
        execBtn.onclick = () => { const cmdData = { final_command: fixCmd, action_text: `Fix #${index + 1}`, risk_analysis: data.risk_analysis || {} }; showConfirmButtons(cmdData); };
        actions.appendChild(copyBtn); actions.appendChild(execBtn);
        header.appendChild(leftHeader); header.appendChild(actions);
        const body = document.createElement('div'); body.className = 'code-card-body'; const pre = document.createElement('pre'); const code = document.createElement('code'); code.textContent = fixCmd; pre.appendChild(code); body.appendChild(pre);
        card.appendChild(header); card.appendChild(body); block.appendChild(card);
      });
      container.appendChild(block); container.scrollTop = container.scrollHeight;
    } else {
      appendMessage('No suggested fixes returned from analysis.', 'system');
    }
  })
  .catch(err => { setButtonLoading(troubleshootBtn, false); appendMessage(`Backend error: ${err.message || 'Unknown error occurred'}`, "system"); });
}

// Namespacing shim: expose Command and Troubleshoot facades
(function(){
  try {
    window.Modules = window.Modules || {};
    window.Modules.Command = {
      showConfirmButtons,
      createConfirmationButtons,
      showRiskWarning,
      submitPrompt,
      executeCommand,
      executeAlternative,
      reconnectTerminal,
      copyCommandToClipboard
    };
    window.Modules.Troubleshoot = {
      submitTroubleshoot
    };
  } catch (_) {}
})();
