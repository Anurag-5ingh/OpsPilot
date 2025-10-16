"""
Automatic Data Collection Middleware

Seamlessly integrates with the command execution pipeline to automatically
collect training data for ML risk scoring without requiring manual intervention.
"""

import time
import uuid
from datetime import datetime
from typing import Dict, Optional, Any
from .ml_database_manager import MLDatabaseManager
import logging

logger = logging.getLogger(__name__)


class CommandExecutionCollector:
    """
    Automatic data collection for command executions.
    
    This class acts as middleware in the command execution pipeline,
    automatically collecting and storing data for ML training.
    """
    
    def __init__(self, db_manager: Optional[MLDatabaseManager] = None):
        """Initialize with optional database manager"""
        self.db_manager = db_manager or MLDatabaseManager()
        self.active_sessions = {}  # Track active command sessions
    
    def start_command_session(self, command: str, risk_analysis: Dict, 
                            system_context: Dict, user_id: str = "unknown") -> str:
        """
        Start tracking a command execution session
        
        Args:
            command: The command being executed
            risk_analysis: Initial risk analysis from ML/rule-based system
            system_context: Current system context
            user_id: User identifier
            
        Returns:
            session_id: Unique session identifier
        """
        session_id = str(uuid.uuid4())
        
        session_data = {
            'session_id': session_id,
            'user_id': user_id,
            'command': command,
            'risk_analysis': risk_analysis,
            'system_context': system_context,
            'start_time': time.time(),
            'confirmation_start': None,
            'confirmation_end': None,
            'execution_start': None,
            'execution_end': None,
            'user_confirmed': False,
            'execution_success': None,
            'actual_impact': None,
            'exit_code': None,
            'stdout_length': 0,
            'stderr_length': 0,
            'user_feedback': None,
            'feedback_rating': None
        }
        
        self.active_sessions[session_id] = session_data
        logger.info(f"Started command session: {session_id}")
        
        return session_id
    
    def record_user_confirmation(self, session_id: str, confirmed: bool, 
                               confirmation_time_ms: Optional[int] = None):
        """Record user confirmation decision and timing"""
        if session_id not in self.active_sessions:
            logger.warning(f"Session {session_id} not found for confirmation")
            return
        
        session = self.active_sessions[session_id]
        session['user_confirmed'] = confirmed
        session['confirmation_end'] = time.time()
        
        if confirmation_time_ms:
            session['confirmation_time_ms'] = confirmation_time_ms
        elif session.get('confirmation_start'):
            session['confirmation_time_ms'] = int((session['confirmation_end'] - session['confirmation_start']) * 1000)
        
        logger.info(f"Recorded confirmation for {session_id}: {confirmed}")
    
    def start_confirmation_timer(self, session_id: str):
        """Start timing how long user takes to confirm"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]['confirmation_start'] = time.time()
    
    def start_execution_timer(self, session_id: str):
        """Start timing command execution"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]['execution_start'] = time.time()
    
    def record_execution_result(self, session_id: str, success: bool, 
                              exit_code: int = 0, stdout: str = "", 
                              stderr: str = "", actual_impact: str = "none"):
        """
        Record command execution results
        
        Args:
            session_id: Session identifier
            success: Whether command executed successfully
            exit_code: Command exit code
            stdout: Standard output
            stderr: Standard error output
            actual_impact: Actual impact level (none/minor/moderate/severe)
        """
        if session_id not in self.active_sessions:
            logger.warning(f"Session {session_id} not found for execution result")
            return
        
        session = self.active_sessions[session_id]
        session['execution_end'] = time.time()
        session['execution_success'] = success
        session['exit_code'] = exit_code
        session['stdout_length'] = len(stdout)
        session['stderr_length'] = len(stderr)
        session['actual_impact'] = actual_impact
        
        # Calculate execution time
        if session.get('execution_start'):
            execution_time = session['execution_end'] - session['execution_start']
            session['execution_time_ms'] = int(execution_time * 1000)
        
        logger.info(f"Recorded execution result for {session_id}: success={success}")
    
    def add_user_feedback(self, session_id: str, feedback: str = None, 
                         rating: int = None):
        """Add optional user feedback to session"""
        if session_id not in self.active_sessions:
            logger.warning(f"Session {session_id} not found for feedback")
            return
        
        session = self.active_sessions[session_id]
        if feedback:
            session['user_feedback'] = feedback
        if rating and 1 <= rating <= 5:
            session['feedback_rating'] = rating
        
        logger.info(f"Added user feedback for {session_id}")
    
    def finalize_session(self, session_id: str) -> bool:
        """
        Finalize session and store in database
        
        Args:
            session_id: Session to finalize
            
        Returns:
            bool: True if successfully stored
        """
        if session_id not in self.active_sessions:
            logger.warning(f"Session {session_id} not found for finalization")
            return False
        
        session = self.active_sessions[session_id]
        
        # Ensure we have minimum required data
        if session.get('execution_success') is None:
            logger.warning(f"Session {session_id} missing execution result")
            return False
        
        try:
            # Prepare data for database storage
            execution_data = {
                'session_id': session['session_id'],
                'user_id': session['user_id'],
                'command': session['command'],
                'host_info': session['system_context'].get('host_info', {}),
                'initial_risk_level': session['risk_analysis'].get('risk_level', 'unknown'),
                'initial_risk_score': session['risk_analysis'].get('confidence_score', 0.0),
                'ml_risk_level': session['risk_analysis'].get('ml_risk_level'),
                'ml_confidence': session['risk_analysis'].get('ml_confidence'),
                'user_confirmed': session['user_confirmed'],
                'confirmation_time_ms': session.get('confirmation_time_ms', 0),
                'execution_success': session['execution_success'],
                'execution_time_ms': session.get('execution_time_ms', 0),
                'exit_code': session.get('exit_code', 0),
                'stdout_length': session.get('stdout_length', 0),
                'stderr_length': session.get('stderr_length', 0),
                'actual_impact': session.get('actual_impact', 'none'),
                'system_context': session['system_context'],
                'system_load_1min': session['system_context'].get('load_avg', {}).get('1min'),
                'system_load_5min': session['system_context'].get('load_avg', {}).get('5min'),
                'memory_usage_percent': session['system_context'].get('memory_usage', {}).get('percent'),
                'disk_usage_percent': session['system_context'].get('disk_usage', {}).get('/', {}).get('percent'),
                'network_active': session['system_context'].get('network_active', False),
                'timestamp': datetime.now().isoformat(),
                'user_feedback': session.get('user_feedback'),
                'feedback_rating': session.get('feedback_rating')
            }
            
            # Store in database
            record_id = self.db_manager.record_command_execution(execution_data)
            
            # Clean up session
            del self.active_sessions[session_id]
            
            logger.info(f"Finalized session {session_id} -> DB record {record_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to finalize session {session_id}: {e}")
            return False
    
    def get_session_summary(self, session_id: str) -> Optional[Dict]:
        """Get summary of current session"""
        return self.active_sessions.get(session_id)
    
    def cleanup_stale_sessions(self, max_age_hours: int = 24):
        """Clean up sessions that haven't been finalized"""
        current_time = time.time()
        stale_sessions = []
        
        for session_id, session in self.active_sessions.items():
            age_hours = (current_time - session['start_time']) / 3600
            if age_hours > max_age_hours:
                stale_sessions.append(session_id)
        
        for session_id in stale_sessions:
            del self.active_sessions[session_id]
            logger.info(f"Cleaned up stale session: {session_id}")
        
        return len(stale_sessions)


class AutoImpactDetector:
    """
    Automatically detect command impact based on system changes and outcomes.
    
    Uses heuristics and system monitoring to determine actual command impact
    without requiring manual user assessment.
    """
    
    def __init__(self):
        self.impact_patterns = {
            # File system changes
            'severe': [
                r'rm.*-rf.*/',  # Recursive deletion
                r'mkfs\.',      # Format filesystem
                r'dd.*of=/dev/',# Direct disk write
            ],
            'moderate': [
                r'chmod.*777',   # Dangerous permissions
                r'service.*stop', # Service management
                r'iptables.*-F', # Firewall flush
            ],
            'minor': [
                r'apt.*install', # Package installation
                r'mkdir',        # Directory creation
                r'touch',        # File creation
            ]
        }
    
    def detect_impact(self, command: str, exit_code: int, stdout: str, 
                     stderr: str, system_context_before: Dict, 
                     system_context_after: Dict) -> str:
        """
        Automatically detect command impact
        
        Args:
            command: Executed command
            exit_code: Command exit code
            stdout/stderr: Command output
            system_context_before/after: System state before/after execution
            
        Returns:
            str: Impact level (none/minor/moderate/severe)
        """
        # If command failed, impact is usually none unless it caused damage
        if exit_code != 0:
            if any(keyword in stderr.lower() for keyword in ['permission denied', 'not found']):
                return 'none'
            elif any(keyword in stderr.lower() for keyword in ['corrupted', 'damaged', 'destroyed']):
                return 'severe'
            else:
                return 'minor'
        
        # Pattern-based detection
        import re
        command_lower = command.lower()
        
        for impact_level, patterns in self.impact_patterns.items():
            for pattern in patterns:
                if re.search(pattern, command_lower):
                    return impact_level
        
        # System state comparison
        impact = self._compare_system_states(system_context_before, system_context_after)
        
        return impact if impact else 'none'
    
    def _compare_system_states(self, before: Dict, after: Dict) -> Optional[str]:
        """Compare system states to detect changes"""
        try:
            # Check disk usage changes
            before_disk = before.get('disk_usage', {})
            after_disk = after.get('disk_usage', {})
            
            for mount, usage_after in after_disk.items():
                usage_before = before_disk.get(mount, {})
                
                before_percent = usage_before.get('percent', 0)
                after_percent = usage_after.get('percent', 0)
                change = after_percent - before_percent
                
                if change > 10:  # >10% disk usage change
                    return 'moderate'
                elif change > 5:  # >5% disk usage change
                    return 'minor'
            
            # Check memory usage
            before_mem = before.get('memory_usage', {}).get('percent', 0)
            after_mem = after.get('memory_usage', {}).get('percent', 0)
            mem_change = abs(after_mem - before_mem)
            
            if mem_change > 20:  # >20% memory change
                return 'moderate'
            
            # Check running processes
            before_processes = set(before.get('processes', []))
            after_processes = set(after.get('processes', []))
            
            new_processes = after_processes - before_processes
            stopped_processes = before_processes - after_processes
            
            if len(stopped_processes) > 5:  # Many processes stopped
                return 'moderate'
            elif len(new_processes) > 10:  # Many new processes
                return 'minor'
            
        except Exception as e:
            logger.warning(f"Error comparing system states: {e}")
        
        return None


# Global collector instance
global_collector = CommandExecutionCollector()
impact_detector = AutoImpactDetector()


def collect_command_execution(command: str, risk_analysis: Dict, 
                            system_context: Dict, user_id: str = "unknown") -> str:
    """
    Convenience function to start collecting command execution data
    
    Returns:
        str: Session ID for tracking this execution
    """
    return global_collector.start_command_session(
        command, risk_analysis, system_context, user_id
    )


def finalize_command_collection(session_id: str, success: bool, 
                              exit_code: int = 0, stdout: str = "", 
                              stderr: str = "", system_context_after: Dict = None):
    """
    Convenience function to finalize command execution collection
    
    Automatically detects impact and stores the execution data
    """
    # Auto-detect impact if possible
    session_data = global_collector.get_session_summary(session_id)
    if session_data and system_context_after:
        impact = impact_detector.detect_impact(
            session_data['command'], exit_code, stdout, stderr,
            session_data['system_context'], system_context_after
        )
    else:
        # Fallback impact detection based on success/failure
        if not success:
            impact = 'minor' if exit_code != 0 else 'none'
        else:
            impact = 'none'
    
    # Record execution result
    global_collector.record_execution_result(
        session_id, success, exit_code, stdout, stderr, impact
    )
    
    # Finalize and store
    return global_collector.finalize_session(session_id)