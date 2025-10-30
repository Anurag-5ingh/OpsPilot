/**
 * Command Generation Mode Module
 * Handles intelligent command generation with risk analysis and failure recovery
 */

/**
 * Show confirmation buttons with risk warning if needed
 */
function showConfirmButtons(commandData) {
  const container = document.getElementById("chat-container");
  
  // Show warning popup if command has risks
  if (commandData.risk_analysis && commandData.risk_analysis.requires_confirmation) {
    showRiskWarning(commandData, () => {
      // Show confirmation buttons after user acknowledges warning
      createConfirmationButtons(container, commandData.final_command);
    });
  } else {
    // Show confirmation buttons directly for low-risk commands
    createConfirmationButtons(container, commandData.final_command);
  }
}

/**
 * Create confirmation button group
 */
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

/**
 * Show risk warning popup
 */
function showRiskWarning(commandData, onAccept) {
  const riskAnalysis = commandData.risk_analysis;
  
  // Create modal overlay
  const overlay = document.createElement('div');
  overlay.className = 'warning-overlay';
  
  // Create warning modal
  const modal = document.createElement('div');
  modal.className = `warning-modal risk-${riskAnalysis.risk_level}`;
  
  // Warning header
  const header = document.createElement('div');
  header.className = 'warning-header';
  
  const riskIcon = getRiskIcon(riskAnalysis.risk_level);
  const title = document.createElement('h3');
  title.textContent = 'Command Risk Warning';
  
  header.appendChild(riskIcon);
  header.appendChild(title);
  
  // Warning message
  const message = document.createElement('div');
  message.className = 'warning-message';
  message.textContent = riskAnalysis.warning_message || 'This command may have unintended consequences.';
  
  // Command display
  const commandDisplay = document.createElement('div');
  commandDisplay.className = 'command-display';
  commandDisplay.innerHTML = `<code>${commandData.final_command}</code>`;
  
  // Collapsible details section
  const detailsSection = createDetailsSection(riskAnalysis);
  
  // Action buttons
  const buttonGroup = document.createElement('div');
  buttonGroup.className = 'warning-buttons';
  
  const proceedBtn = document.createElement('button');
  proceedBtn.textContent = 'I Understand, Proceed';
  proceedBtn.className = 'btn-proceed';
  proceedBtn.onclick = () => {
    overlay.remove();
    onAccept();
  };
  
  const cancelBtn = document.createElement('button');
  cancelBtn.textContent = 'Cancel';
  cancelBtn.className = 'btn-cancel-warning';
  cancelBtn.onclick = () => {
    overlay.remove();
    appendMessage('Command execution cancelled for safety.', 'system');
  };
  
  buttonGroup.appendChild(cancelBtn);
  buttonGroup.appendChild(proceedBtn);
  
  // Assemble modal
  modal.appendChild(header);
  modal.appendChild(message);
  modal.appendChild(commandDisplay);
  modal.appendChild(detailsSection);
  modal.appendChild(buttonGroup);
  
  overlay.appendChild(modal);
  document.body.appendChild(overlay);
  
  // Close on overlay click
  overlay.onclick = (e) => {
    if (e.target === overlay) {
      overlay.remove();
      appendMessage('Command execution cancelled.', 'system');
    }
  };
}

/**
 * Create collapsible details section
 */
function createDetailsSection(riskAnalysis) {
  const detailsContainer = document.createElement('div');
  detailsContainer.className = 'details-container';
  
  const toggleButton = document.createElement('button');
  toggleButton.className = 'details-toggle';
  toggleButton.textContent = '▼ View Detailed Risk Information';
  
  const detailsContent = document.createElement('div');
  detailsContent.className = 'details-content';
  detailsContent.style.display = 'none';
  
  // Affected areas
  if (riskAnalysis.affected_areas && riskAnalysis.affected_areas.length > 0) {
    const affectedSection = document.createElement('div');
    affectedSection.className = 'risk-section';
    affectedSection.innerHTML = `
      <h4>🎯 Areas Affected:</h4>
      <ul>${riskAnalysis.affected_areas.map(area => `<li>${area}</li>`).join('')}</ul>
    `;
    detailsContent.appendChild(affectedSection);
  }
  
  // Detailed impacts
  if (riskAnalysis.detailed_impacts && riskAnalysis.detailed_impacts.length > 0) {
    const impactsSection = document.createElement('div');
    impactsSection.className = 'risk-section';
    impactsSection.innerHTML = `
      <h4>⚡ Potential Impacts:</h4>
      <ul>${riskAnalysis.detailed_impacts.map(impact => `<li>${impact}</li>`).join('')}</ul>
    `;
    detailsContent.appendChild(impactsSection);
  }
  
  // Safety recommendations
  if (riskAnalysis.safety_recommendations && riskAnalysis.safety_recommendations.length > 0) {
    const recommendationsSection = document.createElement('div');
    recommendationsSection.className = 'risk-section';
    recommendationsSection.innerHTML = `
      <h4>🛡️ Safety Recommendations:</h4>
      <ul>${riskAnalysis.safety_recommendations.map(rec => `<li>${rec}</li>`).join('')}</ul>
    `;
    detailsContent.appendChild(recommendationsSection);
  }
  
  // Toggle functionality
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

/**
 * Get risk icon based on level
 */
function getRiskIcon(riskLevel) {
  const icon = document.createElement('span');
  icon.className = 'risk-icon';
  
  switch (riskLevel) {
    case 'critical':
      icon.textContent = '🚨';
      break;
    case 'high':
      icon.textContent = '⚠️';
      break;
    case 'medium':
      icon.textContent = '⚡';
      break;
    default:
      icon.textContent = 'ℹ️';
  }
  
  return icon;
}

/**
 * Handle command confirmation with execution tracking
 */
function confirmCommand(choice, container, command) {
  container.remove();

  if (choice === "yes") {
    if (typeof showToast === 'function') showToast(`Executing: ${command}`, 'info');
    executeCommand(command);
  } else {
    appendMessage("Command execution cancelled.", "user");
  }
}

/**
 * Execute command with failure tracking
 */
function executeCommand(command) {
  if (state.terminal && state.terminalConnected) {
    // Store command for failure analysis if needed
    state.lastExecutedCommand = command;
    state.commandStartTime = Date.now();
    
    // Send to terminal
    state.socket.emit("terminal_input", { input: command + "\n" });
    
    // Set up failure detection (simple timeout-based for now)
    setTimeout(() => {
      // Placeholder for failure detection mechanism
    }, 5000);
    
  } else {
    appendMessage("❌ Terminal not connected. Please check connection.", "system");
    
    // Offer alternatives for connection issues
    showConnectionAlternatives();
  }
}

/**
 * Show alternatives when terminal connection fails
 */
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

/**
 * Handle command failure with intelligent analysis
 */
function handleCommandFailure(command, errorOutput) {
  // Call the failure analysis API
  fetch('/analyze-failure', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      original_command: command,
      error_output: errorOutput
    })
  })
  .then(res => res.json())
  .then(data => {
    showFailureAnalysis(data);
  })
  .catch(error => {
    console.error('Failure analysis failed:', error);
    appendMessage('❌ Command failed. Unable to analyze the error.', 'system');
  });
}

/**
 * Show failure analysis with alternatives
 */
function showFailureAnalysis(analysisData) {
  const container = document.getElementById('chat-container');
  
  // Create failure analysis display
  const analysisDiv = document.createElement('div');
  analysisDiv.className = 'failure-analysis';
  
  // Analysis header
  const header = document.createElement('div');
  header.className = 'analysis-header';
  header.innerHTML = `
    <h4>🔍 Command Failure Analysis</h4>
    <p class="root-cause">${analysisData.failure_analysis.root_cause}</p>
  `;
  
  // Alternative solutions
  if (analysisData.alternative_solutions && analysisData.alternative_solutions.length > 0) {
    const alternativesSection = document.createElement('div');
    alternativesSection.className = 'alternatives-section';
    alternativesSection.innerHTML = '<h5>💡 Suggested Alternatives:</h5>';
    
    analysisData.alternative_solutions.forEach((alt, index) => {
      const altDiv = document.createElement('div');
      altDiv.className = 'alternative-solution';
      
      const probability = Math.round(alt.success_probability * 100);
      const probabilityClass = probability >= 80 ? 'high' : probability >= 60 ? 'medium' : 'low';
      
      altDiv.innerHTML = `
        <div class="alt-header">
          <button class="alt-execute-btn" onclick="executeAlternative('${alt.alternative_command}')">
            ▶️ Execute
          </button>
          <code class="alt-command">${alt.alternative_command}</code>
          <span class="success-probability ${probabilityClass}">${probability}%</span>
        </div>
        <div class="alt-reasoning">${alt.reasoning}</div>
        ${alt.side_effects && alt.side_effects.length > 0 ? 
          `<div class="alt-side-effects">⚠️ ${alt.side_effects.join(', ')}</div>` : ''}
      `;
      
      alternativesSection.appendChild(altDiv);
    });
    
    analysisDiv.appendChild(alternativesSection);
  }
  
  analysisDiv.appendChild(header);
  container.appendChild(analysisDiv);
  container.scrollTop = container.scrollHeight;
}

/**
 * Execute an alternative command
 */
function executeAlternative(command) {
  appendMessage(`Trying alternative: ${command}`, 'user');
  executeCommand(command);
}

// Namespacing shim for modularity (non-breaking)
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
  } catch (_) { /* ignore if window not available */ }
})();

/**
 * Copy command to clipboard
 */
function copyCommandToClipboard(command) {
  navigator.clipboard.writeText(command).then(() => {
    if (typeof showToast === 'function') showToast('Command copied to clipboard', 'success');
  }).catch(() => {
    if (typeof showToast === 'function') showToast('Copy failed', 'error');
  });
}

/**
 * Reconnect terminal
 */
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

/**
 * Submit command generation prompt
 */
function submitPrompt() {
  const input = document.getElementById("user-input");
  const askBtn = document.getElementById("ask");

  const prompt = input.value.trim();
  if (!prompt) return;

  appendMessage(prompt, "user");
  input.value = "";
  setButtonLoading(askBtn, true);
  // Route request depending on selected frontend mode. For 'command' use /ask, for 'troubleshoot' use /troubleshoot/analyze
  if (state.currentMode === 'troubleshoot') {
    // Send as troubleshoot analyze request but reuse command-mode UI for presenting fixes so frontend is identical
    fetch('/troubleshoot/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ error_text: prompt })
    })
    .then(res => res.json())
    .then(data => {
      setButtonLoading(askBtn, false);
      // Append analysis summary if available
      if (data.analysis || data.analysis_text || data.reasoning) {
        const analysisText = data.analysis || data.analysis_text || data.reasoning || '';
        appendMessage(`Analysis: ${analysisText}`, 'ai');
      }

      // If backend suggested fix commands, show all as selectable code cards
      const fixes = data.fix_commands || data.suggested_commands || [];
      if (fixes && fixes.length > 0) {
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
          copyBtn.onclick = () => copyCommandToClipboard(fixCmd);
          const execBtn = document.createElement('button');
          execBtn.className = 'code-card-execute';
          execBtn.innerHTML = '<span class="btn-icon">▶️</span> Execute';
          execBtn.onclick = () => {
            // Set current command and show confirmation
            state.currentCommand = fixCmd;
            const cmdData = { 
              final_command: fixCmd, 
              action_text: `Fix #${index + 1}`, 
              risk_analysis: data.risk_analysis || {} 
            };
            showConfirmButtons(cmdData);
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

        // Add a "Run Diagnostics" button that uses existing troubleshoot flow
        const diagBlock = document.createElement('div');
        diagBlock.className = 'diagnostic-action';
        diagBlock.innerHTML = `
          <button class="secondary-btn run-diagnostics">
            <span class="btn-icon">🔍</span> Run Deep Diagnostics
          </button>
          <small class="diagnostic-help">Run step-by-step diagnostics to verify the problem and solutions</small>
        `;
        container.appendChild(diagBlock);

        // Wire up diagnostics button to use existing troubleshoot flow
        const diagBtn = diagBlock.querySelector('.run-diagnostics');
        diagBtn.onclick = () => {
          // Import the existing troubleshoot handler
          if (window.Modules && window.Modules.Troubleshoot && typeof window.Modules.Troubleshoot.startDiagnostics === 'function') {
            window.Modules.Troubleshoot.startDiagnostics(data);
          } else if (typeof startDiagnostics === 'function') {
            startDiagnostics(data);
          } else {
            appendMessage('Diagnostic flow not available.', 'system');
          }
          // Remove this button after clicking
          diagBlock.remove();
        };
      } else {
        appendMessage('No suggested fixes returned from analysis.', 'system');
      }
    })
    .catch(err => {
      setButtonLoading(askBtn, false);
      appendMessage(`Troubleshoot backend error: ${err.message || err}`, 'system');
    });

    return;
  }

  // Default: command generation
  fetch('/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt })
  })
  .then(res => res.json())
  .then(data => {
    setButtonLoading(askBtn, false);

    if (data.ai_command || data.ai_response?.final_command) {
      const commandData = data.ai_response || { final_command: data.ai_command };
      state.currentCommand = commandData.final_command;

      // Container for description + code card
      const container = document.getElementById('chat-container');

      const block = document.createElement('div');
      block.className = 'ai-command-block';

      // Description line (comes from backend as concise action_text)
      const desc = document.createElement('p');
      desc.className = 'ai-command-desc';
      let smartText = (commandData.action_text && commandData.action_text.trim()) ? commandData.action_text.trim() : (prompt || '').trim();
      if (smartText.toLowerCase().startsWith('to ')) smartText = smartText.slice(3);
      desc.textContent = smartText.endsWith(':') ? smartText : `${smartText}:`;
      block.appendChild(desc);

      // Code card with header and copy button
      const card = document.createElement('div');
      card.className = 'code-card';

      const header = document.createElement('div');
      header.className = 'code-card-header';
      const lang = document.createElement('span');
      lang.className = 'code-card-lang';
      lang.textContent = 'bash';
      const copyBtn = document.createElement('button');
      copyBtn.className = 'code-card-copy';
      copyBtn.textContent = 'Copy code';
      copyBtn.onclick = () => copyCommandToClipboard(commandData.final_command);
      header.appendChild(lang);
      header.appendChild(copyBtn);

      const body = document.createElement('div');
      body.className = 'code-card-body';
      const pre = document.createElement('pre');
      const code = document.createElement('code');
      code.textContent = commandData.final_command;
      pre.appendChild(code);
      body.appendChild(pre);

      card.appendChild(header);
      card.appendChild(body);
      block.appendChild(card);

      container.appendChild(block);
      container.scrollTop = container.scrollHeight;

      // Show confirmation with risk awareness
      showConfirmButtons(commandData);
    } else {
      appendMessage('Failed to generate command.', 'system');
    }
  })
  .catch(() => {
    setButtonLoading(askBtn, false);
    appendMessage('Backend error.', 'system');
  });
}
/*
 * Command Generation Mode Module (renamed to camelCase)
 * Copied from command-mode.js
 */

/* ORIGINAL content copied from command-mode.js */
