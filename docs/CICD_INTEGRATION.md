# CI/CD Integration for OpsPilot

This document describes the CI/CD integration feature that has been added to OpsPilot to automatically fetch build logs, detect failed pipelines, and provide AI-generated fix suggestions.

## Overview

The CI/CD integration connects OpsPilot with Jenkins and Ansible to:

1. **Connect to Jenkins and Ansible** with minimal user setup
2. **Fetch builds** related to currently connected servers (not every build)
3. **Show build history** (passed and failed) in a "Logs" section
4. **Analyze failed builds** and show error logs with a "Fix" button
5. **Generate AI suggestions** for terminal commands to fix issues
6. **Execute commands** only after explicit user confirmation

## Architecture

### Backend Components

#### 1. Database Models (`ai_shell_agent/modules/cicd/models.py`)
- `JenkinsConfig`: Stores Jenkins server configurations
- `AnsibleConfig`: Stores Ansible configurations with optional Git sync
- `BuildLog`: Stores Jenkins build information and status
- `FixHistory`: Records fix attempts and results

#### 2. Services

**Jenkins Service** (`jenkins_service.py`)
- REST API client for Jenkins with Basic Auth
- Fetches builds filtered by server context
- Retrieves console logs for analysis
- Supports job parameter extraction for server targeting

**Ansible Service** (`ansible_service.py`)
- Manages local Ansible paths and Git repositories
- Automatically syncs from GitHub with credentials
- Maps Jenkins jobs to relevant playbooks
- Validates playbook syntax and suggests fixes

**AI Log Analyzer** (`ai_analyzer.py`)
- Analyzes Jenkins console logs using AI
- Identifies error patterns and root causes
- Generates specific fix commands
- Suggests relevant Ansible playbooks

#### 3. Background Worker (`background_worker.py`)
- Periodically polls Jenkins for new builds (every 15 minutes)
- Automatically analyzes failed builds
- Syncs Ansible repositories from Git
- Cleans up old build data

#### 4. API Endpoints
- `POST /cicd/jenkins/connect` - Configure Jenkins connection
- `POST /cicd/ansible/connect` - Configure Ansible setup
- `GET /cicd/builds` - Fetch builds for a server
- `GET /cicd/builds/{id}/logs` - Get console logs
- `POST /cicd/builds/{id}/analyze` - Analyze failed build
- `POST /cicd/fix/execute` - Execute fix commands

### Frontend Components

#### 1. Logs Mode (`frontend/js/logs-mode.js`)
- New mode alongside Command and Troubleshoot
- Configuration interface for Jenkins/Ansible
- Build history table with status indicators
- Interactive fix suggestion workflow

#### 2. UI Features
- Server-filtered build fetching
- Real-time console log viewing
- AI analysis results display
- Command confirmation before execution
- Live command execution output

## User Workflow

### Initial Setup
1. User connects to a server (existing SSH flow)
2. User configures Jenkins connection:
   - Base URL, username, API token
   - Connection test and validation
3. User configures Ansible (optional):
   - Local path to playbooks
   - Optional GitHub repository for sync

### Daily Usage
1. Switch to "Logs" mode in OpsPilot
2. Enter server name and fetch builds
3. View build history table showing:
   - Job name, build number, status
   - Duration and timestamp
   - View Logs and Fix actions
4. For failed builds, click "Fix":
   - AI analyzes console logs
   - Shows error summary and root cause
   - Suggests specific fix commands
   - User confirms before execution
5. Commands execute on the connected server via SSH
6. Results are displayed with success/failure status

## Security Features

### Credential Management
- API tokens stored using existing SSH secrets infrastructure
- AES256 encryption for sensitive data
- No plain-text passwords in database
- Secure storage with keyring integration

### Command Execution Safety
- **ALL commands require explicit user confirmation**
- No auto-fix functionality - user must approve each command
- Commands execute through existing SSH infrastructure
- Full audit trail of all executed commands
- Real-time command output streaming

### Access Control
- User-scoped configurations (no cross-user access)
- Read-only Jenkins API tokens preferred
- Log sanitization to prevent secret leakage

## Configuration Examples

### Jenkins Setup
```json
{
  "name": "Production Jenkins",
  "base_url": "https://jenkins.example.com",
  "username": "opspilot",
  "api_token": "11abc123def456..."
}
```

### Ansible Setup
```json
{
  "name": "Production Playbooks",
  "local_path": "/opt/ansible/playbooks",
  "git_repo_url": "https://github.com/company/ansible-playbooks.git",
  "git_branch": "main"
}
```

## API Usage Examples

### Fetch Builds
```bash
GET /cicd/builds?jenkins_config_id=1&server_name=web-01&limit=20
```

### Analyze Failed Build
```bash
POST /cicd/builds/123/analyze
{
  "jenkins_config_id": 1,
  "ansible_config_id": 2
}
```

### Execute Fix Commands
```bash
POST /cicd/fix/execute
{
  "commands": ["sudo systemctl restart nginx"],
  "host": "web-01.example.com",
  "username": "deploy"
}
```

## Technical Implementation Details

### Build Filtering
- Jobs filtered by server name in job titles
- Parameter-based filtering (--limit, host=)
- Environment variable detection
- Ansible inventory parsing

### AI Analysis Pipeline
1. **Pattern Recognition**: Quick regex-based error categorization
2. **AI Analysis**: Deep log analysis using existing command generation AI
3. **Fix Generation**: Context-aware command suggestions
4. **Ansible Integration**: Playbook recommendations based on error types

### Background Processing
- Scheduled with Python `schedule` library
- Configurable polling intervals (default 15 minutes)
- Automatic failure analysis for new builds
- Git repository synchronization every 6 hours

## Dependencies Added
- `requests>=2.25.0` - HTTP client for Jenkins API
- `PyYAML>=6.0` - YAML parsing for Ansible files
- `GitPython>=3.1.0` - Git repository operations
- `schedule>=1.2.0` - Background task scheduling

## Database Schema

### Jenkins Configurations
```sql
CREATE TABLE jenkins_configs (
    id INTEGER PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    base_url TEXT NOT NULL,
    username TEXT NOT NULL,
    api_token_secret_id TEXT,
    created_at TIMESTAMP,
    last_sync TIMESTAMP
);
```

### Build Logs
```sql
CREATE TABLE build_logs (
    id INTEGER PRIMARY KEY,
    job_name TEXT NOT NULL,
    build_number INTEGER NOT NULL,
    status TEXT NOT NULL,
    duration INTEGER,
    started_at TIMESTAMP,
    jenkins_url TEXT,
    target_server TEXT,
    console_log_url TEXT,
    created_at TIMESTAMP
);
```

### Fix History
```sql
CREATE TABLE fix_history (
    id INTEGER PRIMARY KEY,
    build_id INTEGER,
    server_id TEXT,
    commands TEXT,  -- JSON array
    error_summary TEXT,
    execution_result TEXT,  -- JSON
    executed_at TIMESTAMP,
    user_confirmed BOOLEAN,
    success BOOLEAN
);
```

## Monitoring and Logging

The system includes comprehensive logging for:
- Jenkins API calls and responses
- Build analysis results
- Command executions and results
- Background worker activity
- Error conditions and failures

All activities are logged with timestamps and context for troubleshooting and audit purposes.

## Future Enhancements

Potential improvements for future versions:
1. **Webhook Integration**: Replace polling with Jenkins webhooks
2. **Multi-Server Deployments**: Handle complex deployment pipelines
3. **Advanced Playbook Mapping**: ML-based job-to-playbook matching
4. **Custom Fix Templates**: User-defined fix patterns
5. **Integration with Other CI/CD**: GitLab CI, GitHub Actions, etc.
6. **Metrics Dashboard**: Build success rates, fix success rates
7. **Team Collaboration**: Shared configurations and fix history

## Troubleshooting

Common issues and solutions:

1. **Jenkins Connection Failed**: Check URL, credentials, and network access
2. **No Builds Fetched**: Verify server name filtering and job configurations
3. **Analysis Failed**: Check console log accessibility and AI service availability
4. **Command Execution Failed**: Verify SSH connectivity and permissions
5. **Background Worker Not Running**: Check logs for startup errors and dependencies

For detailed logs, check the application log files and the CI/CD specific log entries.