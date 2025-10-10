/**
 * Command Generation Mode Module
 * Handles single command generation feature
 */

/**
 * Show confirmation buttons for command execution
 */
function showConfirmButtons() {
  const container = document.getElementById("chat-container");
  const btnGroup = document.createElement("div");
  btnGroup.className = "confirm-buttons";

  const yesBtn = document.createElement("button");
  yesBtn.textContent = "Yes";
  yesBtn.onclick = () => confirmCommand("yes", btnGroup);

  const noBtn = document.createElement("button");
  noBtn.textContent = "No";
  noBtn.onclick = () => confirmCommand("no", btnGroup);

  btnGroup.append(yesBtn, noBtn);
  container.appendChild(btnGroup);
  container.scrollTop = container.scrollHeight;
}

/**
 * Handle command confirmation
 */
function confirmCommand(choice, container) {
  appendMessage(`You chose: ${choice.toUpperCase()}`, "user");
  container.remove();

  if (choice === "yes") {
    // Paste and run in terminal
    if (state.terminal && state.terminalConnected) {
      state.socket.emit("terminal_input", { input: state.currentCommand + "\n" });
      appendMessage(`Executed in terminal: ${state.currentCommand}`, "system");
    } else {
      appendMessage("Terminal not connected. Please check connection.", "system");
    }
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

      if (data.ai_command) {
        state.currentCommand = data.ai_command;
        appendMessage(`${data.ai_command}`, "ai");
        showConfirmButtons();
      } else {
        appendMessage("Failed to generate command.", "system");
      }
    })
    .catch(() => {
      setButtonLoading(askBtn, false);
      appendMessage("Backend error.", "system");
    });
}
