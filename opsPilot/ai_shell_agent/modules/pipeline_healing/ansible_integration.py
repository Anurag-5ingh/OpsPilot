"""
Ansible Integration
Specialized integration for Ansible pipeline healing
"""
import json
import subprocess
import tempfile
from typing import Dict, List, Optional
from pathlib import Path
from .error_interceptor import ErrorInterceptor
from .autonomous_healer import AutonomousHealer


class AnsibleIntegration:
    """Specialized Ansible integration for pipeline healing"""
    
    def __init__(self, error_interceptor: ErrorInterceptor = None, healer: AutonomousHealer = None):
        """
        Initialize Ansible integration
        
        Args:
            error_interceptor: Error interceptor instance
            healer: Autonomous healer instance
        """
        self.error_interceptor = error_interceptor or ErrorInterceptor()
        self.healer = healer
        self.callback_plugin_path = None
        self.healing_enabled = True
        self.auto_retry_enabled = False
        self.max_retries = 3
    
    def setup_callback_plugin(self, callback_plugin_path: str = None):
        """
        Setup Ansible callback plugin for failure interception
        
        Args:
            callback_plugin_path: Path to callback plugin directory
        """
        if callback_plugin_path:
            self.callback_plugin_path = callback_plugin_path
        else:
            # Use default callback plugin from test environment
            test_path = Path(__file__).parent.parent.parent.parent.parent / "ansible-healing-test"
            self.callback_plugin_path = str(test_path / "healing-agent")
    
    def run_playbook_with_healing(self, playbook_path: str, inventory: str = None, 
                                 extra_vars: Dict = None, tags: List[str] = None) -> Dict:
        """
        Run Ansible playbook with healing capabilities
        
        Args:
            playbook_path: Path to Ansible playbook
            inventory: Inventory file or string
            extra_vars: Extra variables for playbook
            tags: Tags to run
            
        Returns:
            Execution result with healing information
        """
        execution_result = {
            "playbook": playbook_path,
            "success": False,
            "attempts": 0,
            "healing_sessions": [],
            "final_output": "",
            "final_error": ""
        }
        
        attempt = 0
        while attempt < self.max_retries:
            attempt += 1
            execution_result["attempts"] = attempt
            
            print(f"🎭 Running Ansible playbook (attempt {attempt}/{self.max_retries})")
            
            # Run playbook
            run_result = self._execute_playbook(
                playbook_path, inventory, extra_vars, tags
            )
            
            execution_result["final_output"] = run_result["stdout"]
            execution_result["final_error"] = run_result["stderr"]
            
            if run_result["success"]:
                execution_result["success"] = True
                print(f"✅ Playbook completed successfully on attempt {attempt}")
                break
            
            print(f"❌ Playbook failed on attempt {attempt}")
            
            # If healing is enabled and we have more retries, attempt healing
            if self.healing_enabled and self.healer and attempt < self.max_retries:
                healing_result = self._attempt_healing_from_output(
                    run_result["stdout"], run_result["stderr"]
                )
                
                if healing_result:
                    execution_result["healing_sessions"].append(healing_result)
                    
                    if healing_result.get("success"):
                        print(f"🏥 Healing successful, retrying playbook...")
                        continue
                    else:
                        print(f"❌ Healing failed: {healing_result.get('failure_reason')}")
            
            # If auto-retry is disabled or this is the last attempt, break
            if not self.auto_retry_enabled or attempt >= self.max_retries:
                break
        
        return execution_result
    
    def _execute_playbook(self, playbook_path: str, inventory: str = None,
                         extra_vars: Dict = None, tags: List[str] = None) -> Dict:
        """Execute Ansible playbook"""
        cmd = ["ansible-playbook", playbook_path]
        
        # Add inventory
        if inventory:
            cmd.extend(["-i", inventory])
        
        # Add extra vars
        if extra_vars:
            cmd.extend(["--extra-vars", json.dumps(extra_vars)])
        
        # Add tags
        if tags:
            cmd.extend(["--tags", ",".join(tags)])
        
        # Add callback plugin if available
        if self.callback_plugin_path:
            cmd.extend(["--callback-plugins", self.callback_plugin_path])
        
        # Add verbose output
        cmd.append("-v")
        
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300
            )
            
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": " ".join(cmd)
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": "Playbook execution timed out",
                "command": " ".join(cmd)
            }
        except Exception as e:
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": f"Execution error: {str(e)}",
                "command": " ".join(cmd)
            }
    
    def _attempt_healing_from_output(self, stdout: str, stderr: str) -> Optional[Dict]:
        """Attempt healing based on playbook output"""
        try:
            # Parse Ansible output to extract failure information
            failures = self._parse_ansible_failures(stdout, stderr)
            
            if not failures:
                print("⚠️ No parseable failures found in output")
                return None
            
            # Take the first failure for healing
            failure = failures[0]
            
            # Convert to error info format
            error_info = self._convert_failure_to_error_info(failure)
            
            # Attempt healing
            healing_result = self.healer.heal_error(
                error_info=error_info,
                target_hosts=[failure.get("host", "localhost")]
            )
            
            return healing_result
            
        except Exception as e:
            print(f"❌ Healing attempt failed: {e}")
            return None
    
    def _parse_ansible_failures(self, stdout: str, stderr: str) -> List[Dict]:
        """Parse Ansible output to extract failure information"""
        failures = []
        
        # Look for FAILED patterns in stdout
        lines = stdout.split('\n')
        current_failure = None
        
        for line in lines:
            line = line.strip()
            
            # Look for task failure indicators
            if "FAILED!" in line or "fatal:" in line:
                # Extract host and task info
                if "=>" in line:
                    parts = line.split("=>")
                    if len(parts) >= 2:
                        host_part = parts[0].strip()
                        # Extract host name
                        if "[" in host_part and "]" in host_part:
                            host = host_part.split("[")[1].split("]")[0]
                        else:
                            host = "unknown"
                        
                        current_failure = {
                            "host": host,
                            "line": line,
                            "details": []
                        }
            
            # Look for error details
            elif current_failure and ("msg:" in line or "stderr:" in line or "stdout:" in line):
                current_failure["details"].append(line)
            
            # End of failure block
            elif current_failure and line.startswith("PLAY") or line.startswith("TASK"):
                if current_failure["details"]:
                    failures.append(current_failure)
                current_failure = None
        
        # Add final failure if exists
        if current_failure and current_failure["details"]:
            failures.append(current_failure)
        
        return failures
    
    def _convert_failure_to_error_info(self, failure: Dict) -> Dict:
        """Convert parsed failure to error info format"""
        # Extract error message from details
        error_msg = ""
        stderr_content = ""
        stdout_content = ""
        
        for detail in failure.get("details", []):
            if "msg:" in detail:
                error_msg = detail.split("msg:", 1)[1].strip().strip('"')
            elif "stderr:" in detail:
                stderr_content = detail.split("stderr:", 1)[1].strip().strip('"')
            elif "stdout:" in detail:
                stdout_content = detail.split("stdout:", 1)[1].strip().strip('"')
        
        if not error_msg and stderr_content:
            error_msg = stderr_content
        
        error_info = {
            "timestamp": "",  # Will be set by error interceptor
            "source": "ansible",
            "task_name": "Unknown Task",
            "host": failure.get("host", "unknown"),
            "module": "unknown",
            "raw_error": error_msg,
            "stderr": stderr_content,
            "stdout": stdout_content,
            "failed": True,
            "unreachable": False,
            "changed": False
        }
        
        return error_info
    
    def create_healing_playbook(self, healing_commands: List[str], target_hosts: List[str]) -> str:
        """
        Create a temporary playbook for healing commands
        
        Args:
            healing_commands: List of commands to execute
            target_hosts: Target hosts for healing
            
        Returns:
            Path to created playbook
        """
        playbook_content = {
            "name": "OpsPilot Autonomous Healing",
            "hosts": ",".join(target_hosts) if target_hosts else "all",
            "become": True,
            "gather_facts": False,
            "tasks": []
        }
        
        for i, command in enumerate(healing_commands):
            task = {
                "name": f"Healing Command {i+1}",
                "shell": command,
                "register": f"healing_result_{i}",
                "failed_when": False
            }
            playbook_content["tasks"].append(task)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write("---\n")
            f.write("- ")
            json.dump(playbook_content, f, indent=2)
            return f.name
    
    def enable_healing(self, enabled: bool = True):
        """Enable or disable healing"""
        self.healing_enabled = enabled
    
    def enable_auto_retry(self, enabled: bool = True, max_retries: int = 3):
        """Enable or disable auto-retry with healing"""
        self.auto_retry_enabled = enabled
        self.max_retries = max_retries
    
    def get_integration_stats(self) -> Dict:
        """Get integration statistics"""
        stats = {
            "healing_enabled": self.healing_enabled,
            "auto_retry_enabled": self.auto_retry_enabled,
            "max_retries": self.max_retries,
            "callback_plugin_path": self.callback_plugin_path
        }
        
        if self.healer:
            stats["healing_success_rate"] = self.healer.get_success_rate()
            stats["healing_history_count"] = len(self.healer.get_healing_history())
        
        return stats
