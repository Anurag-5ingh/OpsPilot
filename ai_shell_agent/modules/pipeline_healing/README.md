# Pipeline Healing Module

The Pipeline Healing module brings **autonomous pipeline recovery** capabilities to OpsPilot. When CI/CD pipelines fail, this system automatically analyzes errors, generates fixes using AI with server awareness, and attempts to heal the issues without human intervention.

## 🎯 **Core Concept**

Transform OpsPilot from a reactive troubleshooting tool into a **proactive pipeline healing system**:

- **Pipeline Monitoring**: Watch for failures in CI/CD pipelines
- **Error Interception**: Capture failure details and context
- **AI Analysis**: Understand root causes using server awareness
- **Autonomous Remediation**: Fix issues and retry pipelines automatically
- **Learning Loop**: Improve over time from successful fixes

## 🏗️ **Architecture**

```
pipeline_healing/
├── __init__.py                 # Module exports
├── error_interceptor.py        # Captures and analyzes pipeline failures
├── autonomous_healer.py        # Core healing engine with AI integration
├── pipeline_monitor.py         # Monitors pipelines and triggers healing
├── ansible_integration.py      # Specialized Ansible integration
└── README.md                   # This documentation
```

## 🔧 **Core Components**

### **ErrorInterceptor** (`error_interceptor.py`)
- Captures failures from Ansible, Jenkins, GitLab, etc.
- Categorizes errors (package, service, permission, network, etc.)
- Assesses severity and suggests initial actions
- Maintains error history for analysis

### **AutonomousHealer** (`autonomous_healer.py`)
- **AI-Powered Analysis**: Uses existing troubleshooting module with server context
- **Safety Validation**: Checks fix safety before execution
- **Multi-Step Healing**: Diagnostics → Fixes → Verification
- **Risk Assessment**: Evaluates and prevents dangerous operations
- **Healing History**: Tracks success rates and learning

### **PipelineMonitor** (`pipeline_monitor.py`)
- **Webhook Handler**: Receives failure notifications from CI/CD systems
- **Multi-Pipeline Support**: Monitors Jenkins, Ansible, GitLab pipelines
- **Callback System**: Extensible notification system
- **Statistics Tracking**: Monitors healing success rates

### **AnsibleIntegration** (`ansible_integration.py`)
- **Callback Plugin**: Real-time Ansible failure interception
- **Playbook Retry**: Automatic retry with healing
- **Output Parsing**: Extracts meaningful error information
- **Healing Playbooks**: Generates remediation playbooks

## 🚀 **Usage**

### **Basic Integration**
```python
from ai_shell_agent.modules.pipeline_healing import (
    ErrorInterceptor, AutonomousHealer, PipelineMonitor
)
from ai_shell_agent.modules.system_awareness import SystemContextManager

# Initialize components
system_context = SystemContextManager()
healer = AutonomousHealer(system_context)
monitor = PipelineMonitor(healer=healer)

# Handle webhook failure
webhook_data = {
    "source": "jenkins",
    "job_name": "web-deployment",
    "error_message": "Package installation failed",
    "target_hosts": ["web-server-01"]
}

result = monitor.handle_webhook_failure(webhook_data)
```

### **Ansible Integration**
```python
from ai_shell_agent.modules.pipeline_healing import AnsibleIntegration

ansible_healer = AnsibleIntegration(healer=healer)
ansible_healer.enable_auto_retry(True, max_retries=3)

# Run playbook with healing
result = ansible_healer.run_playbook_with_healing(
    playbook_path="deploy.yml",
    inventory="hosts",
    tags=["deploy"]
)
```

## 📡 **API Endpoints**

### **POST /pipeline/webhook**
Receive pipeline failure webhooks:
```json
{
  "source": "jenkins",
  "job_name": "web-app-deployment", 
  "build_number": 123,
  "stage": "Deploy",
  "error_message": "Package installation failed",
  "target_hosts": ["web-server-01"]
}
```

### **GET /pipeline/status**
Get pipeline healing system status:
```json
{
  "pipeline_healing": {
    "monitoring_active": true,
    "total_failures": 15,
    "healing_success_rate": 0.73
  }
}
```

### **GET /pipeline/healing/history**
Get healing session history:
```json
{
  "healing_history": [...],
  "success_rate": 0.73,
  "total_sessions": 15
}
```

### **POST /pipeline/test/trigger**
Test healing manually:
```json
{
  "error_type": "package_failure",
  "host": "test-server",
  "error_message": "Package not found"
}
```

## 🎮 **Testing Environment**

A complete test environment is available in `ansible-healing-test/`:

### **Quick Start**
```bash
# Start test environment
cd ansible-healing-test
python start_test_environment.py --interactive

# Run full test workflow
python run_full_test.py --full-test

# Test Jenkins simulation
python mock-pipeline/jenkins_simulator.py --failure ansible_package_failure
```

### **Test Components**
- **Docker Environment**: Multi-OS test containers (Ubuntu, CentOS, Alpine)
- **Failure Scenarios**: Realistic Ansible playbook failures
- **Jenkins Simulator**: Mock Jenkins pipeline with webhook integration
- **Healing Tests**: End-to-end healing workflow validation

## 🔄 **Healing Workflow**

### **1. Failure Detection**
- Pipeline fails (Ansible task, Jenkins stage, etc.)
- Error interceptor captures failure details
- Error categorization and severity assessment

### **2. AI Analysis**
- Server awareness provides context about target systems
- AI analyzes error with server-specific knowledge
- Generates targeted diagnostic and fix commands

### **3. Safety Validation**
- Risk assessment of proposed fixes
- Safety checks prevent destructive operations
- Human approval for high-risk operations

### **4. Autonomous Execution**
- Execute diagnostic commands to gather information
- Apply fixes using server-appropriate commands
- Verify fixes with confirmation commands

### **5. Pipeline Retry**
- Retry failed pipeline stage/task
- Monitor for success or additional failures
- Learn from results for future improvements

## 🛡️ **Safety Features**

### **Risk Assessment**
- **Low Risk**: Package installations, service restarts
- **Medium Risk**: Configuration changes, file modifications
- **High Risk**: System modifications, destructive operations

### **Safety Checks**
- Validates commands before execution
- Prevents destructive operations (`rm -rf`, `mkfs`, etc.)
- Requires confirmation for high-risk fixes
- Maintains rollback plans where possible

### **Validation**
- Pre-execution command compatibility checking
- Post-execution verification of fixes
- Rollback mechanisms for failed healing attempts

## 📊 **Monitoring & Analytics**

### **Success Metrics**
- Healing success rate per error category
- Time to resolution for different failure types
- Pipeline retry success rates
- Server-specific healing effectiveness

### **Learning Insights**
- Common failure patterns by server type
- Most effective fixes for specific errors
- Server configuration impact on success rates
- Improvement opportunities identification

## 🔮 **Future Enhancements**

### **Advanced Learning**
- **Pattern Recognition**: Learn from successful healing patterns
- **Predictive Healing**: Prevent issues before they occur
- **Cross-Pipeline Learning**: Share knowledge between different pipelines

### **Enhanced Integration**
- **GitLab CI/CD**: Native GitLab pipeline integration
- **GitHub Actions**: GitHub workflow healing support
- **Kubernetes**: Container orchestration healing

### **Intelligent Automation**
- **Dependency Resolution**: Understand and fix dependency chains
- **Multi-Host Coordination**: Coordinate healing across server clusters
- **Infrastructure as Code**: Heal infrastructure definition issues

## 🎯 **Benefits**

### **Operational Excellence**
- **Reduced MTTR**: Faster recovery from pipeline failures
- **24/7 Availability**: Autonomous healing without human intervention
- **Consistent Fixes**: AI-generated solutions based on best practices

### **Developer Productivity**
- **Fewer Interruptions**: Developers focus on features, not pipeline issues
- **Faster Deployments**: Reduced pipeline failure impact
- **Learning Acceleration**: AI learns and improves over time

### **Cost Optimization**
- **Reduced Downtime**: Faster issue resolution
- **Lower Operational Overhead**: Less manual intervention required
- **Improved Resource Utilization**: More successful deployments

## 🚨 **Important Notes**

- **Server Awareness Required**: Works best with server profiling enabled
- **Safety First**: High-risk operations require human approval
- **Learning System**: Improves over time with more healing attempts
- **Extensible Design**: Easy to add new pipeline systems and error types

The Pipeline Healing module represents the next evolution of OpsPilot - from reactive troubleshooting to proactive, intelligent pipeline recovery that keeps your CI/CD systems running smoothly! 🚀
