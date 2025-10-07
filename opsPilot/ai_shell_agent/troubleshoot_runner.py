"""
Workflow engine for executing troubleshooting steps.
"""
from ai_shell_agent.shell_runner import run_shell


class TroubleshootWorkflow:
    """Manages multi-step troubleshooting execution."""
    
    def __init__(self, ssh_client):
        self.ssh_client = ssh_client
        self.steps = []
        self.current_step = 0
    
    def execute_commands(self, commands: list, step_type: str) -> dict:
        """Execute a list of commands and return results."""
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
