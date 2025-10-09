#!/usr/bin/env python3
"""
Test Healing Integration
Tests the integration between Ansible failures and OpsPilot healing system
"""
import sys
import os
import json
from pathlib import Path

# Add OpsPilot modules to path
opspilot_path = Path(__file__).parent.parent.parent / "opsPilot"
sys.path.insert(0, str(opspilot_path))

from ai_shell_agent.modules.pipeline_healing import ErrorInterceptor, AutonomousHealer
from ai_shell_agent.modules.system_awareness import SystemContextManager


class AnsibleHealingTest:
    """Test class for Ansible healing integration"""
    
    def __init__(self):
        """Initialize the test environment"""
        self.error_interceptor = ErrorInterceptor()
        self.system_context = SystemContextManager()
        self.autonomous_healer = AutonomousHealer(self.system_context)
        
        # Disable safety checks for testing
        self.autonomous_healer.enable_safety_checks(False)
    
    def simulate_ansible_failure(self, scenario: str) -> dict:
        """Simulate different Ansible failure scenarios"""
        scenarios = {
            "package_failure": {
                "task": {"name": "Install web server", "action": "package"},
                "host": "ubuntu-server",
                "msg": "No package matching 'httpd' is available",
                "failed": True,
                "stderr": "E: Unable to locate package httpd",
                "stdout": "",
                "module_args": {"name": "httpd", "state": "present"}
            },
            "service_failure": {
                "task": {"name": "Start web service", "action": "service"},
                "host": "centos-server", 
                "msg": "Could not find the requested service fake-service: host",
                "failed": True,
                "stderr": "Failed to start fake-service.service: Unit fake-service.service not found.",
                "stdout": "",
                "module_args": {"name": "fake-service", "state": "started"}
            },
            "permission_failure": {
                "task": {"name": "Create config file", "action": "file"},
                "host": "alpine-server",
                "msg": "Permission denied",
                "failed": True,
                "stderr": "chmod: /etc/test-file: Operation not permitted",
                "stdout": "",
                "module_args": {"path": "/etc/test-file", "state": "touch"}
            }
        }
        
        return scenarios.get(scenario, scenarios["package_failure"])
    
    def test_error_interception(self, scenario: str):
        """Test error interception and analysis"""
        print(f"\n🧪 Testing Error Interception - Scenario: {scenario}")
        print("=" * 60)
        
        # Simulate Ansible failure
        ansible_result = self.simulate_ansible_failure(scenario)
        print(f"📥 Simulated Ansible Result:")
        print(json.dumps(ansible_result, indent=2))
        
        # Intercept and analyze error
        error_info = self.error_interceptor.capture_ansible_error(ansible_result)
        print(f"\n🔍 Error Analysis:")
        print(f"  Category: {error_info['error_category']}")
        print(f"  Severity: {error_info['severity']}")
        print(f"  Suggested Actions: {error_info['suggested_actions']}")
        
        return error_info
    
    def test_autonomous_healing(self, error_info: dict):
        """Test autonomous healing process"""
        print(f"\n🏥 Testing Autonomous Healing")
        print("=" * 60)
        
        # Attempt healing
        healing_result = self.autonomous_healer.heal_error(
            error_info=error_info,
            target_hosts=[error_info.get("host", "localhost")]
        )
        
        print(f"🔧 Healing Session ID: {healing_result['session_id']}")
        print(f"✅ Success: {healing_result['success']}")
        
        if healing_result.get("ai_analysis", {}).get("success"):
            analysis = healing_result["ai_analysis"]["troubleshoot_response"]
            print(f"\n🧠 AI Analysis:")
            print(f"  Analysis: {analysis.get('analysis', 'N/A')}")
            print(f"  Risk Level: {analysis.get('risk_level', 'N/A')}")
            print(f"  Fix Commands: {len(analysis.get('fix_commands', []))}")
        
        if healing_result.get("actions_taken"):
            print(f"\n⚡ Actions Taken: {len(healing_result['actions_taken'])}")
            for action in healing_result["actions_taken"][:3]:  # Show first 3
                print(f"  - {action.get('type', 'unknown')}: {action.get('command', 'N/A')}")
        
        if not healing_result["success"]:
            print(f"❌ Failure Reason: {healing_result.get('failure_reason', 'Unknown')}")
        
        return healing_result
    
    def test_full_healing_workflow(self, scenario: str):
        """Test the complete healing workflow"""
        print(f"\n🚀 Full Healing Workflow Test - Scenario: {scenario}")
        print("=" * 80)
        
        # Step 1: Error Interception
        error_info = self.test_error_interception(scenario)
        
        # Step 2: Autonomous Healing
        healing_result = self.test_autonomous_healing(error_info)
        
        # Step 3: Summary
        print(f"\n📊 Workflow Summary:")
        print(f"  Error Category: {error_info['error_category']}")
        print(f"  Healing Success: {healing_result['success']}")
        print(f"  Actions Taken: {len(healing_result.get('actions_taken', []))}")
        
        return {
            "error_info": error_info,
            "healing_result": healing_result
        }
    
    def run_all_tests(self):
        """Run all test scenarios"""
        print("🎯 OpsPilot Ansible Healing Integration Tests")
        print("=" * 80)
        
        scenarios = ["package_failure", "service_failure", "permission_failure"]
        results = {}
        
        for scenario in scenarios:
            try:
                result = self.test_full_healing_workflow(scenario)
                results[scenario] = result
            except Exception as e:
                print(f"❌ Test failed for {scenario}: {str(e)}")
                results[scenario] = {"error": str(e)}
        
        # Overall summary
        print(f"\n🏁 Test Summary:")
        print("=" * 80)
        successful_healings = 0
        total_tests = len(scenarios)
        
        for scenario, result in results.items():
            if "error" in result:
                print(f"  {scenario}: ❌ Test Error")
            else:
                healing_success = result["healing_result"]["success"]
                status = "✅ Healed" if healing_success else "⚠️ Failed to Heal"
                print(f"  {scenario}: {status}")
                if healing_success:
                    successful_healings += 1
        
        success_rate = (successful_healings / total_tests) * 100
        print(f"\n📈 Healing Success Rate: {success_rate:.1f}% ({successful_healings}/{total_tests})")
        
        return results


def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test OpsPilot Ansible Healing Integration")
    parser.add_argument("--scenario", choices=["package_failure", "service_failure", "permission_failure", "all"], 
                       default="all", help="Test scenario to run")
    
    args = parser.parse_args()
    
    # Initialize test
    test = AnsibleHealingTest()
    
    if args.scenario == "all":
        test.run_all_tests()
    else:
        test.test_full_healing_workflow(args.scenario)


if __name__ == "__main__":
    main()
