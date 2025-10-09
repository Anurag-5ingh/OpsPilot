"""
Error Interceptor
Captures and analyzes pipeline failures from various sources
"""
import json
import re
from typing import Dict, List, Optional
from datetime import datetime


class ErrorInterceptor:
    """Intercepts and analyzes errors from pipeline executions"""
    
    def __init__(self):
        """Initialize the error interceptor"""
        self.error_patterns = self._load_error_patterns()
        self.captured_errors = []
    
    def capture_ansible_error(self, ansible_result: Dict) -> Dict:
        """
        Capture and analyze Ansible task failure
        
        Args:
            ansible_result: Ansible task result dictionary
            
        Returns:
            Structured error information
        """
        error_info = {
            "timestamp": datetime.now().isoformat(),
            "source": "ansible",
            "task_name": ansible_result.get("task", {}).get("name", "Unknown Task"),
            "host": ansible_result.get("host", "Unknown Host"),
            "module": ansible_result.get("task", {}).get("action", "Unknown Module"),
            "raw_error": ansible_result.get("msg", ""),
            "failed": ansible_result.get("failed", False),
            "unreachable": ansible_result.get("unreachable", False),
            "changed": ansible_result.get("changed", False)
        }
        
        # Extract additional context
        if "exception" in ansible_result:
            error_info["exception"] = ansible_result["exception"]
        
        if "stderr" in ansible_result:
            error_info["stderr"] = ansible_result["stderr"]
        
        if "stdout" in ansible_result:
            error_info["stdout"] = ansible_result["stdout"]
        
        # Analyze error type
        error_info["error_category"] = self._categorize_error(error_info)
        error_info["severity"] = self._assess_severity(error_info)
        error_info["suggested_actions"] = self._suggest_initial_actions(error_info)
        
        # Store for analysis
        self.captured_errors.append(error_info)
        
        return error_info
    
    def capture_jenkins_error(self, jenkins_data: Dict) -> Dict:
        """
        Capture Jenkins pipeline failure
        
        Args:
            jenkins_data: Jenkins webhook/API data
            
        Returns:
            Structured error information
        """
        error_info = {
            "timestamp": datetime.now().isoformat(),
            "source": "jenkins",
            "job_name": jenkins_data.get("job_name", "Unknown Job"),
            "build_number": jenkins_data.get("build_number", 0),
            "stage": jenkins_data.get("stage", "Unknown Stage"),
            "raw_error": jenkins_data.get("error_message", ""),
            "console_output": jenkins_data.get("console_output", ""),
            "build_url": jenkins_data.get("build_url", "")
        }
        
        # Analyze error
        error_info["error_category"] = self._categorize_error(error_info)
        error_info["severity"] = self._assess_severity(error_info)
        error_info["suggested_actions"] = self._suggest_initial_actions(error_info)
        
        self.captured_errors.append(error_info)
        return error_info
    
    def _categorize_error(self, error_info: Dict) -> str:
        """Categorize the error type based on patterns"""
        raw_error = error_info.get("raw_error", "").lower()
        stderr = error_info.get("stderr", "").lower()
        
        # Package management errors
        if any(pattern in raw_error for pattern in ["package", "apt", "yum", "dnf", "repository"]):
            return "package_management"
        
        # Service management errors
        if any(pattern in raw_error for pattern in ["service", "systemctl", "daemon", "failed to start"]):
            return "service_management"
        
        # Permission errors
        if any(pattern in raw_error for pattern in ["permission denied", "access denied", "unauthorized"]):
            return "permissions"
        
        # Network errors
        if any(pattern in raw_error for pattern in ["connection", "network", "timeout", "unreachable"]):
            return "network"
        
        # File system errors
        if any(pattern in raw_error for pattern in ["file not found", "directory", "disk space", "mount"]):
            return "filesystem"
        
        # Configuration errors
        if any(pattern in raw_error for pattern in ["config", "syntax error", "invalid"]):
            return "configuration"
        
        return "unknown"
    
    def _assess_severity(self, error_info: Dict) -> str:
        """Assess error severity"""
        error_category = error_info.get("error_category", "unknown")
        
        # High severity errors
        if error_category in ["network", "permissions", "filesystem"]:
            return "high"
        
        # Medium severity errors
        if error_category in ["service_management", "configuration"]:
            return "medium"
        
        # Low severity errors
        if error_category in ["package_management"]:
            return "low"
        
        return "medium"  # Default
    
    def _suggest_initial_actions(self, error_info: Dict) -> List[str]:
        """Suggest initial remediation actions"""
        category = error_info.get("error_category", "unknown")
        suggestions = []
        
        if category == "package_management":
            suggestions = [
                "Update package repositories",
                "Check package name for current OS",
                "Verify package availability",
                "Check for dependency conflicts"
            ]
        elif category == "service_management":
            suggestions = [
                "Check service status",
                "Verify service configuration",
                "Check for port conflicts",
                "Review service logs"
            ]
        elif category == "permissions":
            suggestions = [
                "Check file/directory permissions",
                "Verify user/group ownership",
                "Check sudo/root access",
                "Review SELinux/AppArmor policies"
            ]
        elif category == "network":
            suggestions = [
                "Check network connectivity",
                "Verify DNS resolution",
                "Check firewall rules",
                "Test port accessibility"
            ]
        elif category == "filesystem":
            suggestions = [
                "Check disk space",
                "Verify file/directory existence",
                "Check mount points",
                "Review file permissions"
            ]
        
        return suggestions
    
    def _load_error_patterns(self) -> Dict:
        """Load error pattern definitions"""
        return {
            "package_not_found": [
                r"package .* not found",
                r"no package .* available",
                r"unable to locate package"
            ],
            "service_failed": [
                r"failed to start .*",
                r"service .* failed",
                r"unit .* failed"
            ],
            "permission_denied": [
                r"permission denied",
                r"access denied",
                r"operation not permitted"
            ],
            "connection_failed": [
                r"connection refused",
                r"connection timed out",
                r"host unreachable"
            ]
        }
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict]:
        """Get recent captured errors"""
        return self.captured_errors[-limit:]
    
    def clear_errors(self):
        """Clear captured error history"""
        self.captured_errors.clear()
    
    def export_errors(self, format: str = "json") -> str:
        """Export captured errors in specified format"""
        if format == "json":
            return json.dumps(self.captured_errors, indent=2)
        elif format == "summary":
            summary = []
            for error in self.captured_errors:
                summary.append(f"{error['timestamp']} - {error['source']} - {error['error_category']} - {error['severity']}")
            return "\n".join(summary)
        else:
            return str(self.captured_errors)
