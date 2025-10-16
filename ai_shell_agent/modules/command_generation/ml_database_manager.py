"""
Enhanced ML Database Manager

Comprehensive database management for ML risk scoring with advanced
analytics, data validation, and automatic data collection integration.
"""

import sqlite3
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MLDatabaseManager:
    """
    Enhanced database manager for ML risk scoring system.
    
    Handles data collection, storage, validation, and analytics for
    command execution learning. Provides comprehensive data management
    for the ML pipeline.
    """
    
    def __init__(self, db_path: str = "data/ml_risk_database.db"):
        """Initialize database manager with enhanced schema"""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_enhanced_database()
    
    def init_enhanced_database(self):
        """Initialize enhanced database schema with comprehensive tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Command executions table (enhanced)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS command_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_id TEXT DEFAULT 'unknown',
                host_info TEXT NOT NULL,
                command TEXT NOT NULL,
                command_hash TEXT NOT NULL,
                initial_risk_level TEXT NOT NULL,
                initial_risk_score REAL NOT NULL,
                ml_risk_level TEXT,
                ml_confidence REAL,
                user_confirmed BOOLEAN NOT NULL,
                confirmation_time_ms INTEGER,
                execution_success BOOLEAN NOT NULL,
                execution_time_ms INTEGER,
                exit_code INTEGER,
                stdout_length INTEGER DEFAULT 0,
                stderr_length INTEGER DEFAULT 0,
                actual_impact TEXT NOT NULL,
                impact_details TEXT,
                system_context TEXT NOT NULL,
                system_load_1min REAL,
                system_load_5min REAL,
                memory_usage_percent REAL,
                disk_usage_percent REAL,
                network_active BOOLEAN DEFAULT FALSE,
                timestamp TEXT NOT NULL,
                user_feedback TEXT,
                feedback_rating INTEGER CHECK(feedback_rating >= 1 AND feedback_rating <= 5),
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Command patterns table for frequent commands
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS command_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_hash TEXT UNIQUE NOT NULL,
                base_command TEXT NOT NULL,
                frequency INTEGER DEFAULT 1,
                success_rate REAL DEFAULT 0.0,
                avg_risk_score REAL DEFAULT 0.0,
                common_contexts TEXT,
                last_seen TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Model training sessions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS training_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_version TEXT NOT NULL,
                training_start TEXT NOT NULL,
                training_end TEXT,
                sample_size INTEGER NOT NULL,
                train_size INTEGER,
                test_size INTEGER,
                accuracy REAL,
                precision_score REAL,
                recall_score REAL,
                f1_score REAL,
                feature_count INTEGER,
                training_config TEXT,
                status TEXT DEFAULT 'running',
                error_message TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # User behavior analytics
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_behavior (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                behavior_type TEXT NOT NULL,
                risk_tolerance TEXT,
                avg_confirmation_time_ms REAL,
                command_frequency INTEGER DEFAULT 1,
                preferred_tools TEXT,
                os_preference TEXT,
                date_analyzed TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # System contexts for better feature engineering
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_contexts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                context_hash TEXT UNIQUE NOT NULL,
                os_distribution TEXT,
                os_version TEXT,
                architecture TEXT,
                package_managers TEXT,
                service_manager TEXT,
                shell_type TEXT,
                python_version TEXT,
                available_tools TEXT,
                security_features TEXT,
                last_profiled TEXT NOT NULL,
                profile_confidence REAL DEFAULT 0.0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cmd_timestamp ON command_executions(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cmd_hash ON command_executions(command_hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_session_id ON command_executions(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON command_executions(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_host_info ON command_executions(host_info)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pattern_hash ON command_patterns(pattern_hash)')
        
        conn.commit()
        conn.close()
        logger.info(f"Enhanced ML database initialized at {self.db_path}")
    
    def record_command_execution(self, execution_data: Dict) -> int:
        """
        Record comprehensive command execution data
        
        Args:
            execution_data: Dictionary containing all execution details
            
        Returns:
            int: ID of inserted record
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Generate command hash for pattern recognition
            command_hash = self._generate_command_hash(execution_data['command'])
            
            cursor.execute('''
                INSERT INTO command_executions (
                    session_id, user_id, host_info, command, command_hash,
                    initial_risk_level, initial_risk_score, ml_risk_level, ml_confidence,
                    user_confirmed, confirmation_time_ms, execution_success, execution_time_ms,
                    exit_code, stdout_length, stderr_length, actual_impact, impact_details,
                    system_context, system_load_1min, system_load_5min, memory_usage_percent,
                    disk_usage_percent, network_active, timestamp, user_feedback, feedback_rating
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                execution_data.get('session_id', 'unknown'),
                execution_data.get('user_id', 'unknown'),
                json.dumps(execution_data.get('host_info', {})),
                execution_data['command'],
                command_hash,
                execution_data['initial_risk_level'],
                execution_data.get('initial_risk_score', 0.0),
                execution_data.get('ml_risk_level'),
                execution_data.get('ml_confidence'),
                execution_data['user_confirmed'],
                execution_data.get('confirmation_time_ms', 0),
                execution_data['execution_success'],
                execution_data.get('execution_time_ms', 0),
                execution_data.get('exit_code', 0),
                execution_data.get('stdout_length', 0),
                execution_data.get('stderr_length', 0),
                execution_data['actual_impact'],
                execution_data.get('impact_details'),
                json.dumps(execution_data.get('system_context', {})),
                execution_data.get('system_load_1min'),
                execution_data.get('system_load_5min'),
                execution_data.get('memory_usage_percent'),
                execution_data.get('disk_usage_percent'),
                execution_data.get('network_active', False),
                execution_data.get('timestamp', datetime.now().isoformat()),
                execution_data.get('user_feedback'),
                execution_data.get('feedback_rating')
            ))
            
            record_id = cursor.lastrowid
            
            # Update command patterns
            self._update_command_pattern(cursor, execution_data)
            
            conn.commit()
            logger.info(f"Recorded command execution with ID: {record_id}")
            return record_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to record command execution: {e}")
            raise
        finally:
            conn.close()
    
    def get_training_dataset(self, days_back: int = 90, min_samples: int = 10) -> pd.DataFrame:
        """
        Get comprehensive training dataset as pandas DataFrame
        
        Args:
            days_back: Number of days to look back for training data
            min_samples: Minimum samples required
            
        Returns:
            pandas.DataFrame: Training dataset with features and labels
        """
        conn = sqlite3.connect(self.db_path)
        
        cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
        
        query = '''
            SELECT 
                id, command, command_hash, initial_risk_level, initial_risk_score,
                ml_risk_level, ml_confidence, user_confirmed, execution_success,
                execution_time_ms, actual_impact, system_context, system_load_1min,
                system_load_5min, memory_usage_percent, disk_usage_percent,
                timestamp, feedback_rating, host_info
            FROM command_executions 
            WHERE timestamp > ? AND actual_impact IS NOT NULL
            ORDER BY timestamp DESC
        '''
        
        df = pd.read_sql_query(query, conn, params=(cutoff_date,))
        conn.close()
        
        if len(df) < min_samples:
            logger.warning(f"Insufficient training data: {len(df)} samples (minimum: {min_samples})")
        
        return df
    
    def get_analytics_summary(self, days_back: int = 30) -> Dict:
        """Get comprehensive analytics summary"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
        
        # Total commands executed
        cursor.execute('SELECT COUNT(*) FROM command_executions WHERE timestamp > ?', (cutoff_date,))
        total_commands = cursor.fetchone()[0]
        
        # Success rate
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN execution_success = 1 THEN 1 ELSE 0 END) as successful
            FROM command_executions WHERE timestamp > ?
        ''', (cutoff_date,))
        result = cursor.fetchone()
        success_rate = (result[1] / result[0]) if result[0] > 0 else 0
        
        # Risk level distribution
        cursor.execute('''
            SELECT initial_risk_level, COUNT(*) 
            FROM command_executions 
            WHERE timestamp > ?
            GROUP BY initial_risk_level
        ''', (cutoff_date,))
        risk_distribution = dict(cursor.fetchall())
        
        # User confirmation patterns
        cursor.execute('''
            SELECT 
                initial_risk_level,
                AVG(CASE WHEN user_confirmed = 1 THEN 1.0 ELSE 0.0 END) as confirmation_rate,
                AVG(confirmation_time_ms) as avg_confirmation_time
            FROM command_executions 
            WHERE timestamp > ?
            GROUP BY initial_risk_level
        ''', (cutoff_date,))
        confirmation_patterns = {}
        for row in cursor.fetchall():
            confirmation_patterns[row[0]] = {
                'confirmation_rate': row[1],
                'avg_confirmation_time_ms': row[2]
            }
        
        # Most common commands
        cursor.execute('''
            SELECT base_command, frequency, success_rate 
            FROM command_patterns 
            ORDER BY frequency DESC 
            LIMIT 10
        ''')
        common_commands = [{'command': row[0], 'frequency': row[1], 'success_rate': row[2]} 
                          for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            'period_days': days_back,
            'total_commands': total_commands,
            'success_rate': success_rate,
            'risk_distribution': risk_distribution,
            'confirmation_patterns': confirmation_patterns,
            'common_commands': common_commands,
            'generated_at': datetime.now().isoformat()
        }
    
    def _generate_command_hash(self, command: str) -> str:
        """Generate hash for command pattern recognition"""
        import hashlib
        
        # Normalize command for pattern recognition
        normalized = ' '.join(command.split())  # Normalize whitespace
        normalized = normalized.lower()
        
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _update_command_pattern(self, cursor, execution_data: Dict):
        """Update command pattern statistics"""
        command_hash = self._generate_command_hash(execution_data['command'])
        base_command = execution_data['command'].split()[0] if execution_data['command'].split() else ''
        
        # Check if pattern exists
        cursor.execute('SELECT id, frequency, success_rate FROM command_patterns WHERE pattern_hash = ?', 
                      (command_hash,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing pattern
            pattern_id, frequency, old_success_rate = existing
            new_frequency = frequency + 1
            
            # Calculate new success rate
            if execution_data['execution_success']:
                new_success_rate = (old_success_rate * frequency + 1) / new_frequency
            else:
                new_success_rate = (old_success_rate * frequency) / new_frequency
            
            cursor.execute('''
                UPDATE command_patterns 
                SET frequency = ?, success_rate = ?, last_seen = ?
                WHERE id = ?
            ''', (new_frequency, new_success_rate, datetime.now().isoformat(), pattern_id))
        else:
            # Create new pattern
            success_rate = 1.0 if execution_data['execution_success'] else 0.0
            cursor.execute('''
                INSERT INTO command_patterns 
                (pattern_hash, base_command, frequency, success_rate, last_seen)
                VALUES (?, ?, 1, ?, ?)
            ''', (command_hash, base_command, success_rate, datetime.now().isoformat()))
    
    def export_training_data(self, output_path: str, format: str = 'csv', days_back: int = 180):
        """Export training data for external analysis"""
        df = self.get_training_dataset(days_back=days_back, min_samples=1)
        
        if format.lower() == 'csv':
            df.to_csv(output_path, index=False)
        elif format.lower() == 'json':
            df.to_json(output_path, orient='records', indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        logger.info(f"Exported {len(df)} records to {output_path}")
    
    def cleanup_old_data(self, keep_days: int = 365):
        """Clean up old training data to manage database size"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=keep_days)).isoformat()
        
        cursor.execute('DELETE FROM command_executions WHERE timestamp < ?', (cutoff_date,))
        deleted_count = cursor.rowcount
        
        # Clean up orphaned patterns
        cursor.execute('DELETE FROM command_patterns WHERE last_seen < ?', (cutoff_date,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Cleaned up {deleted_count} old records")
        return deleted_count