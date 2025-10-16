# Jenkins CI Agent (OpsPilot)

Endpoints:
- GET /ci/health
- POST /ci/jenkins/webhook
- GET /ci/runs
- GET /ci/runs/{id}
- POST /ci/intervene
- POST /ci/rerun

## 1) Server setup

- Install deps and run the app (see project README):
  - python -m venv .venv
  - .\.venv\Scripts\Activate.ps1 (Windows)
  - pip install -r requirements.txt
  - python app.py
- App runs at http://localhost:8080

## 2) Jenkins integration

- Copy shared library step from `ci_playbooks/jenkins/vars/opsPilotWrap.groovy` into your Jenkins Shared Library (or inline).
- In your Jenkinsfile (see `ci_playbooks/jenkins/Jenkinsfile.sample`), wrap stages with `opsPilotWrap { ... }`.
- Configure environment (in Jenkins global or job variables):
  - OPSPILOT_URL: e.g. http://your-opspilot-host:8080
  - JENKINS_URL: e.g. http://your-jenkins-host:8080
  - JENKINS_USER and JENKINS_TOKEN (or JENKINS_API_TOKEN)

## 3) Ansible playbooks

- Ansible collection skeleton is at `ci_playbooks/ansible/collections/ansible_collections/opspilot/ci/roles/`.
- Diagnostics role default tasks: `roles/diagnostics/tasks/main.yml`.
- Example playbook: `ci_playbooks/ansible/playbooks/diagnostics.yml`.

## 4) Webhooks and dashboard

- The shared step posts build events to `POST /ci/jenkins/webhook`.
- View runs at `/opspilot?view=ci` and click into any run to see events.

## 5) End-to-end test (manual)

1. Start OpsPilot server on port 8080.
2. Set Jenkins credentials in server env (if using /ci/rerun):
   - On the OpsPilot host: set `JENKINS_URL`, `JENKINS_USER`, `JENKINS_TOKEN`.
3. Configure Jenkins job:
   - Include the shared step `opsPilotWrap` around stages.
   - Ensure `OPSPILOT_URL` points to the OpsPilot server.
4. Trigger a failing build (e.g., simulate disk-full error log text "No space left on device").
5. Send failure log excerpt to `/ci/intervene`:
   - POST http://localhost:8080/ci/intervene
     Body JSON:
     {
       "run_id": "your-run-id",
       "log": "...No space left on device..."
     }
   - This appends a safe cleanup task to diagnostics role if the pattern matches.
6. Trigger Jenkins rerun:
   - POST http://localhost:8080/ci/rerun
     Body JSON:
     {
       "job_name": "YourJobName"
     }
7. Watch progress:
   - Open `/opspilot?view=ci` to see the run update and the intervention event.
   - Click Jenkins link (if available) to view the build.

Notes:
- `/ci/intervene` currently has a simple rule for disk-full. Extend for more patterns.
- `/ci/rerun` uses Jenkins API and requires valid credentials.
