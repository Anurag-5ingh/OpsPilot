# Troubleshooting Feature Documentation

## Overview
A separate AI-driven troubleshooting feature has been added to OpsPilot, completely independent from the existing single-command generation feature.

## Architecture

### Two Distinct Features

#### 1. **Command Generation (Existing)**
- **Purpose**: Generate single commands for specific user requests
- **Endpoint**: `POST /ask`
- **AI Handler**: `ai_shell_agent/ai_command.py`
- **Prompt**: `ai_shell_agent/prompt_config.py`
- **UI**: Blue "Ask AI" button in Command mode

#### 2. **Troubleshooting (New)**
- **Purpose**: Analyze errors and provide multi-step remediation
- **Endpoints**: 
  - `POST /troubleshoot` - Analyze error and generate plan
  - `POST /troubleshoot/execute` - Execute diagnostic/fix/verification steps
- **AI Handler**: `ai_shell_agent/ai_troubleshoot.py`
- **Prompt**: `ai_shell_agent/prompt_troubleshoot.py`
- **Workflow Engine**: `ai_shell_agent/troubleshoot_runner.py`
- **UI**: Red "Troubleshoot" button in Troubleshoot mode

## How It Works

### User Flow

1. **Switch to Troubleshoot Mode**
   - Click "Troubleshoot" button in the header
   - UI switches to show error input textarea

2. **Paste Error Message**
   - User pastes error text or describes the problem
   - Click "Troubleshoot" button or press Ctrl+Enter

3. **AI Analysis**
   - AI analyzes the error using specialized troubleshooting prompt
   - Returns:
     - Analysis of the issue
     - Diagnostic commands (optional)
     - Fix commands
     - Verification commands
     - Risk level assessment
     - Reasoning

4. **Execute Steps**
   - User sees the plan with color-coded risk level
   - Options:
     - **Run Diagnostics** (if diagnostic commands exist)
     - **Run Fixes** (execute fix commands)
     - **Cancel**

5. **Automatic Workflow**
   - If diagnostics run → offers to run fixes
   - If fixes run → automatically runs verification
   - Shows success/failure status

### API Endpoints

#### POST /troubleshoot
```json
Request:
{
  "error_text": "nginx: [emerg] bind() to 0.0.0.0:80 failed",
  "host": "10.0.0.1",
  "username": "ubuntu",
  "port": 22,
  "context": {
    "last_command": "systemctl start nginx",
    "last_output": "",
    "last_error": "Job failed"
  }
}

Response:
{
  "analysis": "Port 80 is already in use by another process",
  "diagnostic_commands": ["sudo lsof -i :80"],
  "fix_commands": ["sudo systemctl stop apache2", "sudo systemctl start nginx"],
  "verification_commands": ["sudo systemctl status nginx"],
  "reasoning": "Apache is likely running on port 80...",
  "risk_level": "medium",
  "requires_confirmation": true
}
```

#### POST /troubleshoot/execute
```json
Request:
{
  "commands": ["sudo systemctl stop apache2"],
  "step_type": "fix",
  "host": "10.0.0.1",
  "username": "ubuntu",
  "port": 22
}

Response:
{
  "step_type": "fix",
  "results": [
    {
      "command": "sudo systemctl stop apache2",
      "output": "",
      "error": "",
      "success": true
    }
  ],
  "all_success": true
}
```

## Files Created/Modified

### New Files
- `ai_shell_agent/prompt_troubleshoot.py` - Troubleshooting-specific AI prompt
- `ai_shell_agent/ai_troubleshoot.py` - AI handler for troubleshooting
- `ai_shell_agent/troubleshoot_runner.py` - Workflow execution engine

### Modified Files
- `app.py` - Added `/troubleshoot` and `/troubleshoot/execute` endpoints
- `frontend/index.html` - Added mode toggle and troubleshoot input section
- `frontend/app.js` - Added troubleshooting UI logic and API calls
- `frontend/style.css` - Added styling for troubleshoot mode

## Key Design Decisions

### Separation of Concerns
- **Different AI prompts**: Command generation uses `prompt_config.py`, troubleshooting uses `prompt_troubleshoot.py`
- **Different endpoints**: `/ask` vs `/troubleshoot`
- **Different UI modes**: Toggle between Command and Troubleshoot
- **No confusion**: AI receives completely different system prompts for each mode

### AI-Driven (No Playbooks)
- All decisions made by AI in real-time
- No hardcoded error patterns or remediation scripts
- AI adapts to any error message
- Uses conversation context for iterative troubleshooting

### Safety Features
- Risk level assessment (low/medium/high)
- User confirmation required before execution
- Step-by-step execution with visibility
- Automatic verification after fixes

## Example Scenarios

### Scenario 1: Service Down
```
User pastes: "systemctl status nginx - Active: inactive (dead)"

AI Response:
- Analysis: Nginx service is stopped
- Fix: systemctl start nginx
- Verification: systemctl status nginx, curl http://localhost
- Risk: Low
```

### Scenario 2: Port Conflict
```
User pastes: "nginx: [emerg] bind() to 0.0.0.0:80 failed (98: Address already in use)"

AI Response:
- Analysis: Port 80 already in use
- Diagnostics: lsof -i :80, netstat -tlnp | grep :80
- Fix: Stop conflicting service, start nginx
- Verification: systemctl status nginx
- Risk: Medium
```

### Scenario 3: Disk Full
```
User pastes: "No space left on device"

AI Response:
- Analysis: Disk is full
- Diagnostics: df -h, du -sh /* | sort -hr | head -10
- Fix: Clean logs, apt cache, docker images
- Verification: df -h
- Risk: Medium
```

## Testing

### Test Command Mode
1. Start app: `python app.py`
2. Connect to server
3. Stay in "Command" mode (default)
4. Type: "list all files in /tmp"
5. Verify: Single command generated, confirmation shown

### Test Troubleshoot Mode
1. Click "Troubleshoot" button
2. Paste error: "nginx: [emerg] bind() to 0.0.0.0:80 failed"
3. Click "Troubleshoot"
4. Verify: Analysis shown with diagnostic/fix/verification commands
5. Click "Run Diagnostics" or "Run Fixes"
6. Verify: Commands execute, results shown

## Future Enhancements

1. **Iterative Troubleshooting**
   - If verification fails, AI generates new approach
   - Feed diagnostic results back to AI for refined fixes

2. **Context Awareness**
   - Store last N command outputs in memory
   - Include in troubleshooting context

3. **Rollback Support**
   - If fix makes things worse, AI suggests reverting
   - Store pre-fix state for comparison

4. **Multi-Server Support**
   - Troubleshoot across multiple connected servers
   - Correlate errors between services

5. **Learning from Success**
   - Store successful troubleshooting sessions
   - Use as examples in future prompts

## Notes

- Both features use the same OpenAI client configuration
- Both features share SSH connection logic
- Conversation memory is currently separate (can be unified later)
- Temperature for troubleshooting (0.2) is lower than command generation (0.3) for consistency
