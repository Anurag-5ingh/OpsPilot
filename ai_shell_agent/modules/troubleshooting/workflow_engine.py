"""
Workflow Engine for Troubleshooting Module
Executes multi-step troubleshooting workflows
"""


class TroubleshootWorkflow:
    """Manages multi-step troubleshooting execution."""
    
    def __init__(self, ssh_client):
        """
        Initialize workflow engine with SSH client.
        
        Args:
            ssh_client: Paramiko SSH client for command execution
        """
        self.ssh_client = ssh_client
        self.steps = []
        self.current_step = 0
    
    def execute_commands(self, commands: list, step_type: str) -> dict:
        """
        Execute a list of commands and return results.
        
        Args:
            commands: List of shell commands to execute
            step_type: Type of step (diagnostic, fix, verification)
            
        Returns:
            dict with step_type, results, and all_success flag
        """
        # Import here to avoid circular dependency
        from ai_shell_agent.modules.ssh.client import run_shell
        
        results = []
        
        for cmd in commands:
            output, error = run_shell(cmd, ssh_client=self.ssh_client)
            results.append({
                "command": cmd,
                "output": output,
                "error": error,
                "success": not error
            })
        
        return {
            "step_type": step_type,
            "results": results,
            "all_success": all(r["success"] for r in results)
        }
    
    def run_diagnostics(self, commands: list) -> dict:
        """Run diagnostic commands."""
        return self.execute_commands(commands, "diagnostic")
    
    def run_fixes(self, commands: list) -> dict:
        """Run fix commands."""
        return self.execute_commands(commands, "fix")
    
    def run_verification(self, commands: list) -> dict:
        """Run verification commands."""
        return self.execute_commands(commands, "verification")
