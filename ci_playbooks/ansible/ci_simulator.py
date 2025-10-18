#!/usr/bin/env python3
"""Simulate a Jenkins CI run for the diagnostics_test playbook.

Usage: python ci_playbooks/ansible/ci_simulator.py
Open http://localhost:8000/ci_playbooks/ansible/ci_sim.html to watch.
"""
import json
import threading
import time
from http.server import SimpleHTTPRequestHandler, HTTPServer
from pathlib import Path

from ai_shell_agent.jenkins_ci_agent.diagnostics_test_patcher import append_task_to_diagnostics_test


ROOT = Path(__file__).resolve().parent
STATUS_FILE = ROOT / 'ci_status.json'


def write_status(tasks, job_url=None):
    STATUS_FILE.write_text(json.dumps({'tasks': tasks, 'job_url': job_url}))


def simulate_run():
    # initial run: three tasks, the third fails
    tasks = [
        {'name': 'checkout', 'status': 'ok'},
        {'name': 'build', 'status': 'ok'},
        {'name': 'tests', 'status': 'running'},
    ]
    write_status(tasks, job_url='http://jenkins.local/job/diagnostics-ci/123/')
    time.sleep(2)
    tasks[2]['status'] = 'fail'
    write_status(tasks, job_url='http://jenkins.local/job/diagnostics-ci/123/')

    # Agent activates and patches
    print('Agent detected failure, appending fix...')
    fix_task = "- name: Agent-applied fix for tests\n  ansible.builtin.shell: echo fixed\n  changed_when: false"
    changed, msg = append_task_to_diagnostics_test(fix_task)
    print('patcher:', changed, msg)
    time.sleep(1)

    # Re-run simulation: tests now pass
    tasks[2]['status'] = 'running'
    write_status(tasks, job_url='http://jenkins.local/job/diagnostics-ci/123/')
    time.sleep(1.5)
    tasks[2]['status'] = 'ok'
    write_status(tasks, job_url='http://jenkins.local/job/diagnostics-ci/123/')
    print('Simulation complete')


class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # allow CORS for local testing
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()


def serve():
    server = HTTPServer(('0.0.0.0', 8000), Handler)
    print('Serving at http://localhost:8000 — press Ctrl-C to stop')
    server.serve_forever()


def main():
    # initial status
    write_status([{'name': 'checkout', 'status': 'pending'}, {'name': 'build', 'status': 'pending'}, {'name': 'tests', 'status': 'pending'}])

    t = threading.Thread(target=serve, daemon=True)
    t.start()

    # let server start
    time.sleep(1)
    simulate_run()
    # keep server running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('Stopping')


if __name__ == '__main__':
    main()
