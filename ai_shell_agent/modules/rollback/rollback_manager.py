"""
Enhanced Command Rollback System

Comprehensive rollback and recovery mechanisms that can automatically reverse failed
operations, maintain system snapshots, and provide granular recovery options for
complex multi-step operations.
"""

import json
import threading
import time
import sqlite3
import subprocess
import shutil
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Callable, Any, Set, Union
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import logging
from pathlib import Path
import hashlib
import tempfile
import copy

from ...utils.logging_utils import get_logger

logger = get_logger(__name__)


class RollbackStatus(Enum):
    """Status of rollback operations"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


class SnapshotType(Enum):
    """Types of system snapshots"""
    FILE_SYSTEM = "file_system"
    DATABASE = "database"
    CONFIGURATION = "configuration"
    SERVICE_STATE = "service_state"
    ENVIRONMENT = "environment"
    REGISTRY = "registry"
    NETWORK = "network"
    CUSTOM = "custom"


class RecoveryMode(Enum):
    """Recovery modes for different scenarios"""
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    INTERACTIVE = "interactive"
    FORCED = "forced"


class OperationType(Enum):
    """Types of operations that can be rolled back"""
    FILE_OPERATION = "file_operation"
    SERVICE_OPERATION = "service_operation"
    DATABASE_OPERATION = "database_operation"
    CONFIGURATION_CHANGE = "configuration_change"
    PACKAGE_OPERATION = "package_operation"
    USER_OPERATION = "user_operation"
    NETWORK_OPERATION = "network_operation"
    SYSTEM_OPERATION = "system_operation"


@dataclass
class SystemSnapshot:
    """Comprehensive system snapshot"""
    snapshot_id: str
    timestamp: datetime
    hostname: str
    snapshot_type: SnapshotType
    description: str
    snapshot_data: Dict[str, Any]
    file_paths: List[str]
    dependencies: List[str]
    size_bytes: int
    checksum: str
    metadata: Dict[str, Any] = None


@dataclass
class OperationStep:
    """Individual step in a complex operation"""
    step_id: str
    operation_id: str
    command: str
    description: str
    operation_type: OperationType
    execution_order: int
    rollback_command: Optional[str] = None
    rollback_dependencies: List[str] = None
    pre_execution_snapshot: Optional[str] = None
    post_execution_snapshot: Optional[str] = None
    execution_result: Optional[Dict[str, Any]] = None
    rollback_result: Optional[Dict[str, Any]] = None
    is_critical: bool = False
    auto_rollback: bool = True


@dataclass
class RollbackOperation:
    """Complete rollback operation"""
    rollback_id: str
    operation_id: str
    description: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: RollbackStatus = RollbackStatus.PENDING
    recovery_mode: RecoveryMode = RecoveryMode.AUTOMATIC
    steps_to_rollback: List[str] = None
    rollback_steps: List[OperationStep] = None
    success_count: int = 0
    failure_count: int = 0
    error_messages: List[str] = None
    requires_manual_intervention: bool = False


@dataclass
class RecoveryPoint:
    """System recovery point"""
    recovery_point_id: str
    timestamp: datetime
    hostname: str
    description: str
    snapshots: List[str]  # List of snapshot IDs
    operation_context: Dict[str, Any]
    recovery_instructions: List[str]
    validation_commands: List[str]
    is_verified: bool = False


class SnapshotManager:
    """Manages system snapshots for rollback purposes"""
    
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Snapshot storage by type
        self.snapshots = {}
        self.snapshot_metadata = {}
        
        # Compression and deduplication
        self.enable_compression = True
        self.enable_deduplication = True
        self.file_hashes = {}  # For deduplication
    
    def create_snapshot(self, snapshot_type: SnapshotType, 
                       description: str, targets: List[str],
                       metadata: Dict[str, Any] = None) -> SystemSnapshot:
        """Create a system snapshot"""
        snapshot_id = f"{snapshot_type.value}_{int(time.time())}_{hashlib.md5(str(targets).encode()).hexdigest()[:8]}"
        timestamp = datetime.now()
        
        snapshot_data = {}
        file_paths = []
        dependencies = []
        total_size = 0
        
        try:
            if snapshot_type == SnapshotType.FILE_SYSTEM:
                snapshot_data, file_paths, total_size = self._create_file_system_snapshot(targets)
            elif snapshot_type == SnapshotType.CONFIGURATION:
                snapshot_data, file_paths, total_size = self._create_configuration_snapshot(targets)
            elif snapshot_type == SnapshotType.SERVICE_STATE:
                snapshot_data, dependencies, total_size = self._create_service_snapshot(targets)
            elif snapshot_type == SnapshotType.DATABASE:
                snapshot_data, file_paths, total_size = self._create_database_snapshot(targets)
            elif snapshot_type == SnapshotType.ENVIRONMENT:
                snapshot_data, total_size = self._create_environment_snapshot(targets)
            else:
                snapshot_data = {"custom_data": targets}
                total_size = len(json.dumps(snapshot_data).encode())
            
            # Calculate checksum
            checksum = hashlib.sha256(json.dumps(snapshot_data, sort_keys=True).encode()).hexdigest()
            
            # Create snapshot object
            snapshot = SystemSnapshot(
                snapshot_id=snapshot_id,
                timestamp=timestamp,
                hostname=os.uname().nodename if hasattr(os, 'uname') else 'localhost',
                snapshot_type=snapshot_type,
                description=description,
                snapshot_data=snapshot_data,
                file_paths=file_paths,
                dependencies=dependencies,
                size_bytes=total_size,
                checksum=checksum,
                metadata=metadata or {}
            )
            
            # Store snapshot
            self._store_snapshot(snapshot)
            
            logger.info(f"Created {snapshot_type.value} snapshot: {snapshot_id}")
            return snapshot
        
        except Exception as e:
            logger.error(f"Failed to create snapshot {snapshot_id}: {e}")
            raise
    
    def _create_file_system_snapshot(self, targets: List[str]) -> Tuple[Dict, List[str], int]:
        """Create file system snapshot"""
        snapshot_data = {}
        file_paths = []
        total_size = 0
        
        for target in targets:
            target_path = Path(target)
            
            if not target_path.exists():
                logger.warning(f"Target path does not exist: {target}")
                continue
            
            if target_path.is_file():
                # Single file
                file_info = self._capture_file_info(target_path)
                snapshot_data[str(target_path)] = file_info
                file_paths.append(str(target_path))
                total_size += file_info.get('size', 0)
            
            elif target_path.is_dir():
                # Directory tree
                for file_path in target_path.rglob('*'):
                    if file_path.is_file():
                        try:
                            file_info = self._capture_file_info(file_path)
                            snapshot_data[str(file_path)] = file_info
                            file_paths.append(str(file_path))
                            total_size += file_info.get('size', 0)
                        except Exception as e:
                            logger.warning(f"Could not snapshot file {file_path}: {e}")
        
        return snapshot_data, file_paths, total_size
    
    def _create_configuration_snapshot(self, targets: List[str]) -> Tuple[Dict, List[str], int]:
        """Create configuration snapshot"""
        config_files = [
            '/etc/nginx/nginx.conf',
            '/etc/apache2/apache2.conf',
            '/etc/mysql/my.cnf',
            '/etc/ssh/sshd_config',
            '/etc/hosts',
            '/etc/fstab',
            '/etc/crontab'
        ]
        
        # Add user-specified config files
        config_files.extend(targets)
        
        return self._create_file_system_snapshot(config_files)
    
    def _create_service_snapshot(self, service_names: List[str]) -> Tuple[Dict, List[str], int]:
        """Create service state snapshot"""
        snapshot_data = {}
        dependencies = []
        total_size = 0
        
        for service_name in service_names:
            try:
                # Get service status
                result = subprocess.run(
                    ['systemctl', 'is-active', service_name],
                    capture_output=True, text=True, timeout=10
                )
                is_active = result.returncode == 0
                
                # Get service configuration
                result = subprocess.run(
                    ['systemctl', 'show', service_name],
                    capture_output=True, text=True, timeout=10
                )
                
                service_info = {
                    'name': service_name,
                    'is_active': is_active,
                    'status_output': result.stdout,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Get service dependencies
                result = subprocess.run(
                    ['systemctl', 'list-dependencies', service_name],
                    capture_output=True, text=True, timeout=10
                )
                
                if result.returncode == 0:
                    deps = [line.strip() for line in result.stdout.split('\n') if line.strip()]
                    service_info['dependencies'] = deps
                    dependencies.extend(deps)
                
                snapshot_data[service_name] = service_info
                total_size += len(json.dumps(service_info).encode())
            
            except Exception as e:
                logger.error(f"Error snapshotting service {service_name}: {e}")
        
        return snapshot_data, dependencies, total_size
    
    def _create_database_snapshot(self, db_configs: List[str]) -> Tuple[Dict, List[str], int]:
        """Create database snapshot (placeholder - actual implementation would vary by DB type)"""
        snapshot_data = {}
        file_paths = []
        total_size = 0
        
        # This is a simplified implementation
        # In practice, you'd use database-specific backup tools
        for db_config in db_configs:
            snapshot_data[db_config] = {
                'type': 'database_dump',
                'config': db_config,
                'timestamp': datetime.now().isoformat(),
                'note': 'Database snapshot would require specific implementation for each DB type'
            }
            total_size += 1024  # Placeholder size
        
        return snapshot_data, file_paths, total_size
    
    def _create_environment_snapshot(self, env_vars: List[str]) -> Tuple[Dict, int]:
        """Create environment variable snapshot"""
        snapshot_data = {}
        
        # Capture specified environment variables
        for var_name in env_vars:
            snapshot_data[var_name] = os.environ.get(var_name, None)
        
        # Capture all environment variables if none specified
        if not env_vars:
            snapshot_data = dict(os.environ)
        
        total_size = len(json.dumps(snapshot_data).encode())
        return snapshot_data, total_size
    
    def _capture_file_info(self, file_path: Path) -> Dict[str, Any]:
        """Capture comprehensive file information"""
        stat_info = file_path.stat()
        
        file_info = {
            'path': str(file_path),
            'size': stat_info.st_size,
            'mode': stat_info.st_mode,
            'uid': stat_info.st_uid,
            'gid': stat_info.st_gid,
            'mtime': stat_info.st_mtime,
            'ctime': stat_info.st_ctime,
        }
        
        # Calculate file hash for deduplication
        if file_path.is_file() and stat_info.st_size < 10 * 1024 * 1024:  # Files under 10MB
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                    file_hash = hashlib.sha256(content).hexdigest()
                    file_info['content_hash'] = file_hash
                    
                    # Store content if deduplication is enabled
                    if self.enable_deduplication:
                        if file_hash not in self.file_hashes:
                            file_info['content'] = content.decode('utf-8', errors='ignore')
                            self.file_hashes[file_hash] = str(file_path)
                        else:
                            file_info['deduplicated'] = True
                            file_info['original_path'] = self.file_hashes[file_hash]
                    else:
                        file_info['content'] = content.decode('utf-8', errors='ignore')
            except Exception as e:
                logger.warning(f"Could not read file content for {file_path}: {e}")
        
        return file_info
    
    def _store_snapshot(self, snapshot: SystemSnapshot):
        """Store snapshot to disk"""
        snapshot_file = self.storage_path / f"{snapshot.snapshot_id}.json"
        
        try:
            # Prepare data for storage
            storage_data = {
                'snapshot_id': snapshot.snapshot_id,
                'timestamp': snapshot.timestamp.isoformat(),
                'hostname': snapshot.hostname,
                'snapshot_type': snapshot.snapshot_type.value,
                'description': snapshot.description,
                'snapshot_data': snapshot.snapshot_data,
                'file_paths': snapshot.file_paths,
                'dependencies': snapshot.dependencies,
                'size_bytes': snapshot.size_bytes,
                'checksum': snapshot.checksum,
                'metadata': snapshot.metadata
            }
            
            # Compress if enabled
            if self.enable_compression:
                import gzip
                with gzip.open(f"{snapshot_file}.gz", 'wt', encoding='utf-8') as f:
                    json.dump(storage_data, f, indent=2)
            else:
                with open(snapshot_file, 'w') as f:
                    json.dump(storage_data, f, indent=2)
            
            # Store in memory cache
            self.snapshots[snapshot.snapshot_id] = snapshot
            self.snapshot_metadata[snapshot.snapshot_id] = {
                'file_path': snapshot_file,
                'compressed': self.enable_compression,
                'created_at': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Failed to store snapshot {snapshot.snapshot_id}: {e}")
            raise
    
    def restore_snapshot(self, snapshot_id: str, 
                        restore_options: Dict[str, Any] = None) -> bool:
        """Restore system from snapshot"""
        if snapshot_id not in self.snapshots:
            snapshot = self.load_snapshot(snapshot_id)
            if not snapshot:
                logger.error(f"Snapshot {snapshot_id} not found")
                return False
        else:
            snapshot = self.snapshots[snapshot_id]
        
        options = restore_options or {}
        dry_run = options.get('dry_run', False)
        
        try:
            if snapshot.snapshot_type == SnapshotType.FILE_SYSTEM:
                return self._restore_file_system_snapshot(snapshot, options)
            elif snapshot.snapshot_type == SnapshotType.CONFIGURATION:
                return self._restore_configuration_snapshot(snapshot, options)
            elif snapshot.snapshot_type == SnapshotType.SERVICE_STATE:
                return self._restore_service_snapshot(snapshot, options)
            elif snapshot.snapshot_type == SnapshotType.ENVIRONMENT:
                return self._restore_environment_snapshot(snapshot, options)
            else:
                logger.warning(f"Restore not implemented for {snapshot.snapshot_type.value}")
                return True
        
        except Exception as e:
            logger.error(f"Failed to restore snapshot {snapshot_id}: {e}")
            return False
    
    def _restore_file_system_snapshot(self, snapshot: SystemSnapshot, 
                                    options: Dict[str, Any]) -> bool:
        """Restore file system from snapshot"""
        dry_run = options.get('dry_run', False)
        backup_existing = options.get('backup_existing', True)
        
        try:
            for file_path_str, file_info in snapshot.snapshot_data.items():
                file_path = Path(file_path_str)
                
                if dry_run:
                    logger.info(f"DRY RUN: Would restore {file_path}")
                    continue
                
                # Backup existing file if requested
                if backup_existing and file_path.exists():
                    backup_path = Path(f"{file_path}.backup_{int(time.time())}")
                    shutil.copy2(file_path, backup_path)
                    logger.info(f"Backed up existing file to {backup_path}")
                
                # Create parent directories
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Restore file content
                if 'content' in file_info:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(file_info['content'])
                elif 'deduplicated' in file_info and file_info['deduplicated']:
                    # Copy from original deduplicated file
                    original_path = Path(file_info['original_path'])
                    if original_path.exists():
                        shutil.copy2(original_path, file_path)
                
                # Restore file attributes
                try:
                    os.chmod(file_path, file_info['mode'])
                    os.chown(file_path, file_info['uid'], file_info['gid'])
                    # Note: Setting mtime/ctime requires more complex handling
                except Exception as e:
                    logger.warning(f"Could not restore all attributes for {file_path}: {e}")
            
            logger.info(f"File system snapshot {snapshot.snapshot_id} restored successfully")
            return True
        
        except Exception as e:
            logger.error(f"Error restoring file system snapshot: {e}")
            return False
    
    def _restore_service_snapshot(self, snapshot: SystemSnapshot, 
                                options: Dict[str, Any]) -> bool:
        """Restore service states from snapshot"""
        dry_run = options.get('dry_run', False)
        
        try:
            for service_name, service_info in snapshot.snapshot_data.items():
                target_state = 'active' if service_info['is_active'] else 'inactive'
                
                if dry_run:
                    logger.info(f"DRY RUN: Would set {service_name} to {target_state}")
                    continue
                
                if service_info['is_active']:
                    # Start the service
                    result = subprocess.run(
                        ['systemctl', 'start', service_name],
                        capture_output=True, text=True, timeout=30
                    )
                    if result.returncode != 0:
                        logger.error(f"Failed to start service {service_name}: {result.stderr}")
                else:
                    # Stop the service
                    result = subprocess.run(
                        ['systemctl', 'stop', service_name],
                        capture_output=True, text=True, timeout=30
                    )
                    if result.returncode != 0:
                        logger.error(f"Failed to stop service {service_name}: {result.stderr}")
            
            logger.info(f"Service snapshot {snapshot.snapshot_id} restored successfully")
            return True
        
        except Exception as e:
            logger.error(f"Error restoring service snapshot: {e}")
            return False
    
    def _restore_environment_snapshot(self, snapshot: SystemSnapshot, 
                                    options: Dict[str, Any]) -> bool:
        """Restore environment variables from snapshot"""
        dry_run = options.get('dry_run', False)
        
        try:
            for var_name, var_value in snapshot.snapshot_data.items():
                if dry_run:
                    logger.info(f"DRY RUN: Would set {var_name}={var_value}")
                    continue
                
                if var_value is not None:
                    os.environ[var_name] = var_value
                elif var_name in os.environ:
                    del os.environ[var_name]
            
            logger.info(f"Environment snapshot {snapshot.snapshot_id} restored successfully")
            return True
        
        except Exception as e:
            logger.error(f"Error restoring environment snapshot: {e}")
            return False
    
    def load_snapshot(self, snapshot_id: str) -> Optional[SystemSnapshot]:
        """Load snapshot from disk"""
        if snapshot_id in self.snapshots:
            return self.snapshots[snapshot_id]
        
        # Try to load from disk
        snapshot_file = self.storage_path / f"{snapshot_id}.json"
        compressed_file = self.storage_path / f"{snapshot_id}.json.gz"
        
        try:
            if compressed_file.exists():
                import gzip
                with gzip.open(compressed_file, 'rt', encoding='utf-8') as f:
                    data = json.load(f)
            elif snapshot_file.exists():
                with open(snapshot_file, 'r') as f:
                    data = json.load(f)
            else:
                return None
            
            # Reconstruct snapshot object
            snapshot = SystemSnapshot(
                snapshot_id=data['snapshot_id'],
                timestamp=datetime.fromisoformat(data['timestamp']),
                hostname=data['hostname'],
                snapshot_type=SnapshotType(data['snapshot_type']),
                description=data['description'],
                snapshot_data=data['snapshot_data'],
                file_paths=data['file_paths'],
                dependencies=data['dependencies'],
                size_bytes=data['size_bytes'],
                checksum=data['checksum'],
                metadata=data.get('metadata', {})
            )
            
            # Cache in memory
            self.snapshots[snapshot_id] = snapshot
            return snapshot
        
        except Exception as e:
            logger.error(f"Failed to load snapshot {snapshot_id}: {e}")
            return None
    
    def list_snapshots(self, snapshot_type: Optional[SnapshotType] = None) -> List[SystemSnapshot]:
        """List available snapshots"""
        snapshots = []
        
        # Add memory cached snapshots
        for snapshot in self.snapshots.values():
            if snapshot_type is None or snapshot.snapshot_type == snapshot_type:
                snapshots.append(snapshot)
        
        # Load snapshots from disk that aren't in memory
        for file_path in self.storage_path.glob("*.json*"):
            snapshot_id = file_path.stem.replace('.json', '')
            if snapshot_id not in self.snapshots:
                snapshot = self.load_snapshot(snapshot_id)
                if snapshot and (snapshot_type is None or snapshot.snapshot_type == snapshot_type):
                    snapshots.append(snapshot)
        
        return sorted(snapshots, key=lambda x: x.timestamp, reverse=True)
    
    def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a snapshot"""
        try:
            # Remove from memory
            if snapshot_id in self.snapshots:
                del self.snapshots[snapshot_id]
            
            if snapshot_id in self.snapshot_metadata:
                del self.snapshot_metadata[snapshot_id]
            
            # Remove from disk
            snapshot_file = self.storage_path / f"{snapshot_id}.json"
            compressed_file = self.storage_path / f"{snapshot_id}.json.gz"
            
            if compressed_file.exists():
                compressed_file.unlink()
            elif snapshot_file.exists():
                snapshot_file.unlink()
            
            logger.info(f"Deleted snapshot {snapshot_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to delete snapshot {snapshot_id}: {e}")
            return False


class RollbackDatabase:
    """Database for storing rollback operations and their history"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.lock = threading.RLock()
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS operations (
                        operation_id TEXT PRIMARY KEY,
                        description TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        completed_at TEXT,
                        status TEXT NOT NULL,
                        hostname TEXT NOT NULL,
                        user_id TEXT,
                        operation_context TEXT,
                        total_steps INTEGER DEFAULT 0,
                        completed_steps INTEGER DEFAULT 0
                    );
                    
                    CREATE TABLE IF NOT EXISTS operation_steps (
                        step_id TEXT PRIMARY KEY,
                        operation_id TEXT NOT NULL,
                        command TEXT NOT NULL,
                        description TEXT,
                        operation_type TEXT NOT NULL,
                        execution_order INTEGER NOT NULL,
                        rollback_command TEXT,
                        rollback_dependencies TEXT,
                        pre_execution_snapshot TEXT,
                        post_execution_snapshot TEXT,
                        execution_result TEXT,
                        rollback_result TEXT,
                        is_critical BOOLEAN DEFAULT FALSE,
                        auto_rollback BOOLEAN DEFAULT TRUE,
                        created_at TEXT NOT NULL,
                        executed_at TEXT,
                        rolled_back_at TEXT,
                        FOREIGN KEY (operation_id) REFERENCES operations(operation_id)
                    );
                    
                    CREATE TABLE IF NOT EXISTS rollback_operations (
                        rollback_id TEXT PRIMARY KEY,
                        operation_id TEXT NOT NULL,
                        description TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        started_at TEXT,
                        completed_at TEXT,
                        status TEXT NOT NULL,
                        recovery_mode TEXT NOT NULL,
                        steps_to_rollback TEXT,
                        success_count INTEGER DEFAULT 0,
                        failure_count INTEGER DEFAULT 0,
                        error_messages TEXT,
                        requires_manual_intervention BOOLEAN DEFAULT FALSE,
                        FOREIGN KEY (operation_id) REFERENCES operations(operation_id)
                    );
                    
                    CREATE TABLE IF NOT EXISTS recovery_points (
                        recovery_point_id TEXT PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        hostname TEXT NOT NULL,
                        description TEXT NOT NULL,
                        snapshots TEXT NOT NULL,
                        operation_context TEXT,
                        recovery_instructions TEXT,
                        validation_commands TEXT,
                        is_verified BOOLEAN DEFAULT FALSE
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_operations_created_at ON operations(created_at);
                    CREATE INDEX IF NOT EXISTS idx_steps_operation_id ON operation_steps(operation_id);
                    CREATE INDEX IF NOT EXISTS idx_rollbacks_operation_id ON rollback_operations(operation_id);
                    CREATE INDEX IF NOT EXISTS idx_recovery_points_timestamp ON recovery_points(timestamp);
                """)
                conn.commit()
            finally:
                conn.close()
    
    def store_operation_step(self, step: OperationStep):
        """Store operation step"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO operation_steps 
                    (step_id, operation_id, command, description, operation_type, 
                     execution_order, rollback_command, rollback_dependencies,
                     pre_execution_snapshot, post_execution_snapshot, execution_result,
                     rollback_result, is_critical, auto_rollback, created_at, 
                     executed_at, rolled_back_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    step.step_id,
                    step.operation_id,
                    step.command,
                    step.description,
                    step.operation_type.value,
                    step.execution_order,
                    step.rollback_command,
                    json.dumps(step.rollback_dependencies or []),
                    step.pre_execution_snapshot,
                    step.post_execution_snapshot,
                    json.dumps(step.execution_result) if step.execution_result else None,
                    json.dumps(step.rollback_result) if step.rollback_result else None,
                    step.is_critical,
                    step.auto_rollback,
                    datetime.now().isoformat(),
                    datetime.now().isoformat() if step.execution_result else None,
                    datetime.now().isoformat() if step.rollback_result else None
                ))
                conn.commit()
            finally:
                conn.close()
    
    def get_operation_steps(self, operation_id: str) -> List[OperationStep]:
        """Get all steps for an operation"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.execute("""
                    SELECT * FROM operation_steps 
                    WHERE operation_id = ? 
                    ORDER BY execution_order
                """, (operation_id,))
                
                steps = []
                for row in cursor.fetchall():
                    step = OperationStep(
                        step_id=row[0],
                        operation_id=row[1],
                        command=row[2],
                        description=row[3],
                        operation_type=OperationType(row[4]),
                        execution_order=row[5],
                        rollback_command=row[6],
                        rollback_dependencies=json.loads(row[7]) if row[7] else [],
                        pre_execution_snapshot=row[8],
                        post_execution_snapshot=row[9],
                        execution_result=json.loads(row[10]) if row[10] else None,
                        rollback_result=json.loads(row[11]) if row[11] else None,
                        is_critical=bool(row[12]),
                        auto_rollback=bool(row[13])
                    )
                    steps.append(step)
                
                return steps
            finally:
                conn.close()
    
    def store_rollback_operation(self, rollback_op: RollbackOperation):
        """Store rollback operation"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO rollback_operations 
                    (rollback_id, operation_id, description, created_at, started_at,
                     completed_at, status, recovery_mode, steps_to_rollback,
                     success_count, failure_count, error_messages, requires_manual_intervention)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rollback_op.rollback_id,
                    rollback_op.operation_id,
                    rollback_op.description,
                    rollback_op.created_at.isoformat(),
                    rollback_op.started_at.isoformat() if rollback_op.started_at else None,
                    rollback_op.completed_at.isoformat() if rollback_op.completed_at else None,
                    rollback_op.status.value,
                    rollback_op.recovery_mode.value,
                    json.dumps(rollback_op.steps_to_rollback or []),
                    rollback_op.success_count,
                    rollback_op.failure_count,
                    json.dumps(rollback_op.error_messages or []),
                    rollback_op.requires_manual_intervention
                ))
                conn.commit()
            finally:
                conn.close()


class RollbackManager:
    """
    Main Enhanced Command Rollback System that provides comprehensive
    rollback and recovery mechanisms for complex multi-step operations.
    """
    
    def __init__(self, storage_path: str = None, db_path: str = None):
        """Initialize rollback manager"""
        self.storage_path = storage_path or "rollback_storage"
        self.db_path = db_path or "rollback_operations.db"
        
        # Components
        self.snapshot_manager = SnapshotManager(self.storage_path)
        self.database = RollbackDatabase(self.db_path)
        
        # State management
        self.active_operations = {}  # operation_id -> list of steps
        self.rollback_operations = {}  # rollback_id -> RollbackOperation
        
        # Recovery points
        self.recovery_points = {}
        
        # Configuration
        self.auto_snapshot_enabled = True
        self.max_rollback_depth = 50  # Maximum number of steps to rollback
        self.cleanup_after_days = 30   # Clean up old snapshots after N days
        
        # Callbacks
        self.rollback_callbacks = []
        self.recovery_callbacks = []
        
        logger.info("Enhanced Command Rollback System initialized")
    
    def start_operation(self, operation_id: str, description: str,
                       context: Dict[str, Any] = None) -> bool:
        """Start tracking a new operation for potential rollback"""
        if operation_id in self.active_operations:
            logger.warning(f"Operation {operation_id} is already active")
            return False
        
        self.active_operations[operation_id] = []
        
        # Create initial recovery point if auto-snapshot is enabled
        if self.auto_snapshot_enabled:
            try:
                recovery_point = self.create_recovery_point(
                    description=f"Pre-operation snapshot for {description}",
                    operation_context=context or {}
                )
                logger.info(f"Created recovery point {recovery_point.recovery_point_id} for operation {operation_id}")
            except Exception as e:
                logger.warning(f"Could not create initial recovery point: {e}")
        
        logger.info(f"Started tracking operation: {operation_id}")
        return True
    
    def add_operation_step(self, operation_id: str, command: str, 
                          description: str, operation_type: OperationType,
                          rollback_command: str = None, 
                          is_critical: bool = False,
                          auto_rollback: bool = True,
                          rollback_dependencies: List[str] = None) -> OperationStep:
        """Add a step to an active operation"""
        if operation_id not in self.active_operations:
            raise ValueError(f"Operation {operation_id} is not active")
        
        step_id = f"{operation_id}_step_{len(self.active_operations[operation_id]) + 1}"
        execution_order = len(self.active_operations[operation_id]) + 1
        
        # Create pre-execution snapshot if auto-snapshot is enabled
        pre_snapshot_id = None
        if self.auto_snapshot_enabled and operation_type in [
            OperationType.FILE_OPERATION, 
            OperationType.CONFIGURATION_CHANGE
        ]:
            try:
                snapshot = self.snapshot_manager.create_snapshot(
                    snapshot_type=SnapshotType.FILE_SYSTEM,
                    description=f"Pre-execution snapshot for {description}",
                    targets=self._extract_targets_from_command(command)
                )
                pre_snapshot_id = snapshot.snapshot_id
            except Exception as e:
                logger.warning(f"Could not create pre-execution snapshot: {e}")
        
        step = OperationStep(
            step_id=step_id,
            operation_id=operation_id,
            command=command,
            description=description,
            operation_type=operation_type,
            execution_order=execution_order,
            rollback_command=rollback_command,
            rollback_dependencies=rollback_dependencies or [],
            pre_execution_snapshot=pre_snapshot_id,
            is_critical=is_critical,
            auto_rollback=auto_rollback
        )
        
        self.active_operations[operation_id].append(step)
        self.database.store_operation_step(step)
        
        logger.debug(f"Added step {step_id} to operation {operation_id}")
        return step
    
    def execute_step(self, step: OperationStep, dry_run: bool = False) -> Dict[str, Any]:
        """Execute a single operation step"""
        execution_result = {
            'step_id': step.step_id,
            'command': step.command,
            'start_time': datetime.now(),
            'success': False,
            'output': '',
            'error': '',
            'exit_code': None,
            'dry_run': dry_run
        }
        
        try:
            if dry_run:
                logger.info(f"DRY RUN: Would execute {step.command}")
                execution_result['success'] = True
                execution_result['output'] = f"DRY RUN: {step.description}"
            else:
                # Execute the command
                result = subprocess.run(
                    step.command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                
                execution_result['output'] = result.stdout
                execution_result['error'] = result.stderr
                execution_result['exit_code'] = result.returncode
                execution_result['success'] = result.returncode == 0
                
                # Create post-execution snapshot if needed
                if (self.auto_snapshot_enabled and 
                    execution_result['success'] and 
                    step.operation_type in [OperationType.FILE_OPERATION, OperationType.CONFIGURATION_CHANGE]):
                    try:
                        snapshot = self.snapshot_manager.create_snapshot(
                            snapshot_type=SnapshotType.FILE_SYSTEM,
                            description=f"Post-execution snapshot for {step.description}",
                            targets=self._extract_targets_from_command(step.command)
                        )
                        step.post_execution_snapshot = snapshot.snapshot_id
                    except Exception as e:
                        logger.warning(f"Could not create post-execution snapshot: {e}")
            
            execution_result['end_time'] = datetime.now()
            execution_result['duration'] = (
                execution_result['end_time'] - execution_result['start_time']
            ).total_seconds()
            
            # Store execution result
            step.execution_result = execution_result
            self.database.store_operation_step(step)
            
        except subprocess.TimeoutExpired:
            execution_result['error'] = "Command execution timed out"
            logger.error(f"Step {step.step_id} timed out")
        except Exception as e:
            execution_result['error'] = str(e)
            logger.error(f"Error executing step {step.step_id}: {e}")
        
        return execution_result
    
    def complete_operation(self, operation_id: str, success: bool = True):
        """Mark an operation as completed"""
        if operation_id not in self.active_operations:
            logger.warning(f"Operation {operation_id} is not active")
            return
        
        steps = self.active_operations[operation_id]
        
        # Create final recovery point if auto-snapshot is enabled
        if self.auto_snapshot_enabled and success:
            try:
                recovery_point = self.create_recovery_point(
                    description=f"Post-operation snapshot for {operation_id}",
                    operation_context={'operation_id': operation_id, 'completed': True}
                )
                logger.info(f"Created final recovery point {recovery_point.recovery_point_id}")
            except Exception as e:
                logger.warning(f"Could not create final recovery point: {e}")
        
        # Move to completed operations (remove from active)
        del self.active_operations[operation_id]
        
        logger.info(f"Completed operation {operation_id} with {len(steps)} steps (success: {success})")
    
    def rollback_operation(self, operation_id: str, 
                          recovery_mode: RecoveryMode = RecoveryMode.AUTOMATIC,
                          target_step: Optional[str] = None,
                          dry_run: bool = False) -> RollbackOperation:
        """Rollback an operation"""
        rollback_id = f"rollback_{operation_id}_{int(time.time())}"
        
        # Get operation steps
        steps = self.database.get_operation_steps(operation_id)
        if not steps:
            raise ValueError(f"No steps found for operation {operation_id}")
        
        # Determine steps to rollback
        if target_step:
            # Rollback to specific step
            target_order = None
            for step in steps:
                if step.step_id == target_step:
                    target_order = step.execution_order
                    break
            
            if target_order is None:
                raise ValueError(f"Target step {target_step} not found")
            
            steps_to_rollback = [s for s in steps if s.execution_order > target_order]
        else:
            # Rollback all executed steps
            steps_to_rollback = [s for s in steps if s.execution_result is not None]
        
        # Sort by execution order (reverse for rollback)
        steps_to_rollback.sort(key=lambda x: x.execution_order, reverse=True)
        
        # Create rollback operation
        rollback_op = RollbackOperation(
            rollback_id=rollback_id,
            operation_id=operation_id,
            description=f"Rollback operation {operation_id}",
            created_at=datetime.now(),
            recovery_mode=recovery_mode,
            steps_to_rollback=[s.step_id for s in steps_to_rollback],
            rollback_steps=steps_to_rollback
        )
        
        # Store rollback operation
        self.rollback_operations[rollback_id] = rollback_op
        
        # Execute rollback
        if not dry_run:
            self._execute_rollback(rollback_op, dry_run=False)
        else:
            logger.info(f"DRY RUN: Would rollback {len(steps_to_rollback)} steps")
        
        return rollback_op
    
    def _execute_rollback(self, rollback_op: RollbackOperation, dry_run: bool = False):
        """Execute the rollback operation"""
        rollback_op.status = RollbackStatus.IN_PROGRESS
        rollback_op.started_at = datetime.now()
        
        try:
            for step in rollback_op.rollback_steps:
                try:
                    rollback_result = self._rollback_step(step, dry_run)
                    
                    if rollback_result['success']:
                        rollback_op.success_count += 1
                    else:
                        rollback_op.failure_count += 1
                        if rollback_op.error_messages is None:
                            rollback_op.error_messages = []
                        rollback_op.error_messages.append(
                            f"Step {step.step_id}: {rollback_result.get('error', 'Unknown error')}"
                        )
                    
                    # Check if manual intervention is needed
                    if not rollback_result['success'] and step.is_critical:
                        rollback_op.requires_manual_intervention = True
                        logger.warning(f"Critical step {step.step_id} rollback failed - manual intervention required")
                
                except Exception as e:
                    rollback_op.failure_count += 1
                    if rollback_op.error_messages is None:
                        rollback_op.error_messages = []
                    rollback_op.error_messages.append(f"Step {step.step_id}: {str(e)}")
                    logger.error(f"Error rolling back step {step.step_id}: {e}")
            
            # Determine final status
            if rollback_op.failure_count == 0:
                rollback_op.status = RollbackStatus.COMPLETED
            elif rollback_op.success_count > 0:
                rollback_op.status = RollbackStatus.PARTIAL
            else:
                rollback_op.status = RollbackStatus.FAILED
            
        except Exception as e:
            rollback_op.status = RollbackStatus.FAILED
            logger.error(f"Rollback operation {rollback_op.rollback_id} failed: {e}")
        
        finally:
            rollback_op.completed_at = datetime.now()
            self.database.store_rollback_operation(rollback_op)
            
            # Notify callbacks
            for callback in self.rollback_callbacks:
                try:
                    callback(rollback_op)
                except Exception as e:
                    logger.error(f"Rollback callback failed: {e}")
    
    def _rollback_step(self, step: OperationStep, dry_run: bool = False) -> Dict[str, Any]:
        """Rollback a single step"""
        rollback_result = {
            'step_id': step.step_id,
            'start_time': datetime.now(),
            'success': False,
            'output': '',
            'error': '',
            'method': 'unknown',
            'dry_run': dry_run
        }
        
        try:
            # Try different rollback methods in order of preference
            
            # 1. Use explicit rollback command
            if step.rollback_command:
                rollback_result['method'] = 'command'
                
                if dry_run:
                    logger.info(f"DRY RUN: Would execute rollback command {step.rollback_command}")
                    rollback_result['success'] = True
                    rollback_result['output'] = f"DRY RUN: {step.rollback_command}"
                else:
                    result = subprocess.run(
                        step.rollback_command,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                    
                    rollback_result['output'] = result.stdout
                    rollback_result['error'] = result.stderr
                    rollback_result['success'] = result.returncode == 0
            
            # 2. Use pre-execution snapshot
            elif step.pre_execution_snapshot:
                rollback_result['method'] = 'snapshot'
                
                if dry_run:
                    logger.info(f"DRY RUN: Would restore snapshot {step.pre_execution_snapshot}")
                    rollback_result['success'] = True
                    rollback_result['output'] = f"DRY RUN: Restore snapshot {step.pre_execution_snapshot}"
                else:
                    success = self.snapshot_manager.restore_snapshot(
                        step.pre_execution_snapshot,
                        {'dry_run': False, 'backup_existing': True}
                    )
                    rollback_result['success'] = success
                    if success:
                        rollback_result['output'] = f"Restored snapshot {step.pre_execution_snapshot}"
                    else:
                        rollback_result['error'] = f"Failed to restore snapshot {step.pre_execution_snapshot}"
            
            # 3. Try automatic rollback based on command type
            else:
                rollback_result['method'] = 'automatic'
                auto_rollback_cmd = self._generate_auto_rollback_command(step)
                
                if auto_rollback_cmd:
                    if dry_run:
                        logger.info(f"DRY RUN: Would execute auto-rollback {auto_rollback_cmd}")
                        rollback_result['success'] = True
                        rollback_result['output'] = f"DRY RUN: {auto_rollback_cmd}"
                    else:
                        result = subprocess.run(
                            auto_rollback_cmd,
                            shell=True,
                            capture_output=True,
                            text=True,
                            timeout=300
                        )
                        
                        rollback_result['output'] = result.stdout
                        rollback_result['error'] = result.stderr
                        rollback_result['success'] = result.returncode == 0
                else:
                    rollback_result['error'] = "No rollback method available"
            
        except Exception as e:
            rollback_result['error'] = str(e)
            logger.error(f"Error rolling back step {step.step_id}: {e}")
        
        finally:
            rollback_result['end_time'] = datetime.now()
            rollback_result['duration'] = (
                rollback_result['end_time'] - rollback_result['start_time']
            ).total_seconds()
            
            # Store rollback result
            step.rollback_result = rollback_result
            self.database.store_operation_step(step)
        
        return rollback_result
    
    def _generate_auto_rollback_command(self, step: OperationStep) -> Optional[str]:
        """Generate automatic rollback command based on operation type and command"""
        command = step.command.strip().lower()
        
        # File operations
        if command.startswith('cp ') or command.startswith('copy '):
            # For copy operations, try to remove the destination
            parts = step.command.split()
            if len(parts) >= 3:
                dest = parts[-1]
                return f"rm -rf {dest}"
        
        elif command.startswith('mv ') or command.startswith('move '):
            # For move operations, try to move back
            parts = step.command.split()
            if len(parts) >= 3:
                source, dest = parts[-2], parts[-1]
                return f"mv {dest} {source}"
        
        elif command.startswith('rm ') or command.startswith('del '):
            # Cannot easily rollback delete operations without backup
            return None
        
        elif command.startswith('mkdir '):
            # Remove created directory
            parts = step.command.split()
            if len(parts) >= 2:
                dir_path = parts[1]
                return f"rmdir {dir_path}"
        
        # Service operations
        elif 'systemctl start' in command:
            return command.replace('start', 'stop')
        elif 'systemctl stop' in command:
            return command.replace('stop', 'start')
        elif 'systemctl enable' in command:
            return command.replace('enable', 'disable')
        elif 'systemctl disable' in command:
            return command.replace('disable', 'enable')
        
        # Package operations
        elif command.startswith('apt install') or command.startswith('yum install'):
            # Convert install to remove
            return command.replace('install', 'remove')
        elif command.startswith('pip install'):
            package = command.replace('pip install', '').strip()
            return f"pip uninstall -y {package}"
        
        return None
    
    def _extract_targets_from_command(self, command: str) -> List[str]:
        """Extract file/directory targets from command for snapshotting"""
        # Simple extraction - could be enhanced with more sophisticated parsing
        targets = []
        
        if any(cmd in command.lower() for cmd in ['cp', 'mv', 'copy', 'move']):
            # Extract source and destination
            parts = command.split()
            if len(parts) >= 3:
                targets.extend(parts[1:-1])  # All but first (command) and last might be sources
                targets.append(parts[-1])    # Last is usually destination
        
        elif 'systemctl' in command:
            # For service operations, we might want to snapshot config files
            targets.extend(['/etc/systemd/system/', '/lib/systemd/system/'])
        
        elif any(cmd in command.lower() for cmd in ['apt', 'yum', 'dnf']):
            # For package operations, snapshot package database
            targets.extend(['/var/lib/dpkg/', '/var/lib/rpm/'])
        
        # Filter out non-existent paths
        return [target for target in targets if Path(target).exists()]
    
    def create_recovery_point(self, description: str, 
                            operation_context: Dict[str, Any] = None) -> RecoveryPoint:
        """Create a comprehensive recovery point"""
        recovery_point_id = f"recovery_{int(time.time())}_{hashlib.md5(description.encode()).hexdigest()[:8]}"
        
        snapshots = []
        
        try:
            # Create multiple types of snapshots
            snapshot_types = [
                (SnapshotType.CONFIGURATION, ['/etc'], 'System configuration'),
                (SnapshotType.SERVICE_STATE, ['ssh', 'cron', 'systemd-resolved'], 'Critical services'),
                (SnapshotType.ENVIRONMENT, [], 'Environment variables')
            ]
            
            for snapshot_type, targets, desc in snapshot_types:
                try:
                    snapshot = self.snapshot_manager.create_snapshot(
                        snapshot_type=snapshot_type,
                        description=f"{desc} - {description}",
                        targets=targets
                    )
                    snapshots.append(snapshot.snapshot_id)
                except Exception as e:
                    logger.warning(f"Failed to create {snapshot_type.value} snapshot: {e}")
            
            # Create recovery point
            recovery_point = RecoveryPoint(
                recovery_point_id=recovery_point_id,
                timestamp=datetime.now(),
                hostname=os.uname().nodename if hasattr(os, 'uname') else 'localhost',
                description=description,
                snapshots=snapshots,
                operation_context=operation_context or {},
                recovery_instructions=[
                    "1. Stop all related services",
                    "2. Restore snapshots in reverse chronological order",
                    "3. Restart services",
                    "4. Validate system state"
                ],
                validation_commands=[
                    "systemctl status",
                    "df -h",
                    "ps aux | head -20"
                ]
            )
            
            # Store recovery point
            self.recovery_points[recovery_point_id] = recovery_point
            
            logger.info(f"Created recovery point {recovery_point_id} with {len(snapshots)} snapshots")
            return recovery_point
        
        except Exception as e:
            logger.error(f"Failed to create recovery point: {e}")
            raise
    
    def restore_to_recovery_point(self, recovery_point_id: str, 
                                dry_run: bool = False) -> bool:
        """Restore system to a recovery point"""
        if recovery_point_id not in self.recovery_points:
            logger.error(f"Recovery point {recovery_point_id} not found")
            return False
        
        recovery_point = self.recovery_points[recovery_point_id]
        
        try:
            if dry_run:
                logger.info(f"DRY RUN: Would restore to recovery point {recovery_point_id}")
                return True
            
            # Restore snapshots in reverse chronological order
            success_count = 0
            total_snapshots = len(recovery_point.snapshots)
            
            for snapshot_id in reversed(recovery_point.snapshots):
                try:
                    if self.snapshot_manager.restore_snapshot(snapshot_id):
                        success_count += 1
                        logger.info(f"Restored snapshot {snapshot_id}")
                    else:
                        logger.error(f"Failed to restore snapshot {snapshot_id}")
                except Exception as e:
                    logger.error(f"Error restoring snapshot {snapshot_id}: {e}")
            
            # Validate recovery
            if success_count == total_snapshots:
                recovery_point.is_verified = True
                logger.info(f"Successfully restored to recovery point {recovery_point_id}")
                
                # Notify callbacks
                for callback in self.recovery_callbacks:
                    try:
                        callback(recovery_point)
                    except Exception as e:
                        logger.error(f"Recovery callback failed: {e}")
                
                return True
            else:
                logger.warning(f"Partial recovery: {success_count}/{total_snapshots} snapshots restored")
                return False
        
        except Exception as e:
            logger.error(f"Error restoring to recovery point {recovery_point_id}: {e}")
            return False
    
    def get_operation_status(self, operation_id: str) -> Dict[str, Any]:
        """Get status of an operation"""
        steps = self.database.get_operation_steps(operation_id)
        
        status = {
            'operation_id': operation_id,
            'total_steps': len(steps),
            'executed_steps': len([s for s in steps if s.execution_result]),
            'successful_steps': len([s for s in steps if s.execution_result and s.execution_result.get('success')]),
            'failed_steps': len([s for s in steps if s.execution_result and not s.execution_result.get('success')]),
            'rollback_ready': all(s.rollback_command or s.pre_execution_snapshot for s in steps),
            'has_critical_steps': any(s.is_critical for s in steps),
            'steps': [
                {
                    'step_id': s.step_id,
                    'description': s.description,
                    'executed': s.execution_result is not None,
                    'success': s.execution_result.get('success') if s.execution_result else None,
                    'rollback_available': bool(s.rollback_command or s.pre_execution_snapshot)
                }
                for s in steps
            ]
        }
        
        return status
    
    def cleanup_old_data(self, older_than_days: int = None):
        """Clean up old snapshots and rollback data"""
        cutoff_days = older_than_days or self.cleanup_after_days
        cutoff_date = datetime.now() - timedelta(days=cutoff_days)
        
        cleaned_snapshots = 0
        cleaned_recovery_points = 0
        
        # Clean up old snapshots
        snapshots = self.snapshot_manager.list_snapshots()
        for snapshot in snapshots:
            if snapshot.timestamp < cutoff_date:
                if self.snapshot_manager.delete_snapshot(snapshot.snapshot_id):
                    cleaned_snapshots += 1
        
        # Clean up old recovery points
        to_remove = []
        for rp_id, recovery_point in self.recovery_points.items():
            if recovery_point.timestamp < cutoff_date:
                to_remove.append(rp_id)
        
        for rp_id in to_remove:
            del self.recovery_points[rp_id]
            cleaned_recovery_points += 1
        
        logger.info(f"Cleanup completed: removed {cleaned_snapshots} snapshots and {cleaned_recovery_points} recovery points")
    
    def add_rollback_callback(self, callback: Callable[[RollbackOperation], None]):
        """Add callback for rollback operations"""
        self.rollback_callbacks.append(callback)
    
    def add_recovery_callback(self, callback: Callable[[RecoveryPoint], None]):
        """Add callback for recovery operations"""
        self.recovery_callbacks.append(callback)
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall rollback system status"""
        snapshots = self.snapshot_manager.list_snapshots()
        
        return {
            'active_operations': len(self.active_operations),
            'total_snapshots': len(snapshots),
            'recovery_points': len(self.recovery_points),
            'rollback_operations': len(self.rollback_operations),
            'auto_snapshot_enabled': self.auto_snapshot_enabled,
            'storage_path': str(self.storage_path),
            'cleanup_after_days': self.cleanup_after_days,
            'snapshots_by_type': {
                snap_type.value: len([s for s in snapshots if s.snapshot_type == snap_type])
                for snap_type in SnapshotType
            }
        }
    
    def cleanup(self):
        """Cleanup resources"""
        # Complete any active operations
        for operation_id in list(self.active_operations.keys()):
            self.complete_operation(operation_id, success=False)
        
        logger.info("Enhanced Command Rollback System cleanup completed")