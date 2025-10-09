#!/usr/bin/env python3
"""
Jenkins Pipeline Simulator
Simulates Jenkins pipeline failures and webhook notifications for testing
"""
import json
import time
import requests
from typing import Dict, List
from datetime import datetime


class JenkinsSimulator:
    """Simulates Jenkins pipeline behavior for testing"""
    
    def __init__(self, opspilot_webhook_url: str = "http://localhost:8080/pipeline/webhook"):
        """
        Initialize Jenkins simulator
        
        Args:
            opspilot_webhook_url: URL to send failure webhooks
        """
        self.webhook_url = opspilot_webhook_url
        self.jobs = {}
        self.build_counter = 1
    
    def create_job(self, job_name: str, job_config: Dict):
        """Create a simulated Jenkins job"""
        self.jobs[job_name] = {
            "config": job_config,
            "builds": [],
            "last_build": 0
        }
        print(f"📋 Created Jenkins job: {job_name}")
    
    def simulate_pipeline_run(self, job_name: str, failure_scenario: str = None) -> Dict:
        """
        Simulate a pipeline run with optional failure
        
        Args:
            job_name: Name of the job to run
            failure_scenario: Type of failure to simulate
            
        Returns:
            Build result
        """
        if job_name not in self.jobs:
            return {"error": f"Job {job_name} not found"}
        
        build_number = self.build_counter
        self.build_counter += 1
        
        build_result = {
            "job_name": job_name,
            "build_number": build_number,
            "timestamp": datetime.now().isoformat(),
            "status": "SUCCESS",
            "stages": [],
            "console_output": "",
            "build_url": f"http://jenkins.example.com/job/{job_name}/{build_number}/"
        }
        
        print(f"🚀 Starting Jenkins build: {job_name} #{build_number}")
        
        # Simulate pipeline stages
        stages = self.jobs[job_name]["config"].get("stages", ["Checkout", "Build", "Test", "Deploy"])
        
        for i, stage in enumerate(stages):
            stage_result = self._simulate_stage(stage, failure_scenario, i)
            build_result["stages"].append(stage_result)
            build_result["console_output"] += stage_result["output"] + "\n"
            
            if not stage_result["success"]:
                build_result["status"] = "FAILURE"
                build_result["failed_stage"] = stage
                
                # Send failure webhook
                self._send_failure_webhook(build_result, stage_result)
                break
            
            time.sleep(0.5)  # Simulate stage execution time
        
        # Store build result
        self.jobs[job_name]["builds"].append(build_result)
        self.jobs[job_name]["last_build"] = build_number
        
        print(f"🏁 Build completed: {job_name} #{build_number} - {build_result['status']}")
        return build_result
    
    def _simulate_stage(self, stage_name: str, failure_scenario: str, stage_index: int) -> Dict:
        """Simulate individual pipeline stage"""
        stage_result = {
            "name": stage_name,
            "success": True,
            "duration": 5 + stage_index * 2,
            "output": f"[{stage_name}] Stage started...\n"
        }
        
        # Simulate different failure scenarios
        if failure_scenario and self._should_fail_stage(stage_name, failure_scenario):
            if failure_scenario == "ansible_package_failure":
                stage_result.update({
                    "success": False,
                    "error_type": "ansible_failure",
                    "output": stage_result["output"] + self._get_ansible_package_failure_output()
                })
            elif failure_scenario == "ansible_service_failure":
                stage_result.update({
                    "success": False,
                    "error_type": "ansible_failure", 
                    "output": stage_result["output"] + self._get_ansible_service_failure_output()
                })
            elif failure_scenario == "docker_build_failure":
                stage_result.update({
                    "success": False,
                    "error_type": "docker_failure",
                    "output": stage_result["output"] + self._get_docker_build_failure_output()
                })
            elif failure_scenario == "test_failure":
                stage_result.update({
                    "success": False,
                    "error_type": "test_failure",
                    "output": stage_result["output"] + self._get_test_failure_output()
                })
        else:
            stage_result["output"] += f"[{stage_name}] Stage completed successfully\n"
        
        return stage_result
    
    def _should_fail_stage(self, stage_name: str, failure_scenario: str) -> bool:
        """Determine if stage should fail based on scenario"""
        failure_stage_map = {
            "ansible_package_failure": ["Deploy", "Provision"],
            "ansible_service_failure": ["Deploy", "Configure"],
            "docker_build_failure": ["Build"],
            "test_failure": ["Test", "Unit Tests"]
        }
        
        target_stages = failure_stage_map.get(failure_scenario, [])
        return any(target in stage_name for target in target_stages)
    
    def _get_ansible_package_failure_output(self) -> str:
        """Generate Ansible package failure output"""
        return """
[Deploy] Running Ansible playbook...
[Deploy] TASK [Install web server] **************************************************
[Deploy] fatal: [web-server-01]: FAILED! => {
[Deploy]     "changed": false,
[Deploy]     "msg": "No package matching 'httpd' is available",
[Deploy]     "rc": 100,
[Deploy]     "stderr": "E: Unable to locate package httpd\\n",
[Deploy]     "stderr_lines": ["E: Unable to locate package httpd"],
[Deploy]     "stdout": "",
[Deploy]     "stdout_lines": []
[Deploy] }
[Deploy] PLAY RECAP *****************************************************************
[Deploy] web-server-01             : ok=2    changed=0    unreachable=0    failed=1    skipped=0    rescued=0    ignored=0
[Deploy] ERROR: Ansible playbook failed
"""
    
    def _get_ansible_service_failure_output(self) -> str:
        """Generate Ansible service failure output"""
        return """
[Configure] Running Ansible playbook...
[Configure] TASK [Start web service] ***********************************************
[Configure] fatal: [web-server-01]: FAILED! => {
[Configure]     "changed": false,
[Configure]     "msg": "Could not find the requested service nginx: host",
[Configure]     "name": "nginx",
[Configure]     "state": "started"
[Configure] }
[Configure] PLAY RECAP *************************************************************
[Configure] web-server-01          : ok=3    changed=1    unreachable=0    failed=1    skipped=0    rescued=0    ignored=0
[Configure] ERROR: Service management failed
"""
    
    def _get_docker_build_failure_output(self) -> str:
        """Generate Docker build failure output"""
        return """
[Build] Building Docker image...
[Build] Step 3/8 : RUN apt-get update && apt-get install -y nginx
[Build]  ---> Running in 7f8a9b2c3d4e
[Build] E: Unable to locate package nginx
[Build] The command '/bin/sh -c apt-get update && apt-get install -y nginx' returned a non-zero code: 100
[Build] ERROR: Docker build failed
"""
    
    def _get_test_failure_output(self) -> str:
        """Generate test failure output"""
        return """
[Test] Running unit tests...
[Test] ================================ FAILURES =================================
[Test] _________________________ test_web_server_response _________________________
[Test] 
[Test]     def test_web_server_response():
[Test]         response = requests.get('http://localhost:80')
[Test] >       assert response.status_code == 200
[Test] E       requests.exceptions.ConnectionError: HTTPConnectionPool(host='localhost', port=80)
[Test] E       Max retries exceeded with url: / (Caused by NewConnectionError)
[Test] 
[Test] ========================= 1 failed, 5 passed in 2.34s =========================
[Test] ERROR: Tests failed
"""
    
    def _send_failure_webhook(self, build_result: Dict, stage_result: Dict):
        """Send failure webhook to OpsPilot"""
        webhook_payload = {
            "source": "jenkins",
            "job_name": build_result["job_name"],
            "build_number": build_result["build_number"],
            "stage": stage_result["name"],
            "error_message": self._extract_error_message(stage_result["output"]),
            "console_output": build_result["console_output"],
            "build_url": build_result["build_url"],
            "timestamp": build_result["timestamp"],
            "error_type": stage_result.get("error_type", "unknown"),
            "target_hosts": self._extract_target_hosts(stage_result["output"])
        }
        
        try:
            print(f"📡 Sending failure webhook to OpsPilot...")
            response = requests.post(
                self.webhook_url,
                json=webhook_payload,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"✅ Webhook sent successfully")
                webhook_response = response.json()
                if webhook_response.get("healing_result"):
                    print(f"🏥 Healing triggered: {webhook_response['healing_result'].get('session_id')}")
            else:
                print(f"⚠️ Webhook failed: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Webhook error: {e}")
    
    def _extract_error_message(self, output: str) -> str:
        """Extract main error message from output"""
        lines = output.split('\n')
        for line in lines:
            if 'ERROR:' in line:
                return line.split('ERROR:', 1)[1].strip()
            elif '"msg":' in line:
                # Extract Ansible error message
                try:
                    start = line.find('"msg": "') + 8
                    end = line.find('",', start)
                    if start > 7 and end > start:
                        return line[start:end]
                except:
                    pass
        
        return "Pipeline stage failed"
    
    def _extract_target_hosts(self, output: str) -> List[str]:
        """Extract target hosts from Ansible output"""
        hosts = []
        lines = output.split('\n')
        for line in lines:
            if 'fatal:' in line and '[' in line and ']' in line:
                try:
                    start = line.find('[') + 1
                    end = line.find(']', start)
                    if start > 0 and end > start:
                        host = line[start:end]
                        if host not in hosts:
                            hosts.append(host)
                except:
                    pass
        
        return hosts or ["unknown-host"]
    
    def get_job_status(self, job_name: str) -> Dict:
        """Get job status"""
        if job_name not in self.jobs:
            return {"error": f"Job {job_name} not found"}
        
        job = self.jobs[job_name]
        return {
            "job_name": job_name,
            "last_build": job["last_build"],
            "total_builds": len(job["builds"]),
            "success_rate": self._calculate_success_rate(job["builds"])
        }
    
    def _calculate_success_rate(self, builds: List[Dict]) -> float:
        """Calculate success rate for builds"""
        if not builds:
            return 0.0
        
        successful = sum(1 for build in builds if build["status"] == "SUCCESS")
        return successful / len(builds)


def main():
    """Test Jenkins simulator"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Jenkins Pipeline Simulator")
    parser.add_argument("--job", default="web-app-deployment", help="Job name")
    parser.add_argument("--failure", choices=["ansible_package_failure", "ansible_service_failure", 
                                            "docker_build_failure", "test_failure"],
                       help="Failure scenario to simulate")
    parser.add_argument("--webhook-url", default="http://localhost:8080/pipeline/webhook",
                       help="OpsPilot webhook URL")
    
    args = parser.parse_args()
    
    # Initialize simulator
    simulator = JenkinsSimulator(args.webhook_url)
    
    # Create test job
    job_config = {
        "stages": ["Checkout", "Build", "Test", "Deploy", "Verify"],
        "ansible_playbook": "deploy-web-app.yml",
        "target_hosts": ["web-server-01", "web-server-02"]
    }
    
    simulator.create_job(args.job, job_config)
    
    # Run pipeline
    result = simulator.simulate_pipeline_run(args.job, args.failure)
    
    print(f"\n📊 Pipeline Result:")
    print(f"  Job: {result['job_name']}")
    print(f"  Build: #{result['build_number']}")
    print(f"  Status: {result['status']}")
    print(f"  Stages: {len(result['stages'])}")
    
    if result['status'] == 'FAILURE':
        print(f"  Failed Stage: {result.get('failed_stage')}")


if __name__ == "__main__":
    main()
