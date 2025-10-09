#!/usr/bin/env python3
"""
Ansible Callback Plugin for Pipeline Healing
Captures Ansible task failures and triggers healing process
"""
import json
import sys
from pathlib import Path
from ansible.plugins.callback import CallbackBase

# Add OpsPilot modules to path
opspilot_path = Path(__file__).parent.parent.parent / "opsPilot"
sys.path.insert(0, str(opspilot_path))

try:
    from ai_shell_agent.modules.pipeline_healing import ErrorInterceptor, AutonomousHealer
    from ai_shell_agent.modules.system_awareness import SystemContextManager
    OPSPILOT_AVAILABLE = True
except ImportError:
    OPSPILOT_AVAILABLE = False
    print("Warning: OpsPilot modules not available. Running in simulation mode.")


class CallbackModule(CallbackBase):
    """
    Ansible callback plugin that intercepts failures and triggers healing
    """
    
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'notification'
    CALLBACK_NAME = 'pipeline_healing'
    CALLBACK_NEEDS_WHITELIST = True
    
    def __init__(self):
        """Initialize the callback plugin"""
        super(CallbackModule, self).__init__()
        
        self.healing_enabled = True
        self.auto_heal = False  # Set to True for autonomous healing
        self.failed_tasks = []
        
        if OPSPILOT_AVAILABLE:
            self.error_interceptor = ErrorInterceptor()
            self.system_context = SystemContextManager()
            self.autonomous_healer = AutonomousHealer(self.system_context)
            # Disable safety checks for testing
            self.autonomous_healer.enable_safety_checks(False)
        else:
            self.error_interceptor = None
            self.autonomous_healer = None
    
    def v2_runner_on_failed(self, result, ignore_errors=False):
        """Called when a task fails"""
        if not self.healing_enabled:
            return
        
        # Extract failure information
        task_data = {
            "task": {
                "name": result._task.get_name(),
                "action": result._task.action
            },
            "host": result._host.get_name(),
            "msg": result._result.get('msg', ''),
            "failed": result._result.get('failed', True),
            "stderr": result._result.get('stderr', ''),
            "stdout": result._result.get('stdout', ''),
            "module_args": result._task.args,
            "exception": result._result.get('exception', ''),
            "unreachable": False,
            "changed": result._result.get('changed', False)
        }
        
        self._display.display(f"\n🚨 TASK FAILURE DETECTED: {task_data['task']['name']}")
        self._display.display(f"   Host: {task_data['host']}")
        self._display.display(f"   Error: {task_data['msg']}")
        
        # Store failed task
        self.failed_tasks.append(task_data)
        
        if OPSPILOT_AVAILABLE and self.error_interceptor:
            # Intercept and analyze error
            error_info = self.error_interceptor.capture_ansible_error(task_data)
            
            self._display.display(f"   Category: {error_info['error_category']}")
            self._display.display(f"   Severity: {error_info['severity']}")
            
            # Trigger healing if auto-heal is enabled
            if self.auto_heal and self.autonomous_healer:
                self._display.display(f"\n🏥 TRIGGERING AUTONOMOUS HEALING...")
                healing_result = self.autonomous_healer.heal_error(
                    error_info=error_info,
                    target_hosts=[task_data['host']]
                )
                
                if healing_result['success']:
                    self._display.display(f"✅ HEALING SUCCESSFUL: {healing_result['session_id']}")
                    self._display.display(f"   Actions: {len(healing_result.get('actions_taken', []))}")
                else:
                    self._display.display(f"❌ HEALING FAILED: {healing_result.get('failure_reason', 'Unknown')}")
            else:
                self._display.display(f"   Suggested Actions: {error_info['suggested_actions']}")
        else:
            self._display.display("   OpsPilot healing not available - running in simulation mode")
    
    def v2_runner_on_unreachable(self, result):
        """Called when a host is unreachable"""
        if not self.healing_enabled:
            return
        
        task_data = {
            "task": {
                "name": result._task.get_name(),
                "action": result._task.action
            },
            "host": result._host.get_name(),
            "msg": result._result.get('msg', 'Host unreachable'),
            "failed": True,
            "unreachable": True,
            "changed": False
        }
        
        self._display.display(f"\n🔌 HOST UNREACHABLE: {task_data['host']}")
        self._display.display(f"   Task: {task_data['task']['name']}")
        
        self.failed_tasks.append(task_data)
        
        if OPSPILOT_AVAILABLE and self.error_interceptor:
            error_info = self.error_interceptor.capture_ansible_error(task_data)
            self._display.display(f"   Category: {error_info['error_category']}")
    
    def v2_playbook_on_stats(self, stats):
        """Called when playbook execution is complete"""
        if not self.failed_tasks:
            self._display.display(f"\n✅ PLAYBOOK COMPLETED SUCCESSFULLY - No healing required")
            return
        
        self._display.display(f"\n📊 PLAYBOOK HEALING SUMMARY")
        self._display.display(f"   Failed Tasks: {len(self.failed_tasks)}")
        
        if OPSPILOT_AVAILABLE and self.autonomous_healer:
            success_rate = self.autonomous_healer.get_success_rate()
            healing_history = self.autonomous_healer.get_healing_history()
            self._display.display(f"   Healing Attempts: {len(healing_history)}")
            self._display.display(f"   Healing Success Rate: {success_rate:.1%}")
        
        # Offer manual healing for failed tasks
        if not self.auto_heal and self.failed_tasks:
            self._display.display(f"\n💡 MANUAL HEALING AVAILABLE:")
            self._display.display(f"   Run: python healing-agent/manual_healing.py")
    
    def enable_healing(self, enabled=True):
        """Enable or disable healing functionality"""
        self.healing_enabled = enabled
    
    def enable_auto_heal(self, enabled=True):
        """Enable or disable automatic healing"""
        self.auto_heal = enabled
        if enabled:
            self._display.display(f"🤖 AUTONOMOUS HEALING ENABLED")
        else:
            self._display.display(f"👤 MANUAL HEALING MODE")


# Standalone test function
def test_callback():
    """Test the callback plugin functionality"""
    print("🧪 Testing Ansible Callback Plugin")
    
    # Create mock result objects for testing
    class MockTask:
        def __init__(self, name, action, args):
            self.name = name
            self.action = action
            self.args = args
        
        def get_name(self):
            return self.name
    
    class MockHost:
        def __init__(self, name):
            self.name = name
        
        def get_name(self):
            return self.name
    
    class MockResult:
        def __init__(self, task, host, result_data):
            self._task = task
            self._host = host
            self._result = result_data
    
    # Initialize callback
    callback = CallbackModule()
    callback.enable_auto_heal(True)  # Enable auto-healing for test
    
    # Test package failure
    task = MockTask("Install web server", "package", {"name": "httpd", "state": "present"})
    host = MockHost("ubuntu-server")
    result_data = {
        "msg": "No package matching 'httpd' is available",
        "failed": True,
        "stderr": "E: Unable to locate package httpd"
    }
    
    result = MockResult(task, host, result_data)
    callback.v2_runner_on_failed(result)
    
    print(f"\n✅ Callback test completed")
    print(f"   Failed tasks captured: {len(callback.failed_tasks)}")


if __name__ == "__main__":
    test_callback()
