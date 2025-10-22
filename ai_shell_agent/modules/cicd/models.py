"""
Database Models for CI/CD Integration

Contains SQLAlchemy models for storing Jenkins builds, Ansible configs, and fix history.
Uses SQLite database for simplicity and portability.
"""

import os
import json
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Database path
DB_PATH = Path("ai_shell_agent/data/cicd.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


class DatabaseManager:
    """Manages SQLite database connection and operations."""
    
    def __init__(self, db_path: str = str(DB_PATH)):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database with required tables and handle migrations."""
        with sqlite3.connect(self.db_path) as conn:
            # Create tables with IF NOT EXISTS (safe for existing DBs)
            conn.executescript("""
                -- Build logs table
                CREATE TABLE IF NOT EXISTS build_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_name TEXT NOT NULL,
                    build_number INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    duration INTEGER,
                    started_at TIMESTAMP,
                    jenkins_url TEXT,
                    target_server TEXT,
                    console_log_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(job_name, build_number)
                );
                
                -- Ansible configurations table  
                CREATE TABLE IF NOT EXISTS ansible_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    local_path TEXT,
                    git_repo_url TEXT,
                    git_branch TEXT DEFAULT 'main',
                    last_synced TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Fix history table
                CREATE TABLE IF NOT EXISTS fix_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    build_id INTEGER,
                    server_id TEXT,
                    commands TEXT,  -- JSON array of commands
                    error_summary TEXT,
                    execution_result TEXT,  -- JSON with results
                    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_confirmed BOOLEAN DEFAULT FALSE,
                    success BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (build_id) REFERENCES build_logs (id)
                );
                
                -- Create indexes for better performance
                CREATE INDEX IF NOT EXISTS idx_build_logs_server ON build_logs(target_server);
                CREATE INDEX IF NOT EXISTS idx_build_logs_status ON build_logs(status);
                CREATE INDEX IF NOT EXISTS idx_build_logs_started ON build_logs(started_at);
                CREATE INDEX IF NOT EXISTS idx_fix_history_build ON fix_history(build_id);
                CREATE INDEX IF NOT EXISTS idx_fix_history_server ON fix_history(server_id);
            """)
            
            # Handle Jenkins table creation/migration separately
            self._migrate_jenkins_configs_table(conn)
    
    def _migrate_jenkins_configs_table(self, conn):
        """Create or migrate Jenkins configurations table."""
        # Check if table exists and get its schema
        cursor = conn.cursor()
        cursor.execute("""
            SELECT sql FROM sqlite_master 
            WHERE type='table' AND name='jenkins_configs'
        """)
        result = cursor.fetchone()
        
        if result is None:
            # Table doesn't exist, create new one with full schema
            logger.info("Creating new jenkins_configs table")
            conn.execute("""
                CREATE TABLE jenkins_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    base_url TEXT NOT NULL,
                    username TEXT NOT NULL,
                    password_secret_id TEXT,  -- Reference to secure password storage
                    api_token_secret_id TEXT,  -- Reference to secure API token storage (optional)
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_sync TIMESTAMP
                );
            """)
            conn.commit()
        else:
            # Table exists, check for missing columns and add them
            table_schema = result[0] or ''
            try:
                if 'password_secret_id' not in table_schema:
                    logger.info("Adding password_secret_id column to existing jenkins_configs table")
                    conn.execute("""
                        ALTER TABLE jenkins_configs 
                        ADD COLUMN password_secret_id TEXT;
                    """)
                    conn.commit()
                if 'api_token_secret_id' not in table_schema:
                    logger.info("Adding api_token_secret_id column to existing jenkins_configs table")
                    conn.execute("""
                        ALTER TABLE jenkins_configs 
                        ADD COLUMN api_token_secret_id TEXT;
                    """)
                    conn.commit()
            except Exception as e:
                logger.error(f"Failed migrating jenkins_configs table: {e}")
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute SELECT query and return results as list of dicts."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute INSERT/UPDATE/DELETE query and return affected row count."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor.rowcount
    
    def execute_insert(self, query: str, params: tuple = ()) -> int:
        """Execute INSERT query and return the new row ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor.lastrowid
    
    def get_last_insert_id(self) -> int:
        """Get the ID of the last inserted row."""
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


# Global database manager instance
db = DatabaseManager()


class BuildLog:
    """Model for Jenkins build logs."""
    
    def __init__(self, job_name: str, build_number: int, status: str, 
                 duration: Optional[int] = None, started_at: Optional[datetime] = None,
                 jenkins_url: Optional[str] = None, target_server: Optional[str] = None,
                 console_log_url: Optional[str] = None, **kwargs):
        self.job_name = job_name
        self.build_number = build_number
        self.status = status
        self.duration = duration
        self.started_at = started_at
        self.jenkins_url = jenkins_url
        self.target_server = target_server
        self.console_log_url = console_log_url
        self.id = kwargs.get('id')
        self.created_at = kwargs.get('created_at')
    
    def save(self) -> int:
        """Save build log to database."""
        query = """
            INSERT OR REPLACE INTO build_logs 
            (job_name, build_number, status, duration, started_at, jenkins_url, 
             target_server, console_log_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            self.job_name, self.build_number, self.status, self.duration,
            self.started_at, self.jenkins_url, self.target_server, self.console_log_url
        )
        
        db.execute_update(query, params)
        
        # Get the ID of the inserted/updated record
        id_query = "SELECT id FROM build_logs WHERE job_name = ? AND build_number = ?"
        result = db.execute_query(id_query, (self.job_name, self.build_number))
        if result:
            self.id = result[0]['id']
            return self.id
        return 0
    
    @classmethod
    def get_by_server(cls, server_name: str, limit: int = 50) -> List['BuildLog']:
        """Get build logs for a specific server."""
        query = """
            SELECT * FROM build_logs 
            WHERE target_server = ? 
            ORDER BY started_at DESC, build_number DESC 
            LIMIT ?
        """
        results = db.execute_query(query, (server_name, limit))
        return [cls(**row) for row in results]
    
    @classmethod
    def get_failed_builds(cls, server_name: Optional[str] = None, limit: int = 20) -> List['BuildLog']:
        """Get failed builds, optionally filtered by server."""
        query = "SELECT * FROM build_logs WHERE status IN ('FAILURE', 'ABORTED', 'UNSTABLE')"
        params = []
        
        if server_name:
            query += " AND target_server = ?"
            params.append(server_name)
        
        query += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)
        
        results = db.execute_query(query, tuple(params))
        return [cls(**row) for row in results]
    
    @classmethod
    def get_by_id(cls, build_id: int) -> Optional['BuildLog']:
        """Get build log by ID."""
        results = db.execute_query("SELECT * FROM build_logs WHERE id = ?", (build_id,))
        return cls(**results[0]) if results else None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        # Normalize datetime fields that may come back from SQLite as strings
        def to_iso(value):
            if isinstance(value, datetime):
                return value.isoformat()
            # Leave strings as-is; frontend can display them
            return value
        
        return {
            'id': self.id,
            'job_name': self.job_name,
            'build_number': self.build_number,
            'status': self.status,
            'duration': self.duration,
            'started_at': to_iso(self.started_at) if self.started_at else None,
            'jenkins_url': self.jenkins_url,
            'target_server': self.target_server,
            'console_log_url': self.console_log_url,
            'created_at': self.created_at
        }


class AnsibleConfig:
    """Model for Ansible configurations."""
    
    def __init__(self, user_id: str, name: str, local_path: Optional[str] = None,
                 git_repo_url: Optional[str] = None, git_branch: str = 'main',
                 last_synced: Optional[datetime] = None, **kwargs):
        self.user_id = user_id
        self.name = name
        self.local_path = local_path
        self.git_repo_url = git_repo_url
        self.git_branch = git_branch
        self.last_synced = last_synced
        self.id = kwargs.get('id')
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
    
    def save(self) -> int:
        """Save Ansible config to database."""
        if self.id:
            # Update existing
            query = """
                UPDATE ansible_configs 
                SET name = ?, local_path = ?, git_repo_url = ?, git_branch = ?,
                    last_synced = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """
            params = (self.name, self.local_path, self.git_repo_url, 
                     self.git_branch, self.last_synced, self.id)
            db.execute_update(query, params)
            return self.id
        else:
            # Insert new
            query = """
                INSERT INTO ansible_configs 
                (user_id, name, local_path, git_repo_url, git_branch, last_synced)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            params = (self.user_id, self.name, self.local_path, 
                     self.git_repo_url, self.git_branch, self.last_synced)
            new_id = db.execute_insert(query, params)
            if new_id:
                self.id = new_id
                return new_id
            return 0
    
    @classmethod
    def get_by_user(cls, user_id: str) -> List['AnsibleConfig']:
        """Get Ansible configs for a user."""
        results = db.execute_query(
            "SELECT * FROM ansible_configs WHERE user_id = ? ORDER BY name", 
            (user_id,)
        )
        return [cls(**row) for row in results]
    
    @classmethod
    def get_by_id(cls, config_id: int) -> Optional['AnsibleConfig']:
        """Get Ansible config by ID."""
        results = db.execute_query("SELECT * FROM ansible_configs WHERE id = ?", (config_id,))
        return cls(**results[0]) if results else None
    
    def delete(self) -> bool:
        """Delete this Ansible config."""
        if self.id:
            rows = db.execute_update("DELETE FROM ansible_configs WHERE id = ?", (self.id,))
            return rows > 0
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        def to_iso(value):
            if isinstance(value, datetime):
                return value.isoformat()
            return value
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'local_path': self.local_path,
            'git_repo_url': self.git_repo_url,
            'git_branch': self.git_branch,
            'last_synced': to_iso(self.last_synced) if self.last_synced else None,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


class FixHistory:
    """Model for fix command execution history."""
    
    def __init__(self, build_id: Optional[int], server_id: str, commands: List[str],
                 error_summary: str, execution_result: Optional[Dict] = None,
                 user_confirmed: bool = False, success: bool = False, **kwargs):
        self.build_id = build_id
        self.server_id = server_id
        self.commands = commands
        self.error_summary = error_summary
        self.execution_result = execution_result or {}
        self.user_confirmed = user_confirmed
        self.success = success
        self.id = kwargs.get('id')
        self.executed_at = kwargs.get('executed_at')
    
    def save(self) -> int:
        """Save fix history to database."""
        query = """
            INSERT INTO fix_history 
            (build_id, server_id, commands, error_summary, execution_result, 
             user_confirmed, success)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            self.build_id, self.server_id, json.dumps(self.commands), 
            self.error_summary, json.dumps(self.execution_result),
            self.user_confirmed, self.success
        )
        new_id = db.execute_insert(query, params)
        if new_id:
            self.id = new_id
            return new_id
        return 0
    
    @classmethod
    def get_by_build(cls, build_id: int) -> List['FixHistory']:
        """Get fix history for a specific build."""
        results = db.execute_query(
            "SELECT * FROM fix_history WHERE build_id = ? ORDER BY executed_at DESC", 
            (build_id,)
        )
        return [cls._from_db_row(row) for row in results]
    
    @classmethod
    def get_by_server(cls, server_id: str, limit: int = 50) -> List['FixHistory']:
        """Get fix history for a specific server."""
        results = db.execute_query(
            "SELECT * FROM fix_history WHERE server_id = ? ORDER BY executed_at DESC LIMIT ?", 
            (server_id, limit)
        )
        return [cls._from_db_row(row) for row in results]
    
    @classmethod
    def _from_db_row(cls, row: Dict[str, Any]) -> 'FixHistory':
        """Create instance from database row."""
        # Parse JSON fields
        commands = json.loads(row['commands']) if row['commands'] else []
        execution_result = json.loads(row['execution_result']) if row['execution_result'] else {}
        
        return cls(
            build_id=row['build_id'],
            server_id=row['server_id'],
            commands=commands,
            error_summary=row['error_summary'],
            execution_result=execution_result,
            user_confirmed=row['user_confirmed'],
            success=row['success'],
            id=row['id'],
            executed_at=row['executed_at']
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'build_id': self.build_id,
            'server_id': self.server_id,
            'commands': self.commands,
            'error_summary': self.error_summary,
            'execution_result': self.execution_result,
            'user_confirmed': self.user_confirmed,
            'success': self.success,
            'executed_at': self.executed_at
        }


class JenkinsConfig:
    """Model for Jenkins configurations."""
    
    def __init__(self, user_id: str, name: str, base_url: str, username: str,
                 password_secret_id: Optional[str] = None,
                 api_token_secret_id: Optional[str] = None, last_sync: Optional[datetime] = None,
                 **kwargs):
        self.user_id = user_id
        self.name = name
        self.base_url = base_url.rstrip('/')  # Remove trailing slash
        self.username = username
        self.password_secret_id = password_secret_id
        self.api_token_secret_id = api_token_secret_id
        self.last_sync = last_sync
        self.id = kwargs.get('id')
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
    
    def save(self) -> int:
        """Save Jenkins config to database."""
        if self.id:
            # Update existing
            query = """
                UPDATE jenkins_configs 
                SET name = ?, base_url = ?, username = ?, password_secret_id = ?, api_token_secret_id = ?,
                    last_sync = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """
            params = (self.name, self.base_url, self.username, self.password_secret_id,
                     self.api_token_secret_id, self.last_sync, self.id)
            db.execute_update(query, params)
            return self.id
        else:
            # Insert new
            query = """
                INSERT INTO jenkins_configs 
                (user_id, name, base_url, username, password_secret_id, api_token_secret_id, last_sync)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            params = (self.user_id, self.name, self.base_url, self.username,
                     self.password_secret_id, self.api_token_secret_id, self.last_sync)
            new_id = db.execute_insert(query, params)
            if new_id:
                self.id = new_id
                return new_id
            return 0
    
    @classmethod
    def get_by_user(cls, user_id: str) -> List['JenkinsConfig']:
        """Get Jenkins configs for a user."""
        results = db.execute_query(
            "SELECT * FROM jenkins_configs WHERE user_id = ? ORDER BY name", 
            (user_id,)
        )
        return [cls(**row) for row in results]
    
    @classmethod
    def get_by_id(cls, config_id: int) -> Optional['JenkinsConfig']:
        """Get Jenkins config by ID."""
        results = db.execute_query("SELECT * FROM jenkins_configs WHERE id = ?", (config_id,))
        return cls(**results[0]) if results else None
    
    def delete(self) -> bool:
        """Delete this Jenkins config."""
        if self.id:
            rows = db.execute_update("DELETE FROM jenkins_configs WHERE id = ?", (self.id,))
            return rows > 0
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization (without sensitive data)."""
        def to_iso(value):
            if isinstance(value, datetime):
                return value.isoformat()
            return value
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'base_url': self.base_url,
            'username': self.username,
            'has_password': bool(self.password_secret_id),
            'has_api_token': bool(self.api_token_secret_id),
            'last_sync': to_iso(self.last_sync) if self.last_sync else None,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
