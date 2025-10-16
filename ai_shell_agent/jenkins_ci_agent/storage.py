import os
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional


_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "ci_runs.db")
_INIT_LOCK = threading.Lock()


def _ensure_db_initialized() -> None:
	with _INIT_LOCK:
		os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
		conn = sqlite3.connect(_DB_PATH)
		try:
			c = conn.cursor()
			c.execute(
				"""
				CREATE TABLE IF NOT EXISTS ci_runs (
					id TEXT PRIMARY KEY,
					jenkins_build_id TEXT,
					job_name TEXT,
					status TEXT,
					created_at INTEGER,
					updated_at INTEGER,
					links TEXT
				)
				"""
			)
			c.execute(
				"""
				CREATE TABLE IF NOT EXISTS ci_events (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					run_id TEXT,
					type TEXT,
					payload TEXT,
					created_at INTEGER
				)
				"""
			)
			conn.commit()
		finally:
			conn.close()


def upsert_run(run: Dict[str, Any]) -> None:
	_ensure_db_initialized()
	conn = sqlite3.connect(_DB_PATH)
	try:
		c = conn.cursor()
		now = int(time.time())
		c.execute(
			"""
			INSERT INTO ci_runs (id, jenkins_build_id, job_name, status, created_at, updated_at, links)
			VALUES (?, ?, ?, ?, ?, ?, ?)
			ON CONFLICT(id) DO UPDATE SET
				jenkins_build_id=excluded.jenkins_build_id,
				job_name=excluded.job_name,
				status=excluded.status,
				updated_at=excluded.updated_at,
				links=excluded.links
			""",
			(
				run.get("id"),
				run.get("jenkins_build_id"),
				run.get("job_name"),
				run.get("status", "unknown"),
				run.get("created_at", now),
				run.get("updated_at", now),
				run.get("links", "")
			),
		)
		conn.commit()
	finally:
		conn.close()


def add_event(run_id: str, event_type: str, payload_text: str) -> None:
	_ensure_db_initialized()
	conn = sqlite3.connect(_DB_PATH)
	try:
		c = conn.cursor()
		c.execute(
			"INSERT INTO ci_events (run_id, type, payload, created_at) VALUES (?, ?, ?, ?)",
			(run_id, event_type, payload_text[:100000], int(time.time())),
		)
		conn.commit()
	finally:
		conn.close()


def list_runs(limit: int = 50) -> List[Dict[str, Any]]:
	_ensure_db_initialized()
	conn = sqlite3.connect(_DB_PATH)
	conn.row_factory = sqlite3.Row
	try:
		c = conn.cursor()
		c.execute("SELECT * FROM ci_runs ORDER BY updated_at DESC LIMIT ?", (limit,))
		rows = c.fetchall()
		return [dict(row) for row in rows]
	finally:
		conn.close()


def get_run(run_id: str) -> Optional[Dict[str, Any]]:
	_ensure_db_initialized()
	conn = sqlite3.connect(_DB_PATH)
	conn.row_factory = sqlite3.Row
	try:
		c = conn.cursor()
		c.execute("SELECT * FROM ci_runs WHERE id = ?", (run_id,))
		row = c.fetchone()
		if not row:
			return None
		c.execute("SELECT type, payload, created_at FROM ci_events WHERE run_id = ? ORDER BY id ASC", (run_id,))
		events = [dict(r) for r in c.fetchall()]
		data = dict(row)
		data["events"] = events
		return data
	finally:
		conn.close()


