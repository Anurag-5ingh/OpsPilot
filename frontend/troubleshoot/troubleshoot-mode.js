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
  
  if (plan.fix_commands && plan.fix_commands.length > 0) {
    const fixDiv = document.createElement("div");
    fixDiv.className = "message ai troubleshoot-step";
    fixDiv.innerHTML = `<strong>Fix Commands:</strong><br>${plan.fix_commands.map(cmd => `• ${cmd}`).join('<br>')}`;
    container.appendChild(fixDiv);
  }
  
  if (plan.verification_commands && plan.verification_commands.length > 0) {
    const verifyDiv = document.createElement("div");
    verifyDiv.className = "message ai troubleshoot-step";
    verifyDiv.innerHTML = `<strong>Verification Commands:</strong><br>${plan.verification_commands.map(cmd => `• ${cmd}`).join('<br>')}`;
    container.appendChild(verifyDiv);
  }
  
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
    diagBtn.onclick = () => executeTroubleshootStep("diagnostic", plan.diagnostic_commands, btnGroup);
    btnGroup.appendChild(diagBtn);
  }
  
  const fixBtn = document.createElement("button");
  fixBtn.textContent = "Run Fixes";
  fixBtn.className = "troubleshoot-action-btn";
  fixBtn.onclick = () => executeTroubleshootStep("fix", plan.fix_commands, btnGroup);
  btnGroup.appendChild(fixBtn);
  
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
      if (stepType === "diagnostic" && state.troubleshootPlan) {
        appendMessage("Diagnostics complete. Ready to run fixes?", "system");
        const fixBtnGroup = document.createElement('div');
        fixBtnGroup.className = 'confirm-buttons';
        const runFixBtn = document.createElement('button');
        runFixBtn.textContent = 'Run Fixes';
        runFixBtn.onclick = () => executeTroubleshootStep('fix', state.troubleshootPlan.fix_commands, fixBtnGroup);
        const cancelBtn = document.createElement('button'); cancelBtn.textContent = 'Cancel'; cancelBtn.onclick = () => { appendMessage('Cancelled.', 'system'); fixBtnGroup.remove(); };
        fixBtnGroup.append(runFixBtn, cancelBtn);
        document.getElementById('chat-container').appendChild(fixBtnGroup);
      }
      if (stepType === "fix" && state.troubleshootPlan && state.troubleshootPlan.verification_commands.length > 0) {
        appendMessage("Fixes applied. Running verification...", "system");
        setTimeout(() => { executeTroubleshootStep("verification", state.troubleshootPlan.verification_commands, document.createElement("div")); }, 1000);
      }
      if (stepType === "verification") {
        const allSuccess = data.all_success;
        const statusMsg = allSuccess ? "✅ Troubleshooting complete! Issue resolved." : "⚠️ Verification failed. Issue may not be fully resolved.";
        appendMessage(statusMsg, "system");
      }
      document.getElementById('chat-container').scrollTop = document.getElementById('chat-container').scrollHeight;
    })
    .catch(err => { appendMessage(`Error executing ${stepType}: ${err.message}`, "system"); });
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
