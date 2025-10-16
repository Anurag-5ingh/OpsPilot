import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional


class JenkinsClient:

	def __init__(self, base_url: Optional[str] = None, user: Optional[str] = None, token: Optional[str] = None):
		self.base_url = (base_url or os.environ.get("JENKINS_URL", "")).rstrip("/")
		self.user = user or os.environ.get("JENKINS_USER")
		token_env = token or os.environ.get("JENKINS_TOKEN") or os.environ.get("JENKINS_API_TOKEN")
		self.token = token_env

	def _auth_header(self) -> Dict[str, str]:
		if self.user and self.token:
			import base64
			cred = f"{self.user}:{self.token}".encode()
			return {"Authorization": "Basic " + base64.b64encode(cred).decode()}
		return {}

	def _post_json(self, path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		if not self.base_url:
			return {"success": False, "error": "JENKINS_URL not configured"}
		url = f"{self.base_url}{path}"
		body = json.dumps(payload or {}).encode()
		headers = {"Content-Type": "application/json"}
		headers.update(self._auth_header())
		req = urllib.request.Request(url, data=body, headers=headers, method="POST")
		try:
			with urllib.request.urlopen(req, timeout=10) as resp:
				return {"success": True, "status": resp.status}
		except urllib.error.HTTPError as e:
			return {"success": False, "error": f"HTTP {e.code}: {e.reason}"}
		except Exception as e:
			return {"success": False, "error": str(e)}

	def trigger_job(self, job_name: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		if not job_name:
			return {"success": False, "error": "job_name required"}
		# Prefer /buildWithParameters when parameters provided, else /build
		if parameters:
			path = f"/job/{job_name}/buildWithParameters"
			return self._post_json(path, parameters)
		else:
			path = f"/job/{job_name}/build"
			return self._post_json(path)


