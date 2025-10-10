"""
Autonomous Healer
Core healing engine that analyzes errors and executes fixes automatically
"""
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Import OpsPilot modules
from ..system_awareness import SystemContextManager
from ..troubleshooting import ask_ai_for_troubleshoot
from ..ssh import create_ssh_client, run_shell


class AutonomousHealer:
    """Autonomous healing engine for pipeline failures"""
    
    def __init__(self, system_context: SystemContextManager = None):
        """
        Initialize the autonomous healer
        
        Args:
            system_context: Optional system context manager for server awareness
        """
        self.system_context = system_context or SystemContextManager()
        self.healing_history = []
        self.safety_checks_enabled = True
        self.max_retry_attempts = 3
    
    def heal_error(self, error_info: Dict, target_hosts: List[str] = None) -> Dict:
        """
        Main healing function - analyzes error and attempts autonomous fix
        
        Args:
            error_info: Error information from ErrorInterceptor
            target_hosts: List of target hosts to apply fixes (optional)
            
        Returns:
            Healing result with success status and actions taken
        """
        healing_session = {
            "session_id": f"heal_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "error_info": error_info,
            "target_hosts": target_hosts or [],
            "actions_taken": [],
            "success": False,
            "retry_count": 0
        }
        
        try:
            # Step 1: Analyze error with AI
            analysis_result = self._analyze_error_with_ai(error_info)
            healing_session["ai_analysis"] = analysis_result
            
            if not analysis_result.get("success"):
                healing_session["failure_reason"] = "AI analysis failed"
                return healing_session
            
            # Step 2: Generate healing plan
            healing_plan = self._generate_healing_plan(analysis_result, error_info)
            healing_session["healing_plan"] = healing_plan
            
            # Step 3: Validate healing plan safety
            if self.safety_checks_enabled:
                safety_result = self._validate_healing_safety(healing_plan, error_info)
                healing_session["safety_validation"] = safety_result
                
                if not safety_result.get("safe", False):
                    healing_session["failure_reason"] = f"Safety check failed: {safety_result.get('reason')}"
                    return healing_session
            
            # Step 4: Execute healing actions
            execution_result = self._execute_healing_plan(healing_plan, target_hosts)
            healing_session["execution_result"] = execution_result
            healing_session["actions_taken"] = execution_result.get("actions", [])
            
            # Step 5: Verify fix
            verification_result = self._verify_fix(healing_plan, target_hosts, error_info)
            healing_session["verification"] = verification_result
            healing_session["success"] = verification_result.get("verified", False)
            
            # Store healing session
            self.healing_history.append(healing_session)
            
            return healing_session
            
        except Exception as e:
            healing_session["failure_reason"] = f"Healing exception: {str(e)}"
            healing_session["success"] = False
            self.healing_history.append(healing_session)
            return healing_session
    
    def _analyze_error_with_ai(self, error_info: Dict) -> Dict:
        """Use AI to analyze the error and generate solutions"""
        try:
            # Prepare error context for AI
            error_context = {
                "error_category": error_info.get("error_category"),
                "severity": error_info.get("severity"),
                "source": error_info.get("source"),
                "raw_error": error_info.get("raw_error"),
                "stderr": error_info.get("stderr", ""),
                "stdout": error_info.get("stdout", ""),
                "task_name": error_info.get("task_name"),
                "module": error_info.get("module")
            }
            
            # Use existing troubleshooting module with system context
            result = ask_ai_for_troubleshoot(
                error_text=error_info.get("raw_error", ""),
                context=error_context,
                system_context=self.system_context
            )
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"AI analysis failed: {str(e)}"
            }
    
    def _generate_healing_plan(self, ai_analysis: Dict, error_info: Dict) -> Dict:
        """Generate a structured healing plan from AI analysis"""
        if not ai_analysis.get("success"):
            return {"valid": False, "reason": "AI analysis failed"}
        
        troubleshoot_response = ai_analysis.get("troubleshoot_response", {})
        
        healing_plan = {
            "valid": True,
            "analysis": troubleshoot_response.get("analysis", ""),
            "diagnostic_commands": troubleshoot_response.get("diagnostic_commands", []),
            "fix_commands": troubleshoot_response.get("fix_commands", []),
            "verification_commands": troubleshoot_response.get("verification_commands", []),
            "risk_level": troubleshoot_response.get("risk_level", "medium"),
            "requires_confirmation": troubleshoot_response.get("requires_confirmation", True),
            "estimated_time": self._estimate_healing_time(troubleshoot_response),
            "rollback_plan": self._generate_rollback_plan(troubleshoot_response)
        }
        
        return healing_plan
    
    def _validate_healing_safety(self, healing_plan: Dict, error_info: Dict) -> Dict:
        """Validate if the healing plan is safe to execute"""
        safety_result = {
            "safe": True,
            "risk_factors": [],
            "warnings": []
        }
        
        # Check risk level
        risk_level = healing_plan.get("risk_level", "medium")
        if risk_level == "high":
            safety_result["risk_factors"].append("High risk operations detected")
            safety_result["safe"] = False
            safety_result["reason"] = "Risk level too high for autonomous execution"
        
        # Check for destructive commands
        fix_commands = healing_plan.get("fix_commands", [])
        destructive_patterns = ["rm -rf", "dd if=", "mkfs", "fdisk", "parted"]
        
        for command in fix_commands:
            if isinstance(command, str):
                for pattern in destructive_patterns:
                    if pattern in command.lower():
                        safety_result["risk_factors"].append(f"Destructive command detected: {pattern}")
                        safety_result["safe"] = False
                        safety_result["reason"] = "Destructive commands not allowed"
        
        # Check if requires confirmation
        if healing_plan.get("requires_confirmation", True):
            safety_result["warnings"].append("Plan requires manual confirmation")
        
        return safety_result
    
    def _execute_healing_plan(self, healing_plan: Dict, target_hosts: List[str]) -> Dict:
        """Execute the healing plan on target hosts"""
        execution_result = {
            "success": True,
            "actions": [],
            "failed_actions": [],
            "host_results": {}
        }
        
        if not target_hosts:
            target_hosts = ["localhost"]  # Default to localhost if no hosts specified
        
        for host in target_hosts:
            host_result = self._execute_on_host(healing_plan, host)
            execution_result["host_results"][host] = host_result
            
            if not host_result.get("success"):
                execution_result["success"] = False
                execution_result["failed_actions"].extend(host_result.get("failed_actions", []))
            else:
                execution_result["actions"].extend(host_result.get("actions", []))
        
        return execution_result
    
    def _execute_on_host(self, healing_plan: Dict, host: str) -> Dict:
        """Execute healing plan on a specific host"""
        host_result = {
            "host": host,
            "success": True,
            "actions": [],
            "failed_actions": []
        }
        
        try:
            # For now, simulate execution - in real implementation, use SSH
            # This will be enhanced when we integrate with the test environment
            
            # Execute diagnostic commands
            for cmd in healing_plan.get("diagnostic_commands", []):
                action = {
                    "type": "diagnostic",
                    "command": cmd,
                    "timestamp": datetime.now().isoformat(),
                    "success": True,  # Simulated
                    "output": f"Simulated execution of: {cmd}"
                }
                host_result["actions"].append(action)
            
            # Execute fix commands
            for cmd in healing_plan.get("fix_commands", []):
                action = {
                    "type": "fix",
                    "command": cmd,
                    "timestamp": datetime.now().isoformat(),
                    "success": True,  # Simulated
                    "output": f"Simulated execution of: {cmd}"
                }
                host_result["actions"].append(action)
            
            return host_result
            
        except Exception as e:
            host_result["success"] = False
            host_result["error"] = str(e)
            return host_result
    
    def _verify_fix(self, healing_plan: Dict, target_hosts: List[str], original_error: Dict) -> Dict:
        """Verify that the fix was successful"""
        verification_result = {
            "verified": True,
            "verification_actions": [],
            "host_verifications": {}
        }
        
        # Execute verification commands
        for host in target_hosts or ["localhost"]:
            host_verification = {
                "host": host,
                "verified": True,
                "checks": []
            }
            
            for cmd in healing_plan.get("verification_commands", []):
                check = {
                    "command": cmd,
                    "timestamp": datetime.now().isoformat(),
                    "success": True,  # Simulated
                    "output": f"Simulated verification: {cmd}"
                }
                host_verification["checks"].append(check)
            
            verification_result["host_verifications"][host] = host_verification
        
        return verification_result
    
    def _estimate_healing_time(self, troubleshoot_response: Dict) -> int:
        """Estimate healing time in seconds"""
        # Simple estimation based on number of commands
        diagnostic_count = len(troubleshoot_response.get("diagnostic_commands", []))
        fix_count = len(troubleshoot_response.get("fix_commands", []))
        verification_count = len(troubleshoot_response.get("verification_commands", []))
        
        # Estimate 5 seconds per command
        return (diagnostic_count + fix_count + verification_count) * 5
    
    def _generate_rollback_plan(self, troubleshoot_response: Dict) -> Dict:
        """Generate rollback plan in case healing fails"""
        return {
            "available": False,  # Will be enhanced later
            "commands": [],
            "notes": "Rollback plan generation not yet implemented"
        }
    
    def get_healing_history(self, limit: int = 10) -> List[Dict]:
        """Get recent healing history"""
        return self.healing_history[-limit:]
    
    def get_success_rate(self) -> float:
        """Calculate healing success rate"""
        if not self.healing_history:
            return 0.0
        
        successful = sum(1 for session in self.healing_history if session.get("success"))
        return successful / len(self.healing_history)
    
    def enable_safety_checks(self, enabled: bool = True):
        """Enable or disable safety checks"""
        self.safety_checks_enabled = enabled
    
    def set_max_retries(self, max_retries: int):
        """Set maximum retry attempts"""
        self.max_retry_attempts = max_retries
