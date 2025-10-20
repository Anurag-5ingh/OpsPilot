# OpsPilot CI/CD Integration Setup Guide

This guide will help you connect OpsPilot with Jenkins and Ansible to automatically analyze failed builds and get AI-powered fix suggestions.

## What You'll Get

✅ **Automatic Build Monitoring** - See all your Jenkins builds in one place  
✅ **Smart Failure Analysis** - AI analyzes why builds fail  
✅ **Fix Suggestions** - Get specific commands to fix problems  
✅ **Safe Execution** - All commands require your approval before running  
✅ **Ansible Integration** - Leverage your existing playbooks for fixes  

## Prerequisites

Before you start, make sure you have:
- OpsPilot installed and running
- Access to your Jenkins server
- (Optional) Ansible playbooks for automated fixes

## Step 1: Connect to Your Server

1. **Start OpsPilot** and connect to your server using SSH
2. Enter your server's IP address or hostname
3. Enter your username and password (or use SSH keys)
4. Click "Connect"

## Step 2: Configure Jenkins Connection

### What You Need from Jenkins

#### 2.1 Get Your Jenkins Information
- **Jenkins URL**: The web address of your Jenkins server
  - Example: `https://jenkins.mycompany.com` or `http://192.168.1.100:8080`
- **Username**: Your Jenkins login username
- **API Token**: A secure token for API access (we'll show you how to get this)

#### 2.2 Create a Jenkins API Token

1. **Log into Jenkins** in your web browser
2. Click on your **username** in the top-right corner
3. Click **"Configure"** from the dropdown menu
4. Scroll down to the **"API Token"** section
5. Click **"Add new Token"**
6. Give it a name like "OpsPilot Integration"
7. Click **"Generate"**
8. **COPY THE TOKEN** immediately - you won't be able to see it again!

   ```
   Example token: 11a1b2c3d4e5f6789abc123def456ghi
   ```

### 2.3 Configure in OpsPilot

1. **Switch to "Logs" mode** in OpsPilot (you'll see tabs: Command | Troubleshoot | Logs)
2. Click the **"Configure"** button next to Jenkins
3. Enter the information you gathered:
   - **Configuration Name**: A friendly name like "Production Jenkins"
   - **Jenkins URL**: Your Jenkins server URL
   - **Username**: Your Jenkins username  
   - **API Token**: The token you just created

4. OpsPilot will test the connection automatically
5. If successful, you'll see a confirmation message

### Common Jenkins Setup Issues

❌ **"Cannot connect to Jenkins server"**  
→ Check that the URL is correct and the server is accessible  
→ Try accessing the URL in your browser first  

❌ **"Authentication failed"**  
→ Double-check your username and API token  
→ Make sure you copied the entire token  

❌ **"Access denied"**  
→ Your Jenkins user may not have sufficient permissions  
→ Contact your Jenkins administrator  

## Step 3: Configure Ansible (Optional but Recommended)

Ansible integration allows OpsPilot to suggest relevant playbooks for fixing issues.

### What You Need

#### 3.1 Local Ansible Setup
- **Ansible Installation**: Make sure Ansible is installed on the OpsPilot server
  ```bash
  # Check if Ansible is installed
  ansible --version
  
  # Install Ansible (Ubuntu/Debian)
  sudo apt update && sudo apt install ansible
  
  # Install Ansible (CentOS/RHEL)
  sudo yum install ansible
  ```

- **Playbooks Path**: The local path where your Ansible playbooks are stored
  - Example: `/opt/ansible/playbooks` or `/home/user/ansible`

#### 3.2 Git Repository (Optional)
If your playbooks are in a Git repository:
- **Repository URL**: The HTTPS URL of your Git repository
  - Example: `https://github.com/mycompany/ansible-playbooks.git`
- **Branch**: The branch to use (usually 'main' or 'master')

### 3.3 Configure in OpsPilot

1. In the Logs mode, click **"Configure"** next to Ansible
2. Enter your information:
   - **Configuration Name**: Like "Production Playbooks"
   - **Local Path**: Where your playbooks are stored
   - **Git Repository URL**: (Optional) Your Git repository URL
   - **Branch**: (Optional) Git branch to use

3. OpsPilot will test the configuration and sync playbooks if needed

### Setting Up Git Access (If Using Private Repository)

For private repositories, you have a few options:

#### Option 1: HTTPS with Personal Access Token
1. Create a personal access token in your Git provider (GitHub, GitLab, etc.)
2. Use URL format: `https://username:token@github.com/mycompany/ansible-playbooks.git`

#### Option 2: SSH Keys (Advanced)
1. Set up SSH keys on the OpsPilot server
2. Use SSH URL format: `git@github.com:mycompany/ansible-playbooks.git`

## Step 4: Using the CI/CD Integration

### 4.1 Viewing Build History

1. **Switch to Logs mode** in OpsPilot
2. **Enter a server name** in the "Server Name" field
   - This filters builds to only show ones related to your current server
   - Example: "web-01", "database-server", "api-prod"
3. **Click "Fetch Builds"**
4. You'll see a table with:
   - Job names and build numbers
   - Status (Success, Failure, etc.)
   - Duration and timestamps
   - Action buttons (View Logs, Fix)

### 4.2 Analyzing Failed Builds

When you see a failed build (red status):

1. **Click "View Logs"** to see the full console output
2. **Click "Fix"** to get AI analysis and suggestions

The AI will:
- Analyze the build failure logs
- Identify the root cause
- Suggest specific commands to fix the problem
- Recommend relevant Ansible playbooks (if configured)

### 4.3 Applying Fixes

When you get fix suggestions:

1. **Review the AI analysis** carefully
   - Read the error summary and root cause
   - Check the suggested commands
2. **Click "Execute Fix Commands"** if you agree
3. **Confirm** that you want to run the commands
4. Watch the **real-time output** as commands execute
5. See the **results** - success or failure for each command

> ⚠️ **Safety Note**: OpsPilot will NEVER run commands automatically. You must always review and approve each command before it runs.

## Step 5: Understanding the Results

### Build Status Colors
- 🟢 **Green (Success)**: Build completed successfully
- 🔴 **Red (Failure)**: Build failed with errors
- 🟡 **Yellow (Unstable)**: Build completed with warnings
- ⚫ **Gray (Aborted)**: Build was stopped/cancelled

### AI Analysis Information
- **Error Summary**: A brief description of what went wrong
- **Root Cause**: The AI's assessment of why it failed
- **Categories**: Types of errors detected (network, permissions, etc.)
- **Suggested Commands**: Specific terminal commands to fix issues
- **Ansible Playbooks**: Relevant automation scripts (if available)

## Troubleshooting Common Issues

### "No builds found"
- Check that you entered the correct server name
- Verify that your Jenkins jobs include the server name in the job name or parameters
- Try leaving the server name blank to see all builds

### "Analysis failed"
- Check that the build logs are accessible in Jenkins
- Verify your Jenkins API permissions include log reading
- Check the OpsPilot logs for detailed error messages

### Commands fail to execute
- Make sure you're connected to the correct server via SSH
- Check that you have the necessary permissions for the suggested commands
- Some commands may require `sudo` access

### Ansible playbooks not suggested
- Verify that Ansible is installed and accessible
- Check that your playbooks path is correct
- Ensure playbooks are properly formatted YAML files
- Check the Git repository sync status

## Security Considerations

### What Information is Stored
- Jenkins server URL, username (API token encrypted)
- Ansible configuration paths (no sensitive data)
- Build metadata and analysis results
- Command execution history (for audit purposes)

### What is NOT Stored
- Your Jenkins password (only API tokens)
- Private keys or sensitive credentials
- Full build logs (only analyzed excerpts)
- Executed command outputs containing secrets

### Best Practices
- Use dedicated Jenkins user accounts with minimal required permissions
- Regularly rotate API tokens
- Review suggested commands before execution
- Monitor command execution logs
- Keep OpsPilot server secure and updated

## Getting Help

### Log Files
If something isn't working, check the OpsPilot log files for detailed error messages:
- Look for messages containing "Jenkins", "Ansible", or "CICD"
- Pay attention to ERROR and WARNING level messages

### Common Solutions
1. **Restart OpsPilot** if connections seem stuck
2. **Check network connectivity** between OpsPilot and Jenkins
3. **Verify permissions** for all user accounts
4. **Update configurations** if server details change

### Support Information
- Check the main OpsPilot documentation
- Review the technical documentation in `docs/CICD_INTEGRATION.md`
- Check GitHub issues for similar problems

## Quick Start Checklist

- [ ] OpsPilot is running and connected to a server
- [ ] Jenkins API token created and tested
- [ ] Jenkins configuration added to OpsPilot
- [ ] (Optional) Ansible playbooks accessible
- [ ] (Optional) Ansible configuration added to OpsPilot
- [ ] Successfully fetched builds for your server
- [ ] Tested the "View Logs" functionality
- [ ] Tested the "Fix" analysis on a failed build

Once you complete this checklist, you're ready to use OpsPilot's CI/CD integration to automatically monitor and fix build failures!

## Example Workflow

Here's what a typical workflow looks like:

1. **Morning Check**: Switch to Logs mode and fetch overnight builds
2. **Spot Failures**: See 2 failed builds for your web server
3. **Quick Analysis**: Click "Fix" on the first failure
4. **AI Insight**: "Service failed to restart due to configuration error"
5. **Review Commands**: AI suggests checking config file and restarting service
6. **Safe Execution**: Click "Execute" and approve each command
7. **Success**: Service restored, build re-triggered automatically
8. **Documentation**: Ansible playbook suggested for future automation

This turns hours of debugging into minutes of guided problem-solving!