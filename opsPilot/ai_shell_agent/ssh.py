# ai_shell_agent/ssh.py
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from .models import db, SSHConnection

ssh_bp = Blueprint("ssh", __name__)


@ssh_bp.route("/ssh/list", methods=["GET"])
@login_required
def list_ssh():
    conns = SSHConnection.query.filter_by(user_id=current_user.id).all()
    out = []
    for c in conns:
        out.append({
            "id": c.id,
            "host": c.host,
            "username": c.username,
            "port": c.port
        })
    return jsonify(out), 200


@ssh_bp.route("/ssh/save", methods=["POST"])
@login_required
def save_ssh():
    data = request.get_json() or request.form
    host = data.get("host")
    username = data.get("username")
    port = int(data.get("port") or 22)

    if not host or not username:
        return jsonify({"error": "host and username required"}), 400

    # Create a new connection (we allow multiple connections per user)
    conn = SSHConnection(host=host, username=username, port=port, user_id=current_user.id)
    db.session.add(conn)
    db.session.commit()

    return jsonify({"message": "saved", "id": conn.id}), 201


@ssh_bp.route("/ssh/delete/<int:conn_id>", methods=["POST", "DELETE"])
@login_required
def delete_ssh(conn_id):
    conn = SSHConnection.query.filter_by(id=conn_id, user_id=current_user.id).first()
    if not conn:
        return jsonify({"error": "not found"}), 404
    db.session.delete(conn)
    db.session.commit()
    return jsonify({"message": "deleted"}), 200
