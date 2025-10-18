# Testing: make playbook fail and have agent fix it

This document explains how to simulate a failing Ansible playbook, use the repository's agent helper to patch the role, and re-run the playbook to verify it passes.

Overview
- We'll create a deterministic failure in the `opspilot.ci.diagnostics` role by adding a task that runs a command guaranteed to fail (exit code != 0).
- We'll run the playbook `ci_playbooks/ansible/playbooks/diagnostics.yml` against localhost using Ansible (or simulate the run if you don't have Ansible installed).
- We'll use the repository helper `ai_shell_agent/jenkins_ci_agent/ansible_patcher.py` (function `append_task_to_diagnostics`) to append a corrective task.
- Re-run the playbook and verify the failure is resolved.

Files involved
- `ci_playbooks/ansible/playbooks/diagnostics.yml` - the playbook that applies the `opspilot.ci.diagnostics` role.
- `ci_playbooks/ansible/collections/ansible_collections/opspilot/ci/roles/diagnostics/tasks/main.yml` - the role's tasks; the patcher appends tasks here.
- `ai_shell_agent/jenkins_ci_agent/ansible_patcher.py` - helper used by the agent to append a task.

Prerequisites
- Python 3.8+ and pip
- (Optional) Ansible installed in your environment if you want to run the real playbook: `pip install ansible`.

Quick test (simulation, no Ansible required)
1. From the repo root, run the included test script (Python):

```powershell
python ci_playbooks/ansible/test_agent_fix.py
```

2. The script will:
   - Insert a failing task into the diagnostics role (creates deterministic fail: `false` command),
   - Show how a playbook run would fail (simulated),
   - Use the patcher to append a fixed task (for demo purposes this will append a small debug/success task),
   - Simulate re-running the playbook and show the success.

Running the real playbook with Ansible
1. Make sure Ansible is installed and you can run ad-hoc against localhost. Example (PowerShell):

```powershell
# install ansible in a virtualenv or system Python
pip install ansible

# Run the diagnostics playbook against localhost
ansible-playbook -i localhost, -c local ci_playbooks/ansible/playbooks/diagnostics.yml
```

2. If the playbook fails due to the injected failing task, run the agent patcher to append the fix (example using Python):

```powershell
python -c "from ai_shell_agent.jenkins_ci_agent.ansible_patcher import append_task_to_diagnostics; print(append_task_to_diagnostics('- name: Fix injected failure\n  ansible.builtin.shell: echo fixed'))"
```

3. Re-run the playbook (same ansible-playbook command above) and confirm it completes successfully.

Notes and safety
- The test script modifies `tasks/main.yml` in-place. The repository contains `main-backup-local` earlier but the safest approach is to create a git branch or stash changes before running any tests.
- The patcher appends tasks only if the exact YAML snippet isn't already present.
- For CI automation, wrap the patcher call with validation to avoid duplicate or unsafe changes.

If you want, I can also create a dedicated test role/playbook copy so we don't modify the primary role during experiments — tell me and I'll add a `diagnostics_test` role and playbook.
