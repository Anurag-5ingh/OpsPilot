import os
from typing import Tuple


def append_task_to_diagnostics(task_yaml: str) -> Tuple[bool, str]:
	"""Append a YAML task to the diagnostics role tasks/main.yml if not present.

	Returns (changed, message).
	"""
	root = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ci_playbooks", "ansible", "collections", "ansible_collections", "opspilot", "ci", "roles", "diagnostics", "tasks"))
	path = os.path.join(root, "main.yml")
	if not os.path.exists(path):
		return False, f"tasks/main.yml not found at {path}"
	with open(path, "r", encoding="utf-8") as f:
		content = f.read()
	if task_yaml.strip() in content:
		return False, "Task already present"
	with open(path, "a", encoding="utf-8") as f:
		f.write("\n" + task_yaml.strip() + "\n")
	return True, "Task appended"


