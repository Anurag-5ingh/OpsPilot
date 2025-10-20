"""
Ansible Integration Service

Handles Ansible playbook management, Git repository synchronization,
and mapping between Jenkins jobs and Ansible playbooks.
"""

import os
import subprocess
import logging
import shutil
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import yaml
import re
import git
from git.exc import GitCommandError, InvalidGitRepositoryError

from .models import AnsibleConfig
from ..ssh.secrets import get_secret

logger = logging.getLogger(__name__)


class AnsibleService:
    """Service for managing Ansible configurations and playbooks."""
    
    def __init__(self, config: AnsibleConfig):
        self.config = config
        self.local_path = Path(config.local_path) if config.local_path else None
        self.git_repo_url = config.git_repo_url
        self.git_branch = config.git_branch or 'main'
        
        # Ensure local path exists
        if self.local_path:
            self.local_path.mkdir(parents=True, exist_ok=True)
    
    def test_configuration(self) -> Dict[str, Any]:
        """Test Ansible configuration and paths."""
        logger.info(f"Testing Ansible configuration - Path: {self.local_path}, Git: {self.git_repo_url}")
        result = {
            'success': True,
            'checks': {},
            'warnings': [],
            'errors': []
        }
        
        try:
            # Check if Ansible is installed
            logger.debug("Checking if Ansible is installed")
            try:
                version_result = subprocess.run(
                    ['ansible', '--version'], 
                    capture_output=True, text=True, timeout=10
                )
                if version_result.returncode == 0:
                    version_line = version_result.stdout.split('\n')[0]
                    result['checks']['ansible_version'] = version_line
                    logger.info(f"Ansible found: {version_line}")
                else:
                    error_msg = 'Ansible command not found'
                    result['errors'].append(error_msg)
                    result['success'] = False
                    logger.error(f"Ansible check failed: {error_msg}")
            except subprocess.TimeoutExpired:
                error_msg = 'Ansible version check timed out'
                result['errors'].append(error_msg)
                result['success'] = False
                logger.error(f"Ansible check failed: {error_msg}")
            except FileNotFoundError:
                error_msg = 'Ansible is not installed or not in PATH'
                result['errors'].append(error_msg)
                result['success'] = False
                logger.error(f"Ansible check failed: {error_msg}")
            
            # Check local path
            if self.local_path:
                if self.local_path.exists():
                    result['checks']['local_path_exists'] = True
                    
                    # Count playbook files
                    playbook_files = list(self.local_path.glob('**/*.yml')) + \
                                   list(self.local_path.glob('**/*.yaml'))
                    result['checks']['playbook_count'] = len(playbook_files)
                    
                    # Check for inventory files
                    inventory_files = []
                    for pattern in ['inventory', 'hosts', '*.ini', '*.yml', '*.yaml']:
                        inventory_files.extend(self.local_path.glob(pattern))
                        inventory_files.extend(self.local_path.glob(f'**/inventory/{pattern}'))
                    
                    result['checks']['inventory_files'] = len(inventory_files)
                    
                    if len(playbook_files) == 0:
                        result['warnings'].append('No playbook files found in local path')
                else:
                    result['errors'].append(f'Local path does not exist: {self.local_path}')
                    result['success'] = False
            
            # Check Git repository if configured
            if self.git_repo_url:
                git_status = self._check_git_repository()
                result['checks']['git_repository'] = git_status
                
                if not git_status['accessible']:
                    result['warnings'].append(f'Git repository not accessible: {git_status.get("error")}')
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to test Ansible configuration: {e}")
            result['success'] = False
            result['errors'].append(f'Configuration test failed: {str(e)}')
            return result
    
    def _check_git_repository(self) -> Dict[str, Any]:
        """Check if Git repository is accessible."""
        try:
            # Try to clone to a temporary directory to test access
            import tempfile
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # Just check if we can access the repository info
                result = subprocess.run([
                    'git', 'ls-remote', '--heads', self.git_repo_url
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    # Count remote branches
                    branches = result.stdout.strip().split('\n') if result.stdout.strip() else []
                    return {
                        'accessible': True,
                        'remote_branches': len(branches),
                        'target_branch_exists': any(self.git_branch in branch for branch in branches)
                    }
                else:
                    return {
                        'accessible': False,
                        'error': result.stderr.strip() or 'Repository not accessible'
                    }
                    
        except Exception as e:
            return {
                'accessible': False,
                'error': str(e)
            }
    
    def sync_from_git(self, force: bool = False) -> Dict[str, Any]:
        """Synchronize local Ansible files from Git repository."""
        logger.info(f"Starting Git sync - Repo: {self.git_repo_url}, Branch: {self.git_branch}, Force: {force}")
        
        if not self.git_repo_url:
            error_msg = 'No Git repository configured'
            logger.error(f"Git sync failed: {error_msg}")
            return {
                'success': False,
                'error': error_msg
            }
        
        if not self.local_path:
            error_msg = 'No local path configured'
            logger.error(f"Git sync failed: {error_msg}")
            return {
                'success': False,
                'error': error_msg
            }
        
        try:
            # Check if local path is already a git repository
            repo = None
            is_existing_repo = False
            
            try:
                repo = git.Repo(self.local_path)
                is_existing_repo = True
                logger.info(f"Found existing Git repository at {self.local_path}")
            except InvalidGitRepositoryError:
                # Not a git repository, need to clone
                is_existing_repo = False
            
            if is_existing_repo and repo:
                # Pull latest changes
                try:
                    origin = repo.remote('origin')
                    
                    # Fetch latest changes
                    origin.fetch()
                    
                    # Check if we need to switch branches
                    current_branch = repo.active_branch.name
                    if current_branch != self.git_branch:
                        # Switch to target branch
                        if self.git_branch in [branch.name for branch in repo.branches]:
                            repo.git.checkout(self.git_branch)
                        else:
                            # Create and track remote branch
                            repo.git.checkout('-b', self.git_branch, f'origin/{self.git_branch}')
                    
                    # Pull latest changes
                    if force:
                        repo.git.reset('--hard', f'origin/{self.git_branch}')
                    else:
                        origin.pull(self.git_branch)
                    
                    # Get commit info
                    latest_commit = repo.head.commit
                    
                    result = {
                        'success': True,
                        'action': 'pulled',
                        'commit_hash': latest_commit.hexsha[:8],
                        'commit_message': latest_commit.message.strip(),
                        'commit_date': datetime.fromtimestamp(latest_commit.committed_date, tz=timezone.utc),
                        'branch': self.git_branch
                    }
                    
                except Exception as e:
                    logger.error(f"Failed to pull from Git repository: {e}")
                    return {
                        'success': False,
                        'error': f'Git pull failed: {str(e)}'
                    }
            else:
                # Clone repository
                try:
                    # Remove existing directory if it exists and is not a git repo
                    if self.local_path.exists():
                        if force:
                            shutil.rmtree(self.local_path)
                        else:
                            # Check if directory is empty
                            if any(self.local_path.iterdir()):
                                return {
                                    'success': False,
                                    'error': f'Local path {self.local_path} exists and is not empty. Use force=True to overwrite.'
                                }
                    
                    # Clone the repository
                    repo = git.Repo.clone_from(
                        self.git_repo_url, 
                        self.local_path, 
                        branch=self.git_branch
                    )
                    
                    latest_commit = repo.head.commit
                    
                    result = {
                        'success': True,
                        'action': 'cloned',
                        'commit_hash': latest_commit.hexsha[:8],
                        'commit_message': latest_commit.message.strip(),
                        'commit_date': datetime.fromtimestamp(latest_commit.committed_date, tz=timezone.utc),
                        'branch': self.git_branch
                    }
                    
                except Exception as e:
                    logger.error(f"Failed to clone Git repository: {e}")
                    return {
                        'success': False,
                        'error': f'Git clone failed: {str(e)}'
                    }
            
            # Update last sync timestamp
            self.config.last_synced = datetime.now(timezone.utc)
            self.config.save()
            
            logger.info(f"Successfully synced Ansible repository: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to sync from Git: {e}")
            return {
                'success': False,
                'error': f'Git sync failed: {str(e)}'
            }
    
    def get_playbooks(self) -> List[Dict[str, Any]]:
        """Get list of available Ansible playbooks."""
        if not self.local_path or not self.local_path.exists():
            return []
        
        playbooks = []
        
        try:
            # Find all YAML files that could be playbooks
            yaml_files = []
            for pattern in ['*.yml', '*.yaml']:
                yaml_files.extend(self.local_path.glob(f'**/{pattern}'))
            
            for yaml_file in yaml_files:
                try:
                    # Skip files in certain directories
                    relative_path = yaml_file.relative_to(self.local_path)
                    if any(part.startswith('.') for part in relative_path.parts):
                        continue
                    
                    # Read and parse YAML to check if it's a playbook
                    with open(yaml_file, 'r', encoding='utf-8') as f:
                        content = yaml.safe_load(f)
                    
                    # Check if this looks like a playbook (has hosts and tasks)
                    if isinstance(content, list) and len(content) > 0:
                        first_play = content[0]
                        if isinstance(first_play, dict) and 'hosts' in first_play:
                            # Extract playbook information
                            playbook_info = {
                                'name': yaml_file.stem,
                                'path': str(relative_path),
                                'full_path': str(yaml_file),
                                'hosts': first_play.get('hosts', ''),
                                'description': first_play.get('name', ''),
                                'tags': self._extract_tags_from_playbook(content),
                                'size': yaml_file.stat().st_size,
                                'modified': datetime.fromtimestamp(yaml_file.stat().st_mtime, tz=timezone.utc)
                            }
                            playbooks.append(playbook_info)
                            
                except Exception as e:
                    logger.debug(f"Could not parse {yaml_file}: {e}")
                    continue
            
            # Sort by name
            playbooks.sort(key=lambda x: x['name'])
            return playbooks
            
        except Exception as e:
            logger.error(f"Failed to get playbooks: {e}")
            return []
    
    def _extract_tags_from_playbook(self, content: List[Dict]) -> List[str]:
        """Extract tags from playbook content."""
        tags = set()
        
        try:
            for play in content:
                if isinstance(play, dict):
                    # Play-level tags
                    if 'tags' in play:
                        play_tags = play['tags']
                        if isinstance(play_tags, list):
                            tags.update(play_tags)
                        elif isinstance(play_tags, str):
                            tags.add(play_tags)
                    
                    # Task-level tags
                    tasks = play.get('tasks', [])
                    for task in tasks:
                        if isinstance(task, dict) and 'tags' in task:
                            task_tags = task['tags']
                            if isinstance(task_tags, list):
                                tags.update(task_tags)
                            elif isinstance(task_tags, str):
                                tags.add(task_tags)
        except Exception as e:
            logger.debug(f"Could not extract tags: {e}")
        
        return sorted(list(tags))
    
    def get_inventory_files(self) -> List[Dict[str, Any]]:
        """Get list of available inventory files."""
        if not self.local_path or not self.local_path.exists():
            return []
        
        inventories = []
        
        try:
            # Common inventory file patterns
            inventory_patterns = [
                'inventory',
                'hosts',
                'inventory.*',
                '*/inventory',
                '*/hosts'
            ]
            
            found_files = []
            for pattern in inventory_patterns:
                found_files.extend(self.local_path.glob(pattern))
            
            for inventory_file in found_files:
                if inventory_file.is_file():
                    relative_path = inventory_file.relative_to(self.local_path)
                    
                    inventory_info = {
                        'name': inventory_file.name,
                        'path': str(relative_path),
                        'full_path': str(inventory_file),
                        'type': self._detect_inventory_type(inventory_file),
                        'size': inventory_file.stat().st_size,
                        'modified': datetime.fromtimestamp(inventory_file.stat().st_mtime, tz=timezone.utc)
                    }
                    inventories.append(inventory_info)
            
            # Sort by name
            inventories.sort(key=lambda x: x['name'])
            return inventories
            
        except Exception as e:
            logger.error(f"Failed to get inventory files: {e}")
            return []
    
    def _detect_inventory_type(self, file_path: Path) -> str:
        """Detect inventory file type (ini, yaml, json)."""
        try:
            suffix = file_path.suffix.lower()
            if suffix in ['.yml', '.yaml']:
                return 'yaml'
            elif suffix in ['.json']:
                return 'json'
            elif suffix in ['.ini']:
                return 'ini'
            else:
                # Try to detect from content
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read(100)  # First 100 chars
                    
                if content.strip().startswith('['):
                    return 'ini'
                elif content.strip().startswith('{'):
                    return 'json'
                else:
                    return 'text'
        except Exception:
            return 'unknown'
    
    def find_playbook_for_jenkins_job(self, job_name: str, console_log: str = "") -> Optional[Dict[str, Any]]:
        """Find the most likely playbook for a Jenkins job."""
        playbooks = self.get_playbooks()
        
        if not playbooks:
            return None
        
        job_name_lower = job_name.lower()
        console_log_lower = console_log.lower()
        
        # Score each playbook
        scored_playbooks = []
        
        for playbook in playbooks:
            score = 0
            playbook_name_lower = playbook['name'].lower()
            
            # Direct name matching
            if playbook_name_lower in job_name_lower:
                score += 10
            elif job_name_lower in playbook_name_lower:
                score += 8
            
            # Partial name matching (word-based)
            job_words = re.findall(r'\w+', job_name_lower)
            playbook_words = re.findall(r'\w+', playbook_name_lower)
            
            common_words = set(job_words) & set(playbook_words)
            score += len(common_words) * 3
            
            # Console log matching
            if console_log:
                if playbook['name'] in console_log_lower:
                    score += 5
                if f"ansible-playbook {playbook['path']}" in console_log_lower:
                    score += 15
                if f"ansible-playbook {playbook['name']}" in console_log_lower:
                    score += 12
            
            # Path-based matching
            path_parts = Path(playbook['path']).parts
            for part in path_parts:
                if part.lower() in job_name_lower:
                    score += 2
            
            if score > 0:
                scored_playbooks.append((score, playbook))
        
        # Return the highest scoring playbook
        if scored_playbooks:
            scored_playbooks.sort(key=lambda x: x[0], reverse=True)
            return scored_playbooks[0][1]
        
        return None
    
    def validate_playbook_syntax(self, playbook_path: str) -> Dict[str, Any]:
        """Validate Ansible playbook syntax."""
        if not self.local_path:
            return {
                'valid': False,
                'error': 'No local path configured'
            }
        
        full_path = self.local_path / playbook_path
        if not full_path.exists():
            return {
                'valid': False,
                'error': f'Playbook not found: {playbook_path}'
            }
        
        try:
            # Use ansible-playbook --syntax-check
            result = subprocess.run([
                'ansible-playbook', 
                '--syntax-check', 
                str(full_path)
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return {
                    'valid': True,
                    'message': 'Playbook syntax is valid'
                }
            else:
                return {
                    'valid': False,
                    'error': result.stderr.strip() or result.stdout.strip()
                }
                
        except subprocess.TimeoutExpired:
            return {
                'valid': False,
                'error': 'Syntax check timed out'
            }
        except Exception as e:
            return {
                'valid': False,
                'error': f'Syntax check failed: {str(e)}'
            }
    
    def suggest_fix_playbook(self, error_summary: str, target_server: str) -> Optional[Dict[str, Any]]:
        """Suggest a playbook that might fix the given error."""
        playbooks = self.get_playbooks()
        
        if not playbooks:
            return None
        
        error_lower = error_summary.lower()
        
        # Keywords that might indicate what kind of fix is needed
        error_keywords = {
            'service': ['service', 'systemd', 'daemon', 'start', 'stop', 'restart'],
            'package': ['package', 'install', 'yum', 'apt', 'dependency'],
            'file': ['file', 'directory', 'permission', 'chmod', 'chown'],
            'network': ['network', 'connection', 'port', 'firewall'],
            'disk': ['disk', 'space', 'mount', 'filesystem'],
            'database': ['database', 'db', 'mysql', 'postgres', 'mongodb'],
            'web': ['apache', 'nginx', 'web', 'http', 'ssl']
        }
        
        # Score playbooks based on error content
        scored_playbooks = []
        
        for playbook in playbooks:
            score = 0
            playbook_name_lower = playbook['name'].lower()
            playbook_path_lower = playbook['path'].lower()
            
            # Check for category matches
            for category, keywords in error_keywords.items():
                category_matches = sum(1 for kw in keywords if kw in error_lower)
                playbook_category_matches = sum(1 for kw in keywords if kw in playbook_name_lower or kw in playbook_path_lower)
                
                if category_matches > 0 and playbook_category_matches > 0:
                    score += category_matches * playbook_category_matches * 5
            
            # Direct keyword matching
            error_words = re.findall(r'\w+', error_lower)
            playbook_words = re.findall(r'\w+', playbook_name_lower)
            
            common_words = set(error_words) & set(playbook_words)
            score += len(common_words) * 2
            
            # Server-specific matching
            if target_server and target_server.lower() in playbook_name_lower:
                score += 3
            
            # Tags matching
            for tag in playbook.get('tags', []):
                if tag.lower() in error_lower:
                    score += 4
            
            if score > 0:
                scored_playbooks.append((score, playbook))
        
        # Return the highest scoring playbook
        if scored_playbooks:
            scored_playbooks.sort(key=lambda x: x[0], reverse=True)
            return scored_playbooks[0][1]
        
        return None


def create_ansible_service(config_id: int) -> Optional[AnsibleService]:
    """Create an Ansible service instance from a stored configuration."""
    try:
        config = AnsibleConfig.get_by_id(config_id)
        if config:
            return AnsibleService(config)
        else:
            logger.error(f"Ansible config {config_id} not found")
            return None
    except Exception as e:
        logger.error(f"Failed to create Ansible service: {e}")
        return None