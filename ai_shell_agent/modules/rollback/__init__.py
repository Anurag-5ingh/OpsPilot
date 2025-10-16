"""
Enhanced Command Rollback Module

Comprehensive rollback and recovery mechanisms that can automatically reverse failed
operations, maintain system snapshots, and provide granular recovery options for
complex multi-step operations.
"""

from .rollback_manager import (
    RollbackManager,
    SnapshotManager,
    RollbackDatabase,
    SystemSnapshot,
    OperationStep,
    RollbackOperation,
    RecoveryPoint,
    RollbackStatus,
    SnapshotType,
    RecoveryMode,
    OperationType
)

__all__ = [
    'RollbackManager',
    'SnapshotManager',
    'RollbackDatabase',
    'SystemSnapshot',
    'OperationStep',
    'RollbackOperation',
    'RecoveryPoint',
    'RollbackStatus',
    'SnapshotType',
    'RecoveryMode',
    'OperationType'
]

__version__ = "1.0.0"