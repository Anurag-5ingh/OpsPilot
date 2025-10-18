"""
SSH Client Module
Handles SSH connection creation and command execution with enhanced authentication
"""
import os
import io
import socket
import logging
import threading
import time
from pathlib import Path
from typing import Dict, Optional, Callable, Any
import paramiko
from paramiko.agent import Agent
from paramiko.pkey import PKey
from paramiko.ssh_exception import (
    AuthenticationException, 
    SSHException, 
    BadHostKeyException,
    PartialAuthentication
)
from dotenv import load_dotenv
from .secrets import get_secret, get_profile_secret_id
from .hostkeys import host_key_manager, HostKeyVerificationError
from .audit_logger import log_connection_attempt, log_host_key_event, log_auth_event

load_dotenv()
logger = logging.getLogger(__name__)

def create_ssh_client(host: str, user: str, port: int = 22, password: str = None):
    """
    Legacy SSH client creation for backward compatibility.
    
    Args:
        host: Remote host address
        user: SSH username
        port: SSH port (default 22)
        password: SSH password (optional)
        
    Returns:
        paramiko.SSHClient or None
    """
    ssh = paramiko.SSHClient()
    
    # Check if enhanced SSH is enabled
    enhanced_mode = os.getenv('OSPILOT_SSH_ENHANCED', 'true').lower() == 'true'
    
    if enhanced_mode:
        # Use secure host key policy
        policy = host_key_manager.create_policy(strict_mode="no")  # Auto-add for legacy compatibility
        ssh.set_missing_host_key_policy(policy)
    else:
        # Legacy behavior
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        if password:
            ssh.connect(host, username=user, port=port, password=password, timeout=30)
        else:
            ssh.connect(host, username=user, port=port, timeout=30)
        
        # Set keepalive
        ssh.get_transport().set_keepalive(60)
        
        logger.info(f"SSH connection established to {user}@{host}:{port}")
        
        # Log successful connection
        log_connection_attempt(
            host=host,
            username=user,
            auth_method="password" if password else "key_or_agent",
            result="success"
        )
        
        return ssh
    except Exception as e:
        logger.error(f"SSH connection failed to {user}@{host}:{port}: {e}")
        
        # Log failed connection
        log_connection_attempt(
            host=host,
            username=user,
            auth_method="password" if password else "key_or_agent",
            result="failure",
            error_summary=str(e)[:200]
        )
        
        return None

def connect_with_profile(profile: Dict, 
                        on_auth_prompt: Optional[Callable] = None,
                        on_hostkey_decision: Optional[Callable] = None) -> Optional[paramiko.SSHClient]:
    """
    Connect to SSH server using a connection profile with advanced authentication.
    
    Args:
        profile: Connection profile dictionary
        on_auth_prompt: Callback for interactive auth prompts (title, instructions, prompts) -> responses
        on_hostkey_decision: Callback for unknown host keys (hostname, key_type, fingerprint) -> bool
        
    Returns:
        Connected SSH client or None on failure
    """
    try:
        # Extract profile information
        host = profile['host']
        port = profile.get('port', 22)
        username = profile['username']
        auth_method = profile.get('auth_method', 'password')
        strict_mode = profile.get('strict_host_key_checking', 'ask')
        
        logger.info(f"Connecting to {username}@{host}:{port} using {auth_method} auth")
        
        # Handle bastion/jump host if configured
        if profile.get('bastion'):
            return _connect_via_bastion(profile, on_auth_prompt, on_hostkey_decision)
        
        # Create SSH client with host key policy
        ssh_client = paramiko.SSHClient()
        policy = host_key_manager.create_policy(
            strict_mode=strict_mode,
            on_unknown_host=on_hostkey_decision
        )
        ssh_client.set_missing_host_key_policy(policy)
        
        # Attempt connection with authentication
        success = _authenticate_connection(
            ssh_client, profile, on_auth_prompt
        )
        
        if success:
            # Set keepalive for connection health
            ssh_client.get_transport().set_keepalive(60)
            logger.info(f"Successfully connected to {username}@{host}:{port}")
            return ssh_client
        else:
            ssh_client.close()
            return None
            
    except Exception as e:
        logger.error(f"Profile connection failed: {e}")
        return None

def _authenticate_connection(ssh_client: paramiko.SSHClient, 
                           profile: Dict,
                           on_auth_prompt: Optional[Callable] = None) -> bool:
    """
    Authenticate SSH connection based on profile settings.
    
    Returns:
        True if authentication successful, False otherwise
    """
    host = profile['host']
    port = profile.get('port', 22)
    username = profile['username']
    auth_method = profile['auth_method']
    
    try:
        # First, establish the transport connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(30)
        sock.connect((host, port))
        
        transport = paramiko.Transport(sock)
        transport.start_client()
        
        # Store transport in SSH client
        ssh_client._transport = transport
        
        # Authenticate based on method
        if auth_method == 'agent':
            return _auth_with_agent(transport, username)
        elif auth_method == 'key':
            return _auth_with_key(transport, username, profile)
        elif auth_method == 'password':
            return _auth_with_password(transport, username, profile)
        elif auth_method == 'keyboard-interactive':
            return _auth_with_keyboard_interactive(transport, username, profile, on_auth_prompt)
        else:
            logger.error(f"Unsupported auth method: {auth_method}")
            return False
            
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        return False

def _auth_with_agent(transport: paramiko.Transport, username: str) -> bool:
    """Authenticate using SSH agent."""
    try:
        agent = Agent()
        agent_keys = agent.get_keys()
        
        if not agent_keys:
            logger.warning("No keys available from SSH agent")
            return False
        
        for key in agent_keys:
            try:
                transport.auth_publickey(username, key)
                logger.info(f"Agent authentication successful with {key.get_name()} key")
                return True
            except AuthenticationException:
                continue
        
        logger.error("Agent authentication failed with all available keys")
        return False
        
    except Exception as e:
        logger.error(f"Agent authentication error: {e}")
        return False

def _auth_with_key(transport: paramiko.Transport, username: str, profile: Dict) -> bool:
    """Authenticate using private key."""
    try:
        # Get private key data
        private_key_data = None
        
        if profile.get('key_source') == 'stored' and profile.get('private_key_secret_id'):
            # Load from secure storage
            private_key_data = get_secret(profile['private_key_secret_id'])
        elif profile.get('_temp_private_key'):
            # Temporary key data for testing
            private_key_data = profile['_temp_private_key']
        elif profile.get('key_path'):
            # Load from file
            key_path = Path(profile['key_path']).expanduser()
            if key_path.exists():
                private_key_data = key_path.read_text()
        
        if not private_key_data:
            logger.error("No private key data available")
            return False
        
        # Get passphrase if needed
        passphrase = None
        if profile.get('passphrase_secret_id'):
            passphrase = get_secret(profile['passphrase_secret_id'])
        elif profile.get('_temp_passphrase'):
            passphrase = profile['_temp_passphrase']
        
        # Load private key
        key_obj = _load_private_key(private_key_data, passphrase, profile.get('key_type', 'auto'))
        if not key_obj:
            return False
        
        # Authenticate
        transport.auth_publickey(username, key_obj)
        logger.info(f"Key authentication successful with {key_obj.get_name()} key")
        return True
        
    except AuthenticationException as e:
        logger.error(f"Key authentication failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Key authentication error: {e}")
        return False

def _auth_with_password(transport: paramiko.Transport, username: str, profile: Dict) -> bool:
    """Authenticate using password."""
    try:
        # Get password
        password = None
        if profile.get('password_secret_id'):
            password = get_secret(profile['password_secret_id'])
        elif profile.get('_temp_password'):
            password = profile['_temp_password']
        
        if not password:
            logger.error("No password available")
            return False
        
        transport.auth_password(username, password)
        logger.info("Password authentication successful")
        return True
        
    except AuthenticationException as e:
        logger.error(f"Password authentication failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Password authentication error: {e}")
        return False

def _auth_with_keyboard_interactive(transport: paramiko.Transport, 
                                  username: str, 
                                  profile: Dict,
                                  on_auth_prompt: Optional[Callable] = None) -> bool:
    """Authenticate using keyboard-interactive (MFA)."""
    try:
        def interactive_handler(title, instructions, prompt_list):
            if on_auth_prompt:
                # Convert prompts to expected format
                prompts = []
                for prompt, echo in prompt_list:
                    prompts.append({
                        'prompt': prompt,
                        'echo': echo
                    })
                
                # Call the callback
                responses = on_auth_prompt(title, instructions, prompts)
                return responses if responses else []
            else:
                # Fallback for testing or when no callback available
                logger.warning("No auth prompt callback available")
                return []
        
        transport.auth_interactive(username, interactive_handler)
        logger.info("Keyboard-interactive authentication successful")
        return True
        
    except AuthenticationException as e:
        logger.error(f"Keyboard-interactive authentication failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Keyboard-interactive authentication error: {e}")
        return False

def _load_private_key(key_data: str, passphrase: Optional[str] = None, key_type: str = 'auto') -> Optional[PKey]:
    """Load private key from string data."""
    try:
        key_file = io.StringIO(key_data)
        
        # Try different key types based on hint or auto-detect
        key_loaders = []
        
        if key_type == 'rsa' or key_type == 'auto':
            key_loaders.append(paramiko.RSAKey)
        if key_type == 'ecdsa' or key_type == 'auto':
            key_loaders.append(paramiko.ECDSAKey)
        if key_type == 'ed25519' or key_type == 'auto':
            key_loaders.append(paramiko.Ed25519Key)
        if key_type == 'dss' or key_type == 'auto':
            key_loaders.append(paramiko.DSSKey)
        
        for key_loader in key_loaders:
            try:
                key_file.seek(0)
                return key_loader.from_private_key(key_file, password=passphrase)
            except Exception:
                continue
        
        logger.error("Failed to load private key with any supported format")
        return None
        
    except Exception as e:
        logger.error(f"Error loading private key: {e}")
        return None

def _connect_via_bastion(profile: Dict, 
                        on_auth_prompt: Optional[Callable] = None,
                        on_hostkey_decision: Optional[Callable] = None) -> Optional[paramiko.SSHClient]:
    """Connect through a bastion/jump host."""
    try:
        bastion_config = profile['bastion']
        bastion_host = bastion_config['host']
        bastion_port = bastion_config.get('port', 22)
        bastion_username = bastion_config['username']
        
        logger.info(f"Connecting via bastion {bastion_username}@{bastion_host}:{bastion_port}")
        
        # Create bastion profile
        bastion_profile = {
            'host': bastion_host,
            'port': bastion_port,
            'username': bastion_username,
            'auth_method': bastion_config.get('auth_method', 'agent'),
            'strict_host_key_checking': profile.get('strict_host_key_checking', 'ask')
        }
        
        # Connect to bastion
        bastion_client = connect_with_profile(bastion_profile, on_auth_prompt, on_hostkey_decision)
        if not bastion_client:
            return None
        
        try:
            # Open channel to target through bastion
            target_host = profile['host']
            target_port = profile.get('port', 22)
            
            bastion_transport = bastion_client.get_transport()
            channel = bastion_transport.open_channel(
                'direct-tcpip',
                (target_host, target_port),
                ('', 0)
            )
            
            # Create SSH client for target using the channel as socket
            target_client = paramiko.SSHClient()
            policy = host_key_manager.create_policy(
                strict_mode=profile.get('strict_host_key_checking', 'ask'),
                on_unknown_host=on_hostkey_decision
            )
            target_client.set_missing_host_key_policy(policy)
            
            # Create target profile without bastion for direct auth
            target_profile = profile.copy()
            target_profile.pop('bastion', None)
            
            # Connect through the channel
            target_transport = paramiko.Transport(channel)
            target_transport.start_client()
            
            target_client._transport = target_transport
            
            # Authenticate to target
            auth_success = _authenticate_connection(target_client, target_profile, on_auth_prompt)
            
            if auth_success:
                target_client.get_transport().set_keepalive(60)
                logger.info(f"Successfully connected to target via bastion")
                return target_client
            else:
                target_client.close()
                return None
                
        finally:
            bastion_client.close()
            
    except Exception as e:
        logger.error(f"Bastion connection failed: {e}")
        return None


def run_shell(command: str, ssh_client=None, profile_id: str = None) -> tuple:
    """
    Execute a command over SSH with profile or legacy support.

    Args:
        command: Shell command to execute
        ssh_client: Optional existing SSH client
        profile_id: Optional profile ID to use for connection
        
    Returns:
        tuple: (stdout_str, stderr_str)
    """
    created_ssh = False

    if ssh_client is None:
        # Try profile-based connection first if profile_id provided
        if profile_id and os.getenv('OSPILOT_SSH_ENHANCED', 'true').lower() == 'true':
            try:
                from .session_manager import _get_profile_by_id
                profile = _get_profile_by_id(profile_id)
                if profile:
                    ssh_client = connect_with_profile(profile)
                    if ssh_client:
                        created_ssh = True
                    else:
                        return "", f"SSH connection failed: could not connect using profile {profile_id}"
                else:
                    return "", f"SSH connection failed: profile {profile_id} not found"
            except Exception as e:
                logger.error(f"Profile connection error: {e}")
                # Fall through to legacy connection
        
        # Fallback to legacy environment variables
        if ssh_client is None:
            remote_host = os.getenv("REMOTE_HOST")
            remote_user = os.getenv("REMOTE_USER")
            remote_password = os.getenv("REMOTE_PASSWORD", "")
            try:
                remote_port = int(os.getenv("REMOTE_PORT", 22))
            except Exception:
                remote_port = 22

            if not remote_host or not remote_user:
                return "", "SSH connection failed: no host/user available (set REMOTE_HOST/REMOTE_USER or use profile)"

            ssh_client = create_ssh_client(remote_host, remote_user, port=remote_port, password=remote_password)
            if ssh_client is None:
                return "", "SSH connection failed: could not establish connection"
            created_ssh = True

    # Execute command
    try:
        stdin, stdout, stderr = ssh_client.exec_command(command, timeout=300)  # 5 minute timeout
        output = stdout.read().decode('utf-8', errors='ignore').strip()
        error = stderr.read().decode('utf-8', errors='ignore').strip()
        
        # Close stdin to signal command completion
        stdin.close()
        
    except Exception as e:
        output, error = "", f"Command execution failed: {str(e)}"

    if created_ssh:
        try:
            ssh_client.close()
        except Exception:
            pass

    return output, error

def get_profile_by_id(profile_id: str) -> Optional[Dict]:
    """
    Helper function to get profile by ID.
    
    Args:
        profile_id: Profile ID to lookup
        
    Returns:
        Profile dictionary or None if not found
    """
    try:
        from .session_manager import _get_profile_by_id
        return _get_profile_by_id(profile_id)
    except Exception as e:
        logger.error(f"Failed to get profile {profile_id}: {e}")
        return None
