# Ansible Pipeline Healing Test Environment

This is a **temporary test environment** for developing and testing the pipeline healing capabilities. This directory will be deleted once the feature is stable and integrated.

## 🎯 Purpose

Test autonomous pipeline healing with realistic failure scenarios:
- Simulate common Ansible playbook failures
- Test error interception and analysis
- Validate autonomous healing capabilities
- Mock Jenkins pipeline integration

## 🏗️ Structure

```
ansible-healing-test/
├── docker-environment/         # Multi-OS test containers
├── playbooks/                  # Test playbooks with failure scenarios
├── healing-agent/              # Test integration with OpsPilot
├── mock-pipeline/              # Simulated Jenkins pipeline
└── test-scenarios/             # Predefined failure cases
```

## 🚀 Quick Start

1. **Start test environment:**
   ```bash
   cd docker-environment
   docker-compose up -d
   ```

2. **Run failure scenarios:**
   ```bash
   cd test-scenarios
   python run_test_scenario.py --scenario package_failure
   ```

3. **Test healing:**
   ```bash
   cd healing-agent
   python test_healing.py
   ```

## ⚠️ Important

**This is a temporary test environment and will be deleted after development is complete.**
All production code goes in `opsPilot/ai_shell_agent/modules/pipeline_healing/`.
