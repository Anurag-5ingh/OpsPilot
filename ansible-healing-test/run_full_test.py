#!/usr/bin/env python3
"""
Full Pipeline Healing Test
Demonstrates end-to-end pipeline healing workflow
"""
import sys
import time
import subprocess
import requests
from pathlib import Path

# Add OpsPilot to path
opspilot_path = Path(__file__).parent.parent / "opsPilot"
sys.path.insert(0, str(opspilot_path))


class FullPipelineTest:
    """Complete pipeline healing test workflow"""
    
    def __init__(self):
        """Initialize test environment"""
        self.opspilot_url = "http://localhost:8080"
        self.jenkins_simulator_path = Path(__file__).parent / "mock-pipeline" / "jenkins_simulator.py"
        self.healing_test_path = Path(__file__).parent / "healing-agent" / "test_healing_integration.py"
    
    def check_opspilot_running(self) -> bool:
        """Check if OpsPilot is running"""
        try:
            response = requests.get(f"{self.opspilot_url}/pipeline/status", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def test_pipeline_healing_workflow(self):
        """Test complete pipeline healing workflow"""
        print("🚀 Full Pipeline Healing Test")
        print("=" * 80)
        
        # Step 1: Check OpsPilot
        print("\n📡 Step 1: Checking OpsPilot availability...")
        if not self.check_opspilot_running():
            print("❌ OpsPilot not running. Please start with: python app.py")
            return False
        print("✅ OpsPilot is running")
        
        # Step 2: Test healing integration
        print("\n🧪 Step 2: Testing healing integration...")
        self.run_healing_integration_test()
        
        # Step 3: Test Jenkins pipeline simulation
        print("\n🏭 Step 3: Testing Jenkins pipeline simulation...")
        self.run_jenkins_simulation_test()
        
        # Step 4: Test webhook integration
        print("\n📡 Step 4: Testing webhook integration...")
        self.test_webhook_integration()
        
        # Step 5: Show final results
        print("\n📊 Step 5: Final results...")
        self.show_final_results()
        
        return True
    
    def run_healing_integration_test(self):
        """Run healing integration test"""
        try:
            result = subprocess.run([
                sys.executable, str(self.healing_test_path), "--scenario", "package_failure"
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print("✅ Healing integration test passed")
            else:
                print("⚠️ Healing integration test had issues")
                print(f"   Output: {result.stdout[-200:]}")  # Last 200 chars
                
        except subprocess.TimeoutExpired:
            print("⚠️ Healing integration test timed out")
        except Exception as e:
            print(f"❌ Healing integration test failed: {e}")
    
    def run_jenkins_simulation_test(self):
        """Run Jenkins pipeline simulation"""
        scenarios = [
            "ansible_package_failure",
            "ansible_service_failure",
            "docker_build_failure"
        ]
        
        for scenario in scenarios:
            print(f"   Testing scenario: {scenario}")
            try:
                result = subprocess.run([
                    sys.executable, str(self.jenkins_simulator_path),
                    "--job", f"test-job-{scenario}",
                    "--failure", scenario,
                    "--webhook-url", f"{self.opspilot_url}/pipeline/webhook"
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    print(f"   ✅ {scenario} simulation completed")
                else:
                    print(f"   ⚠️ {scenario} simulation had issues")
                    
            except Exception as e:
                print(f"   ❌ {scenario} simulation failed: {e}")
            
            time.sleep(2)  # Brief pause between scenarios
    
    def test_webhook_integration(self):
        """Test direct webhook integration"""
        test_webhooks = [
            {
                "name": "Package Failure",
                "payload": {
                    "source": "jenkins",
                    "job_name": "web-deployment",
                    "build_number": 42,
                    "stage": "Deploy",
                    "error_message": "No package matching 'httpd' is available",
                    "target_hosts": ["web-server-01"],
                    "error_type": "ansible_failure"
                }
            },
            {
                "name": "Service Failure", 
                "payload": {
                    "source": "ansible",
                    "task_name": "Start nginx service",
                    "host": "web-server-02",
                    "raw_error": "Could not find the requested service nginx",
                    "error_category": "service_management"
                }
            }
        ]
        
        for webhook in test_webhooks:
            print(f"   Testing: {webhook['name']}")
            try:
                response = requests.post(
                    f"{self.opspilot_url}/pipeline/webhook",
                    json=webhook["payload"],
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("success"):
                        healing_result = result.get("healing_result")
                        if healing_result and healing_result.get("success"):
                            print(f"   ✅ {webhook['name']} - Webhook processed and healed")
                        else:
                            print(f"   ⚠️ {webhook['name']} - Webhook processed, healing failed")
                    else:
                        print(f"   ❌ {webhook['name']} - Webhook processing failed")
                else:
                    print(f"   ❌ {webhook['name']} - HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ {webhook['name']} - Error: {e}")
            
            time.sleep(1)
    
    def show_final_results(self):
        """Show final test results"""
        try:
            # Get pipeline status
            response = requests.get(f"{self.opspilot_url}/pipeline/status", timeout=10)
            if response.status_code == 200:
                status = response.json()
                print("📊 Pipeline Healing Status:")
                healing_stats = status.get("pipeline_healing", {})
                print(f"   Total Failures Captured: {healing_stats.get('total_failures', 0)}")
                print(f"   Healing Success Rate: {healing_stats.get('healing_success_rate', 0):.1%}")
            
            # Get healing history
            response = requests.get(f"{self.opspilot_url}/pipeline/healing/history?limit=5", timeout=10)
            if response.status_code == 200:
                history = response.json()
                print(f"\n🏥 Recent Healing Sessions: {history.get('total_sessions', 0)}")
                for session in history.get("healing_history", [])[:3]:
                    success = "✅" if session.get("success") else "❌"
                    print(f"   {success} {session.get('session_id', 'unknown')}")
            
            # Test manual healing trigger
            print(f"\n🧪 Testing manual healing trigger...")
            response = requests.post(f"{self.opspilot_url}/pipeline/test/trigger", json={
                "error_type": "package_failure",
                "host": "test-server",
                "error_message": "Test package installation failed"
            }, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("test_triggered") and result.get("healing_result", {}).get("success"):
                    print("   ✅ Manual healing trigger successful")
                else:
                    print("   ⚠️ Manual healing trigger completed but healing failed")
            else:
                print("   ❌ Manual healing trigger failed")
                
        except Exception as e:
            print(f"❌ Error getting final results: {e}")
    
    def run_interactive_demo(self):
        """Run interactive demonstration"""
        print("🎮 Interactive Pipeline Healing Demo")
        print("=" * 50)
        
        while True:
            print("\nSelect test to run:")
            print("1. Full workflow test")
            print("2. Healing integration only")
            print("3. Jenkins simulation only")
            print("4. Webhook test only")
            print("5. Manual healing trigger")
            print("6. Show current status")
            print("7. Exit")
            
            choice = input("\nEnter choice (1-7): ").strip()
            
            if choice == "1":
                self.test_pipeline_healing_workflow()
            elif choice == "2":
                self.run_healing_integration_test()
            elif choice == "3":
                self.run_jenkins_simulation_test()
            elif choice == "4":
                self.test_webhook_integration()
            elif choice == "5":
                self.test_manual_trigger()
            elif choice == "6":
                self.show_current_status()
            elif choice == "7":
                print("👋 Goodbye!")
                break
            else:
                print("Invalid choice. Please select 1-7.")
    
    def test_manual_trigger(self):
        """Test manual healing trigger"""
        error_types = ["package_failure", "service_failure", "permission_failure", "network_failure"]
        
        print("Select error type:")
        for i, error_type in enumerate(error_types, 1):
            print(f"  {i}. {error_type}")
        
        try:
            choice = int(input("Enter choice (1-4): ")) - 1
            if 0 <= choice < len(error_types):
                error_type = error_types[choice]
                host = input("Enter host name (default: test-server): ").strip() or "test-server"
                error_msg = input("Enter error message: ").strip() or f"Test {error_type}"
                
                response = requests.post(f"{self.opspilot_url}/pipeline/test/trigger", json={
                    "error_type": error_type,
                    "host": host,
                    "error_message": error_msg
                }, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    healing_result = result.get("healing_result", {})
                    if healing_result.get("success"):
                        print(f"✅ Healing successful: {healing_result.get('session_id')}")
                        print(f"   Actions taken: {len(healing_result.get('actions_taken', []))}")
                    else:
                        print(f"❌ Healing failed: {healing_result.get('failure_reason')}")
                else:
                    print(f"❌ Request failed: HTTP {response.status_code}")
            else:
                print("Invalid choice")
        except ValueError:
            print("Invalid input")
        except Exception as e:
            print(f"Error: {e}")
    
    def show_current_status(self):
        """Show current system status"""
        try:
            response = requests.get(f"{self.opspilot_url}/pipeline/status", timeout=10)
            if response.status_code == 200:
                status = response.json()
                print("\n📊 Current Status:")
                print("=" * 30)
                
                healing_stats = status.get("pipeline_healing", {})
                print(f"Monitoring Active: {healing_stats.get('monitoring_active', False)}")
                print(f"Total Failures: {healing_stats.get('total_failures', 0)}")
                print(f"Healing Success Rate: {healing_stats.get('healing_success_rate', 0):.1%}")
                
                system_context = status.get("system_context", {})
                print(f"System Aware: {system_context.get('has_profile', False)}")
                
                if system_context.get('has_profile'):
                    print(f"Server Profile: Available")
                else:
                    print(f"Server Profile: Not available")
            else:
                print(f"❌ Failed to get status: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ Error getting status: {e}")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Full Pipeline Healing Test")
    parser.add_argument("--interactive", action="store_true", help="Run interactive demo")
    parser.add_argument("--full-test", action="store_true", help="Run full workflow test")
    
    args = parser.parse_args()
    
    test = FullPipelineTest()
    
    if args.interactive:
        test.run_interactive_demo()
    elif args.full_test:
        test.test_pipeline_healing_workflow()
    else:
        # Default to interactive
        test.run_interactive_demo()


if __name__ == "__main__":
    main()
