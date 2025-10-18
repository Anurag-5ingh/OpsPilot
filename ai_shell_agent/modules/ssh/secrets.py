"""
Secure Secret Storage Module

Provides secure storage for SSH-related secrets like private keys, passphrases, and passwords.
Uses OS keyring by default with encrypted file fallback.
"""

import os
import json
import secrets
import logging
from pathlib import Path
from typing import Optional, Dict
from cryptography.fernet import Fernet
import base64

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

logger = logging.getLogger(__name__)

class SecretStorage:
    """
    Handles secure storage and retrieval of sensitive data.
    
    Uses OS keyring (Windows Credential Manager, macOS Keychain, Linux Secret Service)
    as primary storage with encrypted file fallback.
    """
    
    def __init__(self):
        """Initialize secret storage with keyring and file fallback."""
        self.service_name = "OpsPilot-SSH"
        self.data_dir = Path("ai_shell_agent/data")
        self.secrets_file = self.data_dir / "secrets.enc"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize encryption key for file storage
        self._encryption_key = self._get_or_create_master_key()
        self._fernet = Fernet(self._encryption_key)
        
    def _get_or_create_master_key(self) -> bytes:
        """Get or create master encryption key for file storage."""
        # Try to get from environment first
        env_key = os.getenv("OSPILOT_MASTER_KEY")
        if env_key:
            try:
                return base64.urlsafe_b64decode(env_key.encode())
            except Exception as e:
                logger.warning(f"Invalid OSPILOT_MASTER_KEY in environment: {e}")
        
        # Try to get from keyring
        if KEYRING_AVAILABLE:
            try:
                stored_key = keyring.get_password(self.service_name, "master_key")
                if stored_key:
                    return base64.urlsafe_b64decode(stored_key.encode())
            except Exception as e:
                logger.warning(f"Failed to retrieve master key from keyring: {e}")
        
        # Generate new key
        logger.info("Generating new master encryption key")
        new_key = Fernet.generate_key()
        
        # Try to store in keyring
        if KEYRING_AVAILABLE:
            try:
                keyring.set_password(
                    self.service_name, 
                    "master_key", 
                    base64.urlsafe_b64encode(new_key).decode()
                )
                logger.info("Master key stored in OS keyring")
            except Exception as e:
                logger.warning(f"Failed to store master key in keyring: {e}")
                logger.info("Add OSPILOT_MASTER_KEY to your .env file to persist the key")
                print(f"Add this to your .env file:\nOSPILOT_MASTER_KEY={base64.urlsafe_b64encode(new_key).decode()}")
        
        return new_key
    
    def set_secret(self, secret_id: str, value: str) -> bool:
        """
        Store a secret value securely.
        
        Args:
            secret_id: Unique identifier for the secret
            value: Secret value to store
            
        Returns:
            True if successfully stored, False otherwise
        """
        if not secret_id or not value:
            return False
            
        # Never log secret values
        logger.debug(f"Storing secret with ID: {secret_id}")
        
        # Try keyring first
        if KEYRING_AVAILABLE:
            try:
                keyring.set_password(self.service_name, secret_id, value)
                return True
            except Exception as e:
                logger.warning(f"Failed to store secret in keyring: {e}")
        
        # Fallback to encrypted file
        try:
            return self._store_in_encrypted_file(secret_id, value)
        except Exception as e:
            logger.error(f"Failed to store secret in file: {e}")
            return False
    
    def get_secret(self, secret_id: str) -> Optional[str]:
        """
        Retrieve a secret value.
        
        Args:
            secret_id: Unique identifier for the secret
            
        Returns:
            Secret value or None if not found
        """
        if not secret_id:
            return None
            
        logger.debug(f"Retrieving secret with ID: {secret_id}")
        
        # Try keyring first
        if KEYRING_AVAILABLE:
            try:
                value = keyring.get_password(self.service_name, secret_id)
                if value is not None:
                    return value
            except Exception as e:
                logger.warning(f"Failed to retrieve secret from keyring: {e}")
        
        # Fallback to encrypted file
        try:
            return self._retrieve_from_encrypted_file(secret_id)
        except Exception as e:
            logger.warning(f"Failed to retrieve secret from file: {e}")
            return None
    
    def delete_secret(self, secret_id: str) -> bool:
        """
        Delete a secret value.
        
        Args:
            secret_id: Unique identifier for the secret
            
        Returns:
            True if successfully deleted or not found, False on error
        """
        if not secret_id:
            return True
            
        logger.debug(f"Deleting secret with ID: {secret_id}")
        success = True
        
        # Try keyring
        if KEYRING_AVAILABLE:
            try:
                keyring.delete_password(self.service_name, secret_id)
            except keyring.errors.PasswordDeleteError:
                pass  # Secret not found in keyring, that's OK
            except Exception as e:
                logger.warning(f"Failed to delete secret from keyring: {e}")
                success = False
        
        # Try encrypted file
        try:
            self._delete_from_encrypted_file(secret_id)
        except Exception as e:
            logger.warning(f"Failed to delete secret from file: {e}")
            success = False
            
        return success
    
    def _store_in_encrypted_file(self, secret_id: str, value: str) -> bool:
        """Store secret in encrypted JSON file."""
        try:
            # Load existing data
            data = {}
            if self.secrets_file.exists():
                try:
                    encrypted_data = self.secrets_file.read_bytes()
                    decrypted_data = self._fernet.decrypt(encrypted_data)
                    data = json.loads(decrypted_data.decode())
                except Exception as e:
                    logger.warning(f"Failed to read existing secrets file: {e}")
                    # Continue with empty data
            
            # Add new secret
            data[secret_id] = value
            
            # Encrypt and save
            json_data = json.dumps(data, indent=2)
            encrypted_data = self._fernet.encrypt(json_data.encode())
            
            # Write atomically
            temp_file = self.secrets_file.with_suffix('.tmp')
            temp_file.write_bytes(encrypted_data)
            temp_file.replace(self.secrets_file)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store secret in encrypted file: {e}")
            return False
    
    def _retrieve_from_encrypted_file(self, secret_id: str) -> Optional[str]:
        """Retrieve secret from encrypted JSON file."""
        if not self.secrets_file.exists():
            return None
            
        try:
            encrypted_data = self.secrets_file.read_bytes()
            decrypted_data = self._fernet.decrypt(encrypted_data)
            data = json.loads(decrypted_data.decode())
            return data.get(secret_id)
            
        except Exception as e:
            logger.error(f"Failed to retrieve secret from encrypted file: {e}")
            return None
    
    def _delete_from_encrypted_file(self, secret_id: str) -> None:
        """Delete secret from encrypted JSON file."""
        if not self.secrets_file.exists():
            return
            
        try:
            encrypted_data = self.secrets_file.read_bytes()
            decrypted_data = self._fernet.decrypt(encrypted_data)
            data = json.loads(decrypted_data.decode())
            
            if secret_id in data:
                del data[secret_id]
                
                # Save updated data
                if data:
                    json_data = json.dumps(data, indent=2)
                    encrypted_data = self._fernet.encrypt(json_data.encode())
                    temp_file = self.secrets_file.with_suffix('.tmp')
                    temp_file.write_bytes(encrypted_data)
                    temp_file.replace(self.secrets_file)
                else:
                    # Remove empty file
                    self.secrets_file.unlink(missing_ok=True)
                    
        except Exception as e:
            logger.error(f"Failed to delete secret from encrypted file: {e}")


# Global instance
secret_storage = SecretStorage()

def set_secret(secret_id: str, value: str) -> bool:
    """Store a secret value securely."""
    return secret_storage.set_secret(secret_id, value)

def get_secret(secret_id: str) -> Optional[str]:
    """Retrieve a secret value."""
    return secret_storage.get_secret(secret_id)

def delete_secret(secret_id: str) -> bool:
    """Delete a secret value."""
    return secret_storage.delete_secret(secret_id)

def get_profile_secret_id(profile_id: str, secret_type: str) -> str:
    """Generate standardized secret ID for profiles."""
    return f"opspilot/ssh/profile/{profile_id}/{secret_type}"