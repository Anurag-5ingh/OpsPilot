"""
SSH Session Manager
Flask blueprint for SSH session management endpoints
"""
from flask import Blueprint, request, jsonify

ssh_bp = Blueprint("ssh", __name__)


@ssh_bp.route("/ssh/list", methods=["GET"])
def list_ssh():
    """List saved SSH connections (database disabled)"""
    # Return empty list since we removed database functionality
    return jsonify([]), 200


@ssh_bp.route("/ssh/save", methods=["POST"])
def save_ssh():
    """Save SSH connection info (database disabled)"""
    data = request.get_json() or request.form
    host = data.get("host")
    username = data.get("username")
    port = int(data.get("port") or 22)
    description = data.get("description", "")

    if not host or not username:
        return jsonify({"error": "host and username required"}), 400

    # Since database is removed, just return success without storing
    return jsonify({
        "message": "connection info received (database disabled)",
        "host": host,
        "username": username,
        "port": port
    }), 200


@ssh_bp.route("/ssh/delete/<int:conn_id>", methods=["POST", "DELETE"])
def delete_ssh(conn_id):
    """Delete SSH connection (database disabled)"""
    # Since database is removed, just return success
    return jsonify({"message": "delete requested (database disabled)"}), 200
