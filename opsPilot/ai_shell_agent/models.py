# ai_shell_agent/models.py
# Database models for the application.

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# SQLAlchemy instance (initialized in app.py)
db = SQLAlchemy()


class User(UserMixin, db.Model):
    # Keep table name default if you already had it earlier.
    # If you prefer an explicit table name, uncomment the next line:
    # __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password: str):
        """Hashes and stores the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verifies the provided password."""
        return check_password_hash(self.password_hash, password)


class SSHConnection(db.Model):
    """
    Stores simple SSH connection metadata for each user.
    NOTE: This does NOT store passwords. It assumes key-based SSH auth
    (which is what your existing create_ssh_client() uses).
    """
    __tablename__ = "ssh_connections"

    id = db.Column(db.Integer, primary_key=True)
    host = db.Column(db.String(255), nullable=False)
    username = db.Column(db.String(150), nullable=False)
    port = db.Column(db.Integer, default=22, nullable=False)

    # Link to the User table. If your User table uses a different tablename,
    # ensure the FK refers to the correct table name (default is 'user' or 'users').
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    owner = db.relationship("User", backref=db.backref("ssh_connections", lazy=True))
