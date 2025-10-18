# OpsPilot Enhanced SSH Authentication Guide

## Overview

OpsPilot now supports advanced SSH authentication methods beyond simple password authentication. This enhanced system provides:

- **SSH Key Authentication** (RSA, ECDSA, Ed25519)
- **SSH Agent Integration** 
- **Multi-Factor Authentication (MFA)** via keyboard-interactive
- **Secure Host Key Verification**
- **Connection Profiles** for easy management
- **Bastion/Jump Host Support**
- **Secure Credential Storage**

## Quick Start

### 1. Enable Enhanced SSH

Add to your `.env` file:
```
OSPILOT_SSH_ENHANCED=true
```

### 2. Install Dependencies

The enhanced SSH features require additional Python packages. Install them:

```bash
pip install keyring cryptography
```

### 3. Choose Your Authentication Method

#### Option A: SSH Agent (Recommended)

**Windows (PowerShell as Administrator):**
```powershell
# Start SSH agent service
Start-Service ssh-agent

# Add your private key
ssh-add C:\Users\YourName\.ssh\id_ed25519
```

**macOS/Linux:**
```bash
# Start SSH agent
eval "$(ssh-agent -s)"

# Add your private key
ssh-add ~/.ssh/id_ed25519
```

#### Option B: Private Key File

1. Place your private key file in a secure location
2. Ensure proper file permissions:
   - **Windows**: Right-click → Properties → Security → Advanced → Disable inheritance
   - **macOS/Linux**: `chmod 600 ~/.ssh/id_ed25519`

#### Option C: Password or MFA

For servers requiring passwords or multi-factor authentication.

### 4. Create a Connection Profile

1. Open OpsPilot web interface
2. Click "Profiles" on the login screen
3. Fill in connection details:
   - **Name**: Descriptive name for this connection
   - **Host**: Server hostname or IP address
   - **Port**: SSH port (default: 22)
   - **Username**: Your username on the remote server
   - **Auth Method**: Choose from agent, key, password, or keyboard-interactive
   - **Key File**: Path to private key (if using key auth)
   - **Host Key Checking**: ask (default), yes (strict), or no (auto-add)

4. Click "Test Connection" to verify
5. Click "Save Profile" if test succeeds

### 5. Connect

Select your saved profile and click "Connect with Profile" instead of the manual connection fields.

## Server-Side Setup

### Public Key Authentication

1. **Generate SSH key pair** (if you don't have one):
   ```bash
   # Ed25519 (recommended)
   ssh-keygen -t ed25519 -C "your_email@example.com"
   
   # Or RSA (older systems)
   ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
   ```

2. **Copy public key to server**:
   ```bash
   # Method 1: Using ssh-copy-id
   ssh-copy-id username@server-hostname
   
   # Method 2: Manual copy
   cat ~/.ssh/id_ed25519.pub | ssh username@server-hostname "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
   ```

3. **Verify server SSH configuration** (`/etc/ssh/sshd_config`):
   ```
   PubkeyAuthentication yes
   AuthorizedKeysFile .ssh/authorized_keys
   PasswordAuthentication no  # Optional: disable passwords
   ```

4. **Restart SSH service** (if config changed):
   ```bash
   sudo systemctl restart sshd
   ```

### Multi-Factor Authentication

For servers with MFA (like Google Authenticator):

1. Ensure your server supports keyboard-interactive authentication
2. Create a profile with auth method "keyboard-interactive"
3. During connection, you'll be prompted for additional factors

## Host Key Verification

OpsPilot securely verifies server host keys to prevent man-in-the-middle attacks.

### First Connection

When connecting to a new server:

1. OpsPilot will show the host key fingerprint
2. **Verify this matches your server** (check with server admin or compare with previous connections)
3. Click "Trust" to permanently store the key
4. Future connections will verify against this stored key

### Host Key Management

- Host keys are stored in `ai_shell_agent/data/known_hosts`
- You can also load keys from your user `~/.ssh/known_hosts`
- Set "Host Key Checking" in profiles:
  - **ask**: Prompt for unknown keys (recommended)
  - **yes**: Reject unknown keys (most secure)
  - **no**: Auto-add unknown keys (least secure)

## Bastion/Jump Hosts

For connections through intermediate servers:

1. In profile creation, check "Use Bastion Host"
2. Fill in bastion details:
   - **Bastion Host**: Jump server hostname
   - **Bastion User**: Username on jump server
   - **Bastion Auth**: Authentication method for jump server
3. OpsPilot will connect through the bastion to reach your target server

## Security Features

### Secure Storage

- **SSH Agent**: Uses OS SSH agent when available
- **OS Keyring**: Credentials stored in Windows Credential Manager, macOS Keychain, or Linux Secret Service
- **Encrypted Fallback**: Local encrypted file storage with master key
- **No Plaintext**: Passwords and keys are never stored in plaintext

### Audit Logging

All connection attempts are logged to `ai_shell_agent/logs/audit.log`:
- Timestamp and connection details
- Authentication methods used
- Success/failure status
- Host key verification events
- No sensitive data (passwords/keys) logged

## Troubleshooting

### Common Issues

**"No keys available from SSH agent"**
- Solution: Start SSH agent and add your keys
- Windows: `Start-Service ssh-agent`, then `ssh-add path\to\key`
- macOS/Linux: `eval "$(ssh-agent -s)"`, then `ssh-add ~/.ssh/id_ed25519`

**"Permission denied (publickey)"**
- Check: Is your public key in the server's `~/.ssh/authorized_keys`?
- Check: Are the file permissions correct? (`chmod 600 ~/.ssh/id_ed25519`, `chmod 644 ~/.ssh/id_ed25519.pub`)
- Check: Is `PubkeyAuthentication yes` in server's `/etc/ssh/sshd_config`?

**"Host key verification failed"**
- Solution: Remove old host key and reconnect
- Or: Update known_hosts if server key legitimately changed

**"Failed to store password securely"**
- Solution: Install keyring package: `pip install keyring`
- Alternative: Set `OSPILOT_MASTER_KEY` in `.env` file

**"Connection test failed"**
- Check: Is the server accessible from your network?
- Check: Is the SSH service running on the server? (`sudo systemctl status sshd`)
- Check: Are firewall rules allowing SSH connections?

### Advanced Configuration

**Environment Variables:**
```bash
# Required for enhanced features
OSPILOT_SSH_ENHANCED=true

# Optional: Custom paths and settings
OSPILOT_MASTER_KEY=your-32-character-base64-key
OPS_KNOWN_HOSTS_PATH=custom/path/to/known_hosts

# Legacy fallback settings
REMOTE_HOST=default-server.example.com
REMOTE_USER=default-username
REMOTE_PASSWORD=default-password
REMOTE_PORT=22
```

**Key File Permissions:**
- Private keys: `600` (read/write for owner only)
- Public keys: `644` (readable by all)
- `.ssh` directory: `700` (read/write/execute for owner only)
- `authorized_keys`: `600` (read/write for owner only)

### Debugging

Enable debug logging by adding to your `.env`:
```
LOG_LEVEL=DEBUG
```

Check logs in:
- Application logs: Console output
- Audit logs: `ai_shell_agent/logs/audit.log`
- Connection logs: Look for SSH-related messages

## Migration from Legacy Authentication

If you're currently using the old password-only authentication:

1. **No immediate action needed** - legacy connections still work
2. **Recommended**: Create profiles for your regular connections
3. **Optional**: Set `OSPILOT_SSH_ENHANCED=false` to disable new features temporarily

## Best Practices

1. **Use SSH Agent**: Most convenient and secure for daily use
2. **Use Ed25519 keys**: Smaller, faster, and more secure than RSA
3. **Enable strict host key checking**: Prevents MITM attacks
4. **Use unique keys per purpose**: Different keys for different servers/roles
5. **Regularly rotate keys**: Generate new keys periodically
6. **Monitor audit logs**: Review connection attempts regularly
7. **Use bastion hosts**: For additional security layers

## Examples

### SSH Agent with Ed25519 Key

```bash
# Generate key
ssh-keygen -t ed25519 -f ~/.ssh/opspilot_ed25519

# Add to agent
ssh-add ~/.ssh/opspilot_ed25519

# Create profile in OpsPilot:
# - Auth Method: agent
# - Host Key Checking: ask
```

### Password with MFA

```bash
# Create profile in OpsPilot:
# - Auth Method: keyboard-interactive
# - Host Key Checking: ask
# - During connection, enter password + OTP when prompted
```

### Bastion Connection

```bash
# Profile settings:
# - Target: production-server.internal
# - Bastion Host: bastion.company.com  
# - Bastion User: jumpuser
# - Bastion Auth: agent
# - Target Auth: key (with private key file)
```