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
    appendMessage(`Executing: ${command}`, "system");
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

/**
 * Copy command to clipboard
 */
function copyCommandToClipboard(command) {
  navigator.clipboard.writeText(command).then(() => {
    appendMessage(`📋 Command copied to clipboard: ${command}`, 'system');
  }).catch(() => {
    appendMessage(`📋 Copy failed. Command: ${command}`, 'system');
  });
}

/**
 * Reconnect terminal
 */
function reconnectTerminal() {
  appendMessage('🔄 Attempting to reconnect terminal...', 'system');
  // This would trigger the terminal reconnection logic
  // Implementation depends on existing terminal connection code
  if (state.socket) {
    state.socket.emit('start_ssh', {
      ip: state.currentHost,
      user: state.currentUser,
      password: state.currentPassword
    });
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

  fetch("/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
  })
    .then(res => res.json())
    .then(data => {
      setButtonLoading(askBtn, false);

      if (data.ai_command || data.ai_response?.final_command) {
        const commandData = data.ai_response || { final_command: data.ai_command };
        state.currentCommand = commandData.final_command;
        
        // Display command with risk indicator
        const riskLevel = commandData.risk_analysis?.risk_level || 'low';
        const riskIcon = getRiskIcon(riskLevel).textContent;
        
        appendMessage(`${riskIcon} ${commandData.final_command}`, "ai");
        
        // Show explanation if available
        if (commandData.explanation) {
          appendMessage(`💡 ${commandData.explanation}`, "ai-explanation");
        }
        
        // Show confirmation with risk awareness
        showConfirmButtons(commandData);
      } else {
        appendMessage("Failed to generate command.", "system");
      }
    })
    .catch(() => {
      setButtonLoading(askBtn, false);
      appendMessage("Backend error.", "system");
    });
}
/*
 * Command Generation Mode Module (renamed to camelCase)
 * Copied from command-mode.js
 */

/* ORIGINAL content copied from command-mode.js */
