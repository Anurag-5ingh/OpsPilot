# ai_shell_agent/ssh.py
from flask import Blueprint, request, jsonify

ssh_bp = Blueprint("ssh", __name__)


@ssh_bp.route("/ssh/list", methods=["GET"])
def list_ssh():
    # Return empty list since we removed database functionality
    return jsonify([]), 200


@ssh_bp.route("/ssh/save", methods=["POST"])
def save_ssh():
    data = request.get_json() or request.form
    host = data.get("host")
    username = data.get("username")
    port = int(data.get("port") or 22)
    description = data.get("description", "")

    if not host or not username:
        return jsonify({"error": "host and username required"}), 400

    # Since database is removed, just return success without storing
    return jsonify({"message": "connection info received (database disabled)", "host": host, "username": username, "port": port}), 200


@ssh_bp.route("/ssh/delete/<int:conn_id>", methods=["POST", "DELETE"])
def delete_ssh(conn_id):
    # Since database is removed, just return success
    return jsonify({"message": "delete requested (database disabled)"}), 200
