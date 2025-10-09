#!/usr/bin/env python3
"""
Start Test Environment
Easy startup script for the Ansible healing test environment
"""
import subprocess
import time
import sys
import os
from pathlib import Path


class TestEnvironmentManager:
    """Manages the test environment lifecycle"""
    
    def __init__(self):
        """Initialize the environment manager"""
        self.base_path = Path(__file__).parent
        self.docker_path = self.base_path / "docker-environment"
        self.playbooks_path = self.base_path / "playbooks"
        self.healing_path = self.base_path / "healing-agent"
    
    def start_containers(self):
        """Start Docker containers"""
        print("🐳 Starting Docker containers...")
        
        os.chdir(self.docker_path)
        result = subprocess.run(["docker-compose", "up", "-d"], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Containers started successfully")
            return True
        else:
            print(f"❌ Failed to start containers: {result.stderr}")
            return False
    
    def wait_for_containers(self, timeout=60):
        """Wait for containers to be ready"""
        print("⏳ Waiting for containers to be ready...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.check_container_health():
                print("✅ All containers are ready")
                return True
            time.sleep(5)
        
        print("⚠️ Timeout waiting for containers")
        return False
    
    def check_container_health(self):
        """Check if all containers are healthy"""
        containers = ["healing-test-ubuntu", "healing-test-centos", "healing-test-alpine", "healing-ansible-controller"]
        
        for container in containers:
            result = subprocess.run(
                ["docker", "exec", container, "echo", "healthy"], 
                capture_output=True, text=True
            )
            if result.returncode != 0:
                return False
        
        return True
    
    def run_test_scenario(self, scenario="package_failure"):
        """Run a specific test scenario"""
        print(f"🎯 Running test scenario: {scenario}")
        
        # Run the healing integration test
        os.chdir(self.healing_path)
        result = subprocess.run([
            sys.executable, "test_healing_integration.py", "--scenario", scenario
        ], capture_output=False, text=True)
        
        return result.returncode == 0
    
    def run_ansible_playbook(self, playbook, tags=None):
        """Run an Ansible playbook with healing callback"""
        print(f"📚 Running Ansible playbook: {playbook}")
        
        # Prepare command
        cmd = [
            "docker", "exec", "healing-ansible-controller",
            "ansible-playbook", f"/workspace/playbooks/{playbook}",
            "-i", "/etc/ansible/hosts",
            "-v"
        ]
        
        if tags:
            cmd.extend(["--tags", tags])
        
        # Run playbook
        result = subprocess.run(cmd, capture_output=False, text=True)
        return result.returncode == 0
    
    def show_status(self):
        """Show environment status"""
        print("📊 Environment Status:")
        print("=" * 50)
        
        # Check Docker containers
        result = subprocess.run(["docker", "ps", "--format", "table {{.Names}}\t{{.Status}}"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("🐳 Docker Containers:")
            for line in result.stdout.split('\n'):
                if 'healing-' in line:
                    print(f"  {line}")
        
        # Check if OpsPilot is available
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent / "opsPilot"))
            from ai_shell_agent.modules.pipeline_healing import ErrorInterceptor
            print("✅ OpsPilot modules: Available")
        except ImportError:
            print("❌ OpsPilot modules: Not available")
    
    def stop_containers(self):
        """Stop Docker containers"""
        print("🛑 Stopping containers...")
        
        os.chdir(self.docker_path)
        result = subprocess.run(["docker-compose", "down"], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Containers stopped successfully")
        else:
            print(f"❌ Failed to stop containers: {result.stderr}")
    
    def interactive_menu(self):
        """Show interactive menu"""
        while True:
            print("\n🎮 Ansible Healing Test Environment")
            print("=" * 50)
            print("1. Start environment")
            print("2. Run healing integration test")
            print("3. Run Ansible playbook with failures")
            print("4. Show environment status")
            print("5. Stop environment")
            print("6. Exit")
            
            choice = input("\nSelect option (1-6): ").strip()
            
            if choice == "1":
                if self.start_containers():
                    self.wait_for_containers()
            
            elif choice == "2":
                scenarios = ["package_failure", "service_failure", "permission_failure", "all"]
                print("\nAvailable scenarios:")
                for i, scenario in enumerate(scenarios, 1):
                    print(f"  {i}. {scenario}")
                
                scenario_choice = input("Select scenario (1-4): ").strip()
                try:
                    scenario_index = int(scenario_choice) - 1
                    if 0 <= scenario_index < len(scenarios):
                        self.run_test_scenario(scenarios[scenario_index])
                    else:
                        print("Invalid scenario choice")
                except ValueError:
                    print("Invalid input")
            
            elif choice == "3":
                playbooks = [
                    "package-failure-scenario.yml",
                    "service-failure-scenario.yml", 
                    "permission-failure-scenario.yml"
                ]
                print("\nAvailable playbooks:")
                for i, playbook in enumerate(playbooks, 1):
                    print(f"  {i}. {playbook}")
                
                playbook_choice = input("Select playbook (1-3): ").strip()
                try:
                    playbook_index = int(playbook_choice) - 1
                    if 0 <= playbook_index < len(playbooks):
                        self.run_ansible_playbook(playbooks[playbook_index])
                    else:
                        print("Invalid playbook choice")
                except ValueError:
                    print("Invalid input")
            
            elif choice == "4":
                self.show_status()
            
            elif choice == "5":
                self.stop_containers()
            
            elif choice == "6":
                print("👋 Goodbye!")
                break
            
            else:
                print("Invalid choice. Please select 1-6.")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Ansible Healing Test Environment Manager")
    parser.add_argument("--start", action="store_true", help="Start the environment")
    parser.add_argument("--stop", action="store_true", help="Stop the environment")
    parser.add_argument("--status", action="store_true", help="Show environment status")
    parser.add_argument("--test", choices=["package_failure", "service_failure", "permission_failure", "all"],
                       help="Run specific test scenario")
    parser.add_argument("--interactive", action="store_true", help="Run interactive menu")
    
    args = parser.parse_args()
    
    manager = TestEnvironmentManager()
    
    if args.start:
        if manager.start_containers():
            manager.wait_for_containers()
    elif args.stop:
        manager.stop_containers()
    elif args.status:
        manager.show_status()
    elif args.test:
        manager.run_test_scenario(args.test)
    elif args.interactive:
        manager.interactive_menu()
    else:
        # Default to interactive mode
        manager.interactive_menu()


if __name__ == "__main__":
    main()
