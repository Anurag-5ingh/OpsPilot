"""
SSH Session Manager
Flask blueprint for SSH session management endpoints with connection profiles
"""
import os
import json
import uuid
import logging
from pathlib import Path
from typing import Dict, List, Optional
from flask import Blueprint, request, jsonify
from .secrets import set_secret, get_secret, delete_secret, get_profile_secret_id
from .client import create_ssh_client, connect_with_profile
from .hostkeys import host_key_manager

logger = logging.getLogger(__name__)

ssh_bp = Blueprint("ssh", __name__)

# Profile storage
PROFILES_FILE = Path("ai_shell_agent/data/ssh_profiles.json")
PROFILES_FILE.parent.mkdir(parents=True, exist_ok=True)

def _load_profiles() -> List[Dict]:
    """Load SSH profiles from JSON file."""
    try:
        if PROFILES_FILE.exists():
            with open(PROFILES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load profiles: {e}")
    return []

def _save_profiles(profiles: List[Dict]) -> bool:
    """Save SSH profiles to JSON file."""
    try:
        # Write atomically
        temp_file = PROFILES_FILE.with_suffix('.tmp')
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(profiles, f, indent=2)
        temp_file.replace(PROFILES_FILE)
        return True
    except Exception as e:
        logger.error(f"Failed to save profiles: {e}")
        return False

def _get_profile_by_id(profile_id: str) -> Optional[Dict]:
    """Get profile by ID."""
    profiles = _load_profiles()
    for profile in profiles:
        if profile.get('id') == profile_id:
            return profile
    return None

def _validate_profile_data(data: Dict) -> tuple[bool, str]:
    """Validate profile data. Returns (is_valid, error_message)."""
    required_fields = ['name', 'host', 'username', 'auth_method']
    for field in required_fields:
        if not data.get(field):
            return False, f"{field} is required"
    
    # Validate auth_method
    valid_auth_methods = ['agent', 'key', 'password', 'keyboard-interactive']
    if data['auth_method'] not in valid_auth_methods:
        return False, f"auth_method must be one of: {', '.join(valid_auth_methods)}"
    
    # Validate port
    try:
        port = int(data.get('port', 22))
        if port < 1 or port > 65535:
            return False, "port must be between 1 and 65535"
    except ValueError:
        return False, "port must be a valid integer"
    
    # Validate strict_host_key_checking
    if 'strict_host_key_checking' in data:
        valid_modes = ['ask', 'yes', 'no']
        if data['strict_host_key_checking'] not in valid_modes:
            return False, f"strict_host_key_checking must be one of: {', '.join(valid_modes)}"
    
    return True, ""

@ssh_bp.route("/ssh/list", methods=["GET"])
def list_ssh():
    """List saved SSH connection profiles."""
    try:
        profiles = _load_profiles()
        
        # Remove sensitive data from response
        safe_profiles = []
        for profile in profiles:
            safe_profile = profile.copy()
            # Remove any accidentally stored secrets
            safe_profile.pop('password', None)
            safe_profile.pop('private_key', None)
            safe_profile.pop('passphrase', None)
            safe_profiles.append(safe_profile)
        
        return jsonify(safe_profiles), 200
        
    except Exception as e:
        logger.error(f"Failed to list profiles: {e}")
        return jsonify({"error": "Failed to load profiles"}), 500

@ssh_bp.route("/ssh/save", methods=["POST"])
def save_ssh():
    """Save SSH connection profile."""
    try:
        data = request.get_json() or request.form.to_dict()
        
        # Validate required fields
        is_valid, error_msg = _validate_profile_data(data)
        if not is_valid:
            return jsonify({"error": error_msg}), 400
        
        # Load existing profiles
        profiles = _load_profiles()
        
        # Generate or use existing ID
        profile_id = data.get('id', str(uuid.uuid4()))
        
        # Find existing profile or create new
        existing_index = None
        for i, profile in enumerate(profiles):
            if profile.get('id') == profile_id:
                existing_index = i
                break
        
        # Create profile dict (non-sensitive data only)
        profile = {
            'id': profile_id,
            'name': data['name'],
            'host': data['host'],
            'port': int(data.get('port', 22)),
            'username': data['username'],
            'auth_method': data['auth_method'],
            'key_source': data.get('key_source', 'file'),  # 'file' or 'stored'
            'key_type': data.get('key_type', 'auto'),
            'key_path': data.get('key_path', ''),
            'strict_host_key_checking': data.get('strict_host_key_checking', 'ask'),
            'created_at': data.get('created_at'),
            'updated_at': data.get('updated_at')
        }
        
        # Handle bastion configuration
        if data.get('bastion_enabled') and data.get('bastion_host'):
            profile['bastion'] = {
                'host': data['bastion_host'],
                'port': int(data.get('bastion_port', 22)),
                'username': data['bastion_username'],
                'auth_method': data.get('bastion_auth_method', 'agent')
            }
        
        # Store sensitive data separately
        if data.get('password'):
            secret_id = get_profile_secret_id(profile_id, 'password')
            if not set_secret(secret_id, data['password']):
                return jsonify({"error": "Failed to store password securely"}), 500
            profile['password_secret_id'] = secret_id
        
        if data.get('passphrase'):
            secret_id = get_profile_secret_id(profile_id, 'passphrase')
            if not set_secret(secret_id, data['passphrase']):
                return jsonify({"error": "Failed to store passphrase securely"}), 500
            profile['passphrase_secret_id'] = secret_id
        
        if data.get('private_key_content'):
            secret_id = get_profile_secret_id(profile_id, 'private_key')
            if not set_secret(secret_id, data['private_key_content']):
                return jsonify({"error": "Failed to store private key securely"}), 500
            profile['private_key_secret_id'] = secret_id
        
        # Update or add profile
        if existing_index is not None:
            profiles[existing_index] = profile
        else:
            profiles.append(profile)
        
        # Save to file
        if not _save_profiles(profiles):
            return jsonify({"error": "Failed to save profile"}), 500
        
        return jsonify({
            "message": "Profile saved successfully",
            "id": profile_id,
            "name": profile['name']
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to save profile: {e}")
        return jsonify({"error": "Failed to save profile"}), 500

@ssh_bp.route("/ssh/delete/<profile_id>", methods=["POST", "DELETE"])
def delete_ssh(profile_id):
    """Delete SSH connection profile and associated secrets."""
    try:
        profiles = _load_profiles()
        
        # Find profile to delete
        profile_to_delete = None
        new_profiles = []
        
        for profile in profiles:
            if profile.get('id') == profile_id:
                profile_to_delete = profile
            else:
                new_profiles.append(profile)
        
        if not profile_to_delete:
            return jsonify({"error": "Profile not found"}), 404
        
        # Delete associated secrets
        secret_types = ['password', 'passphrase', 'private_key']
        for secret_type in secret_types:
            secret_id = get_profile_secret_id(profile_id, secret_type)
            delete_secret(secret_id)
        
        # Save updated profiles
        if not _save_profiles(new_profiles):
            return jsonify({"error": "Failed to update profiles"}), 500
        
        return jsonify({
            "message": "Profile deleted successfully",
            "id": profile_id
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to delete profile: {e}")
        return jsonify({"error": "Failed to delete profile"}), 500

@ssh_bp.route("/ssh/test", methods=["POST"])
def test_ssh_connection():
    """Test SSH connection with profile data without saving."""
    try:
        data = request.get_json() or request.form.to_dict()
        
        # Validate required fields
        is_valid, error_msg = _validate_profile_data(data)
        if not is_valid:
            return jsonify({"error": error_msg}), 400
        
        # Create temporary profile for testing
        test_profile = {
            'id': 'test',
            'name': 'Test Connection',
            'host': data['host'],
            'port': int(data.get('port', 22)),
            'username': data['username'],
            'auth_method': data['auth_method'],
            'key_source': data.get('key_source', 'file'),
            'key_type': data.get('key_type', 'auto'),
            'key_path': data.get('key_path', ''),
            'strict_host_key_checking': data.get('strict_host_key_checking', 'no')  # Less strict for testing
        }
        
        # Add sensitive data temporarily (not stored)
        if data.get('password'):
            test_profile['_temp_password'] = data['password']
        if data.get('passphrase'):
            test_profile['_temp_passphrase'] = data['passphrase']
        if data.get('private_key_content'):
            test_profile['_temp_private_key'] = data['private_key_content']
        
        # Handle bastion
        if data.get('bastion_enabled') and data.get('bastion_host'):
            test_profile['bastion'] = {
                'host': data['bastion_host'],
                'port': int(data.get('bastion_port', 22)),
                'username': data['bastion_username'],
                'auth_method': data.get('bastion_auth_method', 'agent')
            }
        
        # Test connection
        def test_host_key_callback(hostname, key_type, fingerprint):
            return True  # Auto-approve for testing
        
        ssh_client = None
        try:
            # Check if enhanced SSH is enabled
            if os.getenv('OSPILOT_SSH_ENHANCED', 'true').lower() == 'true':
                ssh_client = connect_with_profile(
                    test_profile,
                    on_hostkey_decision=test_host_key_callback
                )
            else:
                # Fallback to legacy connection
                password = data.get('password', '')
                ssh_client = create_ssh_client(
                    data['host'], 
                    data['username'], 
                    int(data.get('port', 22)), 
                    password
                )
            
            if ssh_client is None:
                return jsonify({
                    "success": False,
                    "error": "Connection failed",
                    "details": "Unable to establish SSH connection. Check host, username, and authentication credentials."
                }), 200
            
            # Test with a simple command
            stdin, stdout, stderr = ssh_client.exec_command('echo "Connection test successful"', timeout=10)
            output = stdout.read().decode().strip()
            error = stderr.read().decode().strip()
            
            # Check if command execution was successful
            if stderr.channel.recv_exit_status() != 0:
                ssh_client.close()
                return jsonify({
                    "success": False,
                    "error": "Command execution failed",
                    "details": error or "Command failed to execute"
                }), 200
            
            # Get host key information
            host_key_info = None
            try:
                host_key_info = host_key_manager.get_host_key_info(data['host'], int(data.get('port', 22)))
            except Exception as e:
                logger.warning(f"Failed to get host key info: {e}")
            
            ssh_client.close()
            
            return jsonify({
                "success": True,
                "message": "Connection test successful",
                "output": output,
                "host_key_info": host_key_info
            }), 200
            
        except Exception as e:
            if ssh_client:
                try:
                    ssh_client.close()
                except:
                    pass
            
            logger.error(f"SSH test connection failed: {e}")
            return jsonify({
                "success": False,
                "error": "Connection test failed",
                "details": str(e)
            }), 200
        
    except Exception as e:
        logger.error(f"SSH test endpoint error: {e}")
        return jsonify({"error": "Test connection failed"}), 500
