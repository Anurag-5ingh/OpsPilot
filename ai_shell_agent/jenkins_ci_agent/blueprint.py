import json
import time
from flask import Blueprint, request, jsonify
from . import storage as store
from .jenkins_client import JenkinsClient
from .ansible_patcher import append_task_to_diagnostics


ci_bp = Blueprint("ci", __name__, url_prefix="/ci")


@ci_bp.route("/health", methods=["GET"])
def health():

	return jsonify({"status": "ok", "service": "jenkins_ci_agent", "time": int(time.time())})


@ci_bp.route("/runs", methods=["GET"])
def list_runs():
	runs = store.list_runs(limit=int(request.args.get("limit", 50)))
	return jsonify({"success": True, "runs": runs, "total": len(runs)})


@ci_bp.route("/runs/<run_id>", methods=["GET"])
def get_run(run_id):
	data = store.get_run(run_id)
	if not data:
		return jsonify({"error": "run not found", "run_id": run_id}), 404
	return jsonify({"success": True, "run": data})


@ci_bp.route("/jenkins/webhook", methods=["POST"])
def jenkins_webhook():
	payload = request.get_json(silent=True) or {}
	# Basic correlation: derive/run id from Jenkins build data if present
	run_id = str(payload.get("run_id") or payload.get("build", {}).get("id") or payload.get("id") or int(time.time()))
	job_name = payload.get("jobName") or payload.get("job_name") or payload.get("name") or "unknown"
	status = payload.get("status") or payload.get("build", {}).get("status") or "unknown"
	links = payload.get("url") or payload.get("build", {}).get("fullUrl") or ""
	store.upsert_run({
		"id": run_id,
		"jenkins_build_id": str(payload.get("build", {}).get("id") or payload.get("build_id") or ""),
		"job_name": job_name,
		"status": status,
		"links": links,
		"updated_at": int(time.time()),
	})
	store.add_event(run_id, "jenkins_webhook", json.dumps(payload)[:100000])
	return jsonify({"success": True, "run_id": run_id})


@ci_bp.route("/intervene", methods=["POST"])
def intervene():
	data = request.get_json(silent=True) or {}
	run_id = str(data.get("run_id") or int(time.time()))
	log_excerpt = data.get("log", "")
	# naive rule: if log mentions 'No space left on device' add a disk cleanup task
	changed = False
	message = "no change"
	if "No space left on device" in log_excerpt:
		task = "- name: Clean apt cache\n  ansible.builtin.shell: apt-get clean || true\n  become: true\n"
		changed, message = append_task_to_diagnostics(task)
	store.add_event(run_id, "intervention_plan", json.dumps({"rule": "disk_full", "changed": changed, "message": message}))
	return jsonify({"success": True, "run_id": run_id, "changed": changed, "message": message})


@ci_bp.route("/rerun", methods=["POST"])
def rerun():
	data = request.get_json(silent=True) or {}
	job = data.get("job_name")
	params = data.get("parameters")
	client = JenkinsClient()
	result = client.trigger_job(job, params)
	return jsonify(result), (200 if result.get("success") else 400)


