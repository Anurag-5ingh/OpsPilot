"""
SSH Host Key Verification and Management

Handles host key verification, known_hosts management, and provides secure
host key policies to replace paramiko's AutoAddPolicy.
"""

import os
import hashlib
import base64
import logging
from pathlib import Path
from typing import Dict, List, Optional, Callable, Tuple
import paramiko
from paramiko.hostkeys import HostKeys
from paramiko.pkey import PKey

logger = logging.getLogger(__name__)

class HostKeyVerificationError(Exception):
    """Raised when host key verification fails."""
    pass

class HostKeyPolicy(paramiko.MissingHostKeyPolicy):
    """
    Custom host key policy that handles verification and user interaction.
    
    Replaces paramiko's AutoAddPolicy with secure verification that prompts
    the user for unknown host keys.
    """
    
    def __init__(self, 
                 strict_mode: str = "ask",
                 on_unknown_host: Optional[Callable] = None,
                 known_hosts_path: Optional[str] = None):
        """
        Initialize host key policy.
        
        Args:
            strict_mode: "ask" (default), "yes" (enforce), or "no" (auto-add)
            on_unknown_host: Callback for unknown host keys (host, key_type, fingerprint) -> bool
            known_hosts_path: Path to known_hosts file
        """
        self.strict_mode = strict_mode
        self.on_unknown_host = on_unknown_host
        self.known_hosts_path = known_hosts_path or self._get_default_known_hosts_path()
        self.host_keys = HostKeys()
        self._load_known_hosts()
    
    def _get_default_known_hosts_path(self) -> str:
        """Get default known_hosts file path."""
        # Use application known_hosts
        app_path = Path("ai_shell_agent/data/known_hosts")
        app_path.parent.mkdir(parents=True, exist_ok=True)
        return str(app_path)
    
    def _load_known_hosts(self):
        """Load known host keys from files."""
        try:
            # Load application known_hosts
            if os.path.exists(self.known_hosts_path):
                self.host_keys.load(self.known_hosts_path)
                logger.debug(f"Loaded {len(self.host_keys)} host keys from {self.known_hosts_path}")
            
            # Also load user's known_hosts for convenience
            user_known_hosts = os.path.expanduser("~/.ssh/known_hosts")
            if os.path.exists(user_known_hosts):
                try:
                    self.host_keys.load(user_known_hosts)
                    logger.debug(f"Also loaded user known_hosts from {user_known_hosts}")
                except Exception as e:
                    logger.warning(f"Failed to load user known_hosts: {e}")
                    
        except Exception as e:
            logger.warning(f"Failed to load known_hosts: {e}")
    
    def missing_host_key(self, client: paramiko.SSHClient, hostname: str, key: PKey):
        """
        Handle missing host key verification.
        
        Args:
            client: SSH client instance
            hostname: Remote hostname
            key: Host's public key
        """
        key_type = key.get_name()
        fingerprint = self._get_key_fingerprint(key)
        
        logger.info(f"Unknown host key for {hostname}: {key_type} {fingerprint}")
        
        # Handle based on strict mode
        if self.strict_mode == "no":
            # Auto-add (least secure)
            logger.info(f"Auto-adding host key for {hostname} (strict_mode=no)")
            self._add_host_key(hostname, key)
            return
        
        elif self.strict_mode == "yes":
            # Enforce strict checking - reject unknown keys
            logger.error(f"Rejecting unknown host key for {hostname} (strict_mode=yes)")
            raise HostKeyVerificationError(
                f"Host key verification failed for {hostname}. "
                f"Unknown {key_type} key with fingerprint {fingerprint}"
            )
        
        else:  # strict_mode == "ask" (default)
            # Ask user for verification
            if self.on_unknown_host:
                try:
                    approved = self.on_unknown_host(hostname, key_type, fingerprint)
                    if approved:
                        logger.info(f"User approved host key for {hostname}")
                        self._add_host_key(hostname, key)
                        return
                    else:
                        logger.info(f"User rejected host key for {hostname}")
                        raise HostKeyVerificationError(
                            f"Host key verification rejected by user for {hostname}"
                        )
                except Exception as e:
                    logger.error(f"Error in host key callback: {e}")
                    raise HostKeyVerificationError(
                        f"Host key verification failed for {hostname}: {e}"
                    )
            else:
                # No callback available - reject for security
                logger.error(f"No callback available for unknown host key: {hostname}")
                raise HostKeyVerificationError(
                    f"Host key verification failed for {hostname}. "
                    f"Unknown {key_type} key with fingerprint {fingerprint}. "
                    f"Use strict_host_key_checking=no to auto-add (not recommended)."
                )
    
    def _get_key_fingerprint(self, key: PKey) -> str:
        """Get SHA256 fingerprint of host key."""
        key_bytes = key.asbytes()
        digest = hashlib.sha256(key_bytes).digest()
        return "SHA256:" + base64.b64encode(digest).decode().rstrip('=')
    
    def _add_host_key(self, hostname: str, key: PKey):
        """Add host key to known_hosts file."""
        try:
            # Add to in-memory host keys
            self.host_keys.add(hostname, key.get_name(), key)
            
            # Append to known_hosts file
            with open(self.known_hosts_path, 'a', encoding='utf-8') as f:
                key_line = f"{hostname} {key.get_name()} {key.get_base64()}\n"
                f.write(key_line)
                
            logger.info(f"Added host key for {hostname} to {self.known_hosts_path}")
            
        except Exception as e:
            logger.error(f"Failed to save host key for {hostname}: {e}")
            raise HostKeyVerificationError(f"Failed to save host key: {e}")

class HostKeyManager:
    """
    Manages host keys and provides utilities for verification.
    """
    
    def __init__(self, known_hosts_path: Optional[str] = None):
        """
        Initialize host key manager.
        
        Args:
            known_hosts_path: Path to known_hosts file
        """
        self.known_hosts_path = known_hosts_path or self._get_default_known_hosts_path()
        Path(self.known_hosts_path).parent.mkdir(parents=True, exist_ok=True)
    
    def _get_default_known_hosts_path(self) -> str:
        """Get default known_hosts file path."""
        return str(Path("ai_shell_agent/data/known_hosts"))
    
    def create_policy(self, 
                     strict_mode: str = "ask",
                     on_unknown_host: Optional[Callable] = None) -> HostKeyPolicy:
        """
        Create a host key policy.
        
        Args:
            strict_mode: "ask", "yes", or "no"
            on_unknown_host: Callback for unknown hosts
            
        Returns:
            HostKeyPolicy instance
        """
        return HostKeyPolicy(
            strict_mode=strict_mode,
            on_unknown_host=on_unknown_host,
            known_hosts_path=self.known_hosts_path
        )
    
    def get_host_key_info(self, hostname: str, port: int = 22) -> Optional[Dict]:
        """
        Get information about a host's key if known.
        
        Args:
            hostname: Remote hostname
            port: Remote port
            
        Returns:
            Dict with key info or None if unknown
        """
        try:
            host_keys = HostKeys()
            if os.path.exists(self.known_hosts_path):
                host_keys.load(self.known_hosts_path)
            
            # Try different hostname formats
            for host_format in [hostname, f"[{hostname}]:{port}", f"{hostname}:{port}"]:
                keys = host_keys.get(host_format, {})
                if keys:
                    key_info = []
                    for key_type, key in keys.items():
                        fingerprint = self._get_key_fingerprint(key)
                        key_info.append({
                            "type": key_type,
                            "fingerprint": fingerprint,
                            "base64": key.get_base64()
                        })
                    return {
                        "hostname": host_format,
                        "keys": key_info
                    }
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to get host key info for {hostname}: {e}")
            return None
    
    def _get_key_fingerprint(self, key: PKey) -> str:
        """Get SHA256 fingerprint of host key."""
        key_bytes = key.asbytes()
        digest = hashlib.sha256(key_bytes).digest()
        return "SHA256:" + base64.b64encode(digest).decode().rstrip('=')
    
    def verify_host_key(self, hostname: str, key_type: str, key_data: str) -> bool:
        """
        Verify a host key against known_hosts.
        
        Args:
            hostname: Remote hostname
            key_type: Key type (ssh-rsa, ssh-ed25519, etc.)
            key_data: Base64 encoded key data
            
        Returns:
            True if key is known and matches, False otherwise
        """
        try:
            host_keys = HostKeys()
            if os.path.exists(self.known_hosts_path):
                host_keys.load(self.known_hosts_path)
            
            # Check various hostname formats
            for host_format in [hostname, f"[{hostname}]:22", f"{hostname}:22"]:
                known_keys = host_keys.get(host_format, {})
                if key_type in known_keys:
                    known_key = known_keys[key_type]
                    return known_key.get_base64() == key_data
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to verify host key for {hostname}: {e}")
            return False
    
    def remove_host_key(self, hostname: str) -> bool:
        """
        Remove host key(s) for a hostname.
        
        Args:
            hostname: Remote hostname
            
        Returns:
            True if removed successfully, False otherwise
        """
        try:
            if not os.path.exists(self.known_hosts_path):
                return True
                
            # Read all lines
            with open(self.known_hosts_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Filter out lines for this hostname
            filtered_lines = []
            removed_count = 0
            
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split()
                    if len(parts) >= 3:
                        host_part = parts[0]
                        # Check if this line is for the target hostname
                        if (host_part == hostname or 
                            host_part == f"[{hostname}]:22" or 
                            host_part == f"{hostname}:22"):
                            removed_count += 1
                            continue
                
                filtered_lines.append(line + '\n')
            
            # Write back filtered content
            if removed_count > 0:
                with open(self.known_hosts_path, 'w', encoding='utf-8') as f:
                    f.writelines(filtered_lines)
                logger.info(f"Removed {removed_count} host keys for {hostname}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove host key for {hostname}: {e}")
            return False

# Global instance
host_key_manager = HostKeyManager()