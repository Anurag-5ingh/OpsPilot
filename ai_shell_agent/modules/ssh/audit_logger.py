"""
SSH Audit Logger

Simple audit logging for SSH connection attempts and security events.
"""

import json
import time
import logging
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class SSHAuditLogger:
    """
    Simple audit logger for SSH connection attempts and security events.
    """
    
    def __init__(self, log_dir: str = "ai_shell_agent/logs"):
        """
        Initialize audit logger.
        
        Args:
            log_dir: Directory to store audit logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.audit_file = self.log_dir / "audit.log"
        
    def log_connection_attempt(self,
                             profile_id: Optional[str] = None,
                             host: str = "",
                             username: str = "",
                             auth_method: str = "unknown",
                             result: str = "unknown",
                             error_summary: str = "",
                             hostkey_fingerprint: str = "",
                             **kwargs):
        """
        Log SSH connection attempt.
        
        Args:
            profile_id: Profile ID used (or "legacy" for direct connections)
            host: Target hostname/IP
            username: SSH username
            auth_method: Authentication method used
            result: "success" or "failure"
            error_summary: Brief error description (no sensitive data)
            hostkey_fingerprint: Host key fingerprint if relevant
            **kwargs: Additional context data
        """
        try:
            # Create audit log entry
            entry = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "event_type": "ssh_connection_attempt",
                "profile_id": profile_id or "legacy",
                "host": host,
                "username": username,
                "auth_method": auth_method,
                "result": result,
                "error_summary": error_summary[:500],  # Limit error length
                "hostkey_fingerprint": hostkey_fingerprint
            }
            
            # Add any additional context
            for key, value in kwargs.items():
                if not key.startswith('_') and key not in entry:
                    # Exclude internal/sensitive fields
                    entry[key] = str(value)[:200] if isinstance(value, str) else value
            
            # Write to log file
            self._write_audit_entry(entry)
            
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
    
    def log_host_key_event(self,
                          host: str,
                          key_type: str,
                          fingerprint: str,
                          action: str,
                          profile_id: Optional[str] = None):
        """
        Log host key verification events.
        
        Args:
            host: Target hostname
            key_type: Key algorithm type
            fingerprint: Key fingerprint
            action: "accepted", "rejected", "auto_added"
            profile_id: Associated profile ID if any
        """
        try:
            entry = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "event_type": "host_key_verification",
                "host": host,
                "key_type": key_type,
                "fingerprint": fingerprint,
                "action": action,
                "profile_id": profile_id or "legacy"
            }
            
            self._write_audit_entry(entry)
            
        except Exception as e:
            logger.error(f"Failed to write host key audit log: {e}")
    
    def log_auth_event(self,
                      host: str,
                      username: str,
                      auth_method: str,
                      event: str,
                      details: str = "",
                      profile_id: Optional[str] = None):
        """
        Log authentication events.
        
        Args:
            host: Target hostname
            username: SSH username
            auth_method: Authentication method
            event: "attempt", "success", "failure", "mfa_prompt"
            details: Additional context
            profile_id: Associated profile ID if any
        """
        try:
            entry = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "event_type": "ssh_authentication",
                "host": host,
                "username": username,
                "auth_method": auth_method,
                "event": event,
                "details": details[:300],  # Limit details length
                "profile_id": profile_id or "legacy"
            }
            
            self._write_audit_entry(entry)
            
        except Exception as e:
            logger.error(f"Failed to write auth audit log: {e}")
    
    def _write_audit_entry(self, entry: Dict[str, Any]):
        """Write audit entry to log file."""
        try:
            # Convert to JSON and append to file
            json_line = json.dumps(entry, separators=(',', ':'))
            
            with open(self.audit_file, 'a', encoding='utf-8') as f:
                f.write(json_line + '\n')
                
        except Exception as e:
            logger.error(f"Failed to write audit entry to file: {e}")
    
    def get_recent_events(self, limit: int = 100) -> list:
        """
        Get recent audit events.
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            List of recent audit events
        """
        try:
            if not self.audit_file.exists():
                return []
            
            events = []
            with open(self.audit_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # Get last N lines
            recent_lines = lines[-limit:] if len(lines) > limit else lines
            
            for line in recent_lines:
                line = line.strip()
                if line:
                    try:
                        event = json.loads(line)
                        events.append(event)
                    except json.JSONDecodeError:
                        continue
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to read audit events: {e}")
            return []

# Global instance
audit_logger = SSHAuditLogger()

def log_connection_attempt(*args, **kwargs):
    """Log SSH connection attempt."""
    return audit_logger.log_connection_attempt(*args, **kwargs)

def log_host_key_event(*args, **kwargs):
    """Log host key verification event."""
    return audit_logger.log_host_key_event(*args, **kwargs)

def log_auth_event(*args, **kwargs):
    """Log authentication event."""
    return audit_logger.log_auth_event(*args, **kwargs)