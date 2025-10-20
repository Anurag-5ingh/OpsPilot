"""
Background Worker for CI/CD Integration

Handles periodic polling of Jenkins servers to fetch new builds and 
automatic analysis of failed builds for proactive issue detection.
"""

import time
import threading
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
import schedule

from .models import JenkinsConfig, AnsibleConfig, BuildLog
from .jenkins_service import JenkinsService
from .ansible_service import AnsibleService  
from .ai_analyzer import AILogAnalyzer
from ..shared import ConversationMemory
from ..system_awareness import SystemContextManager

logger = logging.getLogger(__name__)


class CICDBackgroundWorker:
    """Background worker for CI/CD integration tasks."""
    
    def __init__(self, memory: ConversationMemory = None, system_context: SystemContextManager = None):
        self.memory = memory or ConversationMemory(max_entries=20)
        self.system_context = system_context or SystemContextManager()
        self.ai_analyzer = AILogAnalyzer(self.memory, self.system_context)
        
        self.is_running = False
        self.worker_thread = None
        self.stop_event = threading.Event()
        
        # Configuration
        self.poll_interval_minutes = 15  # Poll every 15 minutes by default
        self.max_builds_per_poll = 10    # Limit builds fetched per poll
        self.auto_analyze_failures = True  # Automatically analyze failed builds
        
        # Statistics
        self.stats = {
            'total_polls': 0,
            'builds_fetched': 0,
            'builds_analyzed': 0,
            'last_poll': None,
            'last_error': None
        }
    
    def start(self):
        """Start the background worker."""
        if self.is_running:
            logger.warning("Background worker is already running")
            return
        
        self.is_running = True
        self.stop_event.clear()
        
        # Schedule periodic tasks
        schedule.every(self.poll_interval_minutes).minutes.do(self._poll_jenkins_builds)
        schedule.every().hour.do(self._cleanup_old_builds)
        schedule.every(6).hours.do(self._sync_ansible_repos)
        
        # Start worker thread
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        
        logger.info(f"CI/CD background worker started (poll interval: {self.poll_interval_minutes} minutes)")
    
    def stop(self):
        """Stop the background worker."""
        if not self.is_running:
            return
        
        self.is_running = False
        self.stop_event.set()
        
        # Clear scheduled tasks
        schedule.clear()
        
        # Wait for worker thread to finish
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)
        
        logger.info("CI/CD background worker stopped")
    
    def _worker_loop(self):
        """Main worker loop that runs scheduled tasks."""
        while self.is_running and not self.stop_event.is_set():
            try:
                # Run scheduled tasks
                schedule.run_pending()
                
                # Sleep for a short interval
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                self.stats['last_error'] = str(e)
                time.sleep(60)  # Wait longer on error
    
    def _poll_jenkins_builds(self):
        """Poll all Jenkins configurations for new builds."""
        try:
            self.stats['total_polls'] += 1
            self.stats['last_poll'] = datetime.now(timezone.utc)
            
            # Get all Jenkins configurations (assuming default user for now)
            # In a real application, you'd iterate over all users
            jenkins_configs = JenkinsConfig.get_by_user("system")
            
            if not jenkins_configs:
                logger.debug("No Jenkins configurations found for polling")
                return
            
            total_fetched = 0
            total_analyzed = 0
            
            for config in jenkins_configs:
                try:
                    fetched, analyzed = self._poll_jenkins_config(config)
                    total_fetched += fetched
                    total_analyzed += analyzed
                    
                except Exception as e:
                    logger.error(f"Error polling Jenkins config {config.id}: {e}")
                    continue
            
            self.stats['builds_fetched'] += total_fetched
            self.stats['builds_analyzed'] += total_analyzed
            
            logger.info(f"Polling completed: {total_fetched} builds fetched, {total_analyzed} analyzed")
            
        except Exception as e:
            logger.error(f"Error in Jenkins polling: {e}")
            self.stats['last_error'] = str(e)
    
    def _poll_jenkins_config(self, config: JenkinsConfig) -> Tuple[int, int]:
        """Poll a specific Jenkins configuration for new builds."""
        jenkins_service = None
        builds_fetched = 0
        builds_analyzed = 0
        
        try:
            jenkins_service = JenkinsService(config)
            
            # Test connection first
            connection_test = jenkins_service.test_connection()
            if not connection_test.get('success'):
                logger.warning(f"Jenkins connection failed for config {config.id}: {connection_test.get('error')}")
                return 0, 0
            
            # Get list of servers to poll (this would come from user settings in a real app)
            # For now, we'll fetch recent builds without server filtering
            recent_builds = jenkins_service.fetch_and_store_builds(
                server_name=None, 
                limit=self.max_builds_per_poll
            )
            
            builds_fetched = len(recent_builds)
            
            # Auto-analyze failed builds if enabled
            if self.auto_analyze_failures and recent_builds:
                for build in recent_builds:
                    if build.status in ['FAILURE', 'ABORTED', 'UNSTABLE']:
                        try:
                            # Check if this build was already analyzed recently
                            if self._should_analyze_build(build):
                                self._analyze_build_async(build, jenkins_service, config)
                                builds_analyzed += 1
                        except Exception as e:
                            logger.error(f"Error analyzing build {build.id}: {e}")
            
            return builds_fetched, builds_analyzed
            
        except Exception as e:
            logger.error(f"Error polling Jenkins config {config.id}: {e}")
            return 0, 0
        finally:
            if jenkins_service:
                jenkins_service.close()
    
    def _should_analyze_build(self, build: BuildLog) -> bool:
        """Check if a build should be analyzed (not analyzed recently)."""
        try:
            # Check if there are recent fix history entries for this build
            from .models import FixHistory
            recent_fixes = FixHistory.get_by_build(build.id)
            
            # Only analyze if no recent analysis (within last 24 hours)
            if recent_fixes:
                # Check if the most recent fix was created within last 24 hours
                for fix in recent_fixes:
                    if fix.executed_at:
                        # Parse the timestamp (assuming it's stored as string)
                        try:
                            executed_time = datetime.fromisoformat(fix.executed_at.replace('Z', '+00:00'))
                            time_diff = datetime.now(timezone.utc) - executed_time
                            if time_diff < timedelta(hours=24):
                                return False  # Recently analyzed
                        except:
                            pass
            
            return True  # No recent analysis found
            
        except Exception as e:
            logger.debug(f"Error checking if build should be analyzed: {e}")
            return True  # Default to analyzing
    
    def _analyze_build_async(self, build: BuildLog, jenkins_service: JenkinsService, config: JenkinsConfig):
        """Analyze a build asynchronously (in background)."""
        try:
            # Get corresponding Ansible service if available
            ansible_service = None
            ansible_configs = AnsibleConfig.get_by_user(config.user_id)
            if ansible_configs:
                # Use the first available Ansible config
                ansible_service = AnsibleService(ansible_configs[0])
            
            # Perform analysis
            analysis_result = self.ai_analyzer.analyze_build_failure(
                build, jenkins_service, ansible_service
            )
            
            if analysis_result.get('success'):
                # Create fix history record
                fix_history = self.ai_analyzer.create_fix_history(analysis_result)
                if fix_history:
                    logger.info(f"Auto-analyzed build {build.job_name}#{build.build_number}: {analysis_result.get('error_summary')}")
                else:
                    logger.warning(f"Analysis successful but failed to save fix history for build {build.id}")
            else:
                logger.warning(f"Analysis failed for build {build.id}: {analysis_result.get('error')}")
                
        except Exception as e:
            logger.error(f"Error in async build analysis: {e}")
    
    def _cleanup_old_builds(self):
        """Clean up old build logs to save space."""
        try:
            # This would implement cleanup logic
            # For example: delete build logs older than 30 days
            # and keep only the most recent 100 builds per job
            
            logger.info("Build cleanup task completed")
            
        except Exception as e:
            logger.error(f"Error in build cleanup: {e}")
    
    def _sync_ansible_repos(self):
        """Sync Ansible repositories from Git."""
        try:
            # Get all Ansible configurations with Git repos
            # This is a simplified version - in reality you'd iterate over users
            ansible_configs = AnsibleConfig.get_by_user("system")
            
            synced_count = 0
            
            for config in ansible_configs:
                if config.git_repo_url:
                    try:
                        ansible_service = AnsibleService(config)
                        sync_result = ansible_service.sync_from_git()
                        
                        if sync_result.get('success'):
                            synced_count += 1
                            logger.info(f"Synced Ansible repo for config {config.id}")
                        else:
                            logger.warning(f"Failed to sync Ansible repo for config {config.id}: {sync_result.get('error')}")
                            
                    except Exception as e:
                        logger.error(f"Error syncing Ansible config {config.id}: {e}")
            
            logger.info(f"Ansible sync completed: {synced_count} repositories synced")
            
        except Exception as e:
            logger.error(f"Error in Ansible sync: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the background worker."""
        return {
            'running': self.is_running,
            'poll_interval_minutes': self.poll_interval_minutes,
            'auto_analyze_failures': self.auto_analyze_failures,
            'stats': self.stats.copy()
        }
    
    def update_config(self, config: Dict[str, Any]):
        """Update worker configuration."""
        if 'poll_interval_minutes' in config:
            self.poll_interval_minutes = max(5, int(config['poll_interval_minutes']))
            
            # Update schedule if running
            if self.is_running:
                schedule.clear()
                schedule.every(self.poll_interval_minutes).minutes.do(self._poll_jenkins_builds)
                schedule.every().hour.do(self._cleanup_old_builds)
                schedule.every(6).hours.do(self._sync_ansible_repos)
        
        if 'max_builds_per_poll' in config:
            self.max_builds_per_poll = max(1, int(config['max_builds_per_poll']))
        
        if 'auto_analyze_failures' in config:
            self.auto_analyze_failures = bool(config['auto_analyze_failures'])
        
        logger.info(f"Worker configuration updated: {config}")


# Global worker instance
_worker_instance = None


def get_worker(memory: ConversationMemory = None, system_context: SystemContextManager = None) -> CICDBackgroundWorker:
    """Get the global background worker instance."""
    global _worker_instance
    if _worker_instance is None:
        _worker_instance = CICDBackgroundWorker(memory, system_context)
    return _worker_instance


def start_background_worker(memory: ConversationMemory = None, system_context: SystemContextManager = None):
    """Start the background worker."""
    worker = get_worker(memory, system_context)
    worker.start()
    return worker


def stop_background_worker():
    """Stop the background worker."""
    global _worker_instance
    if _worker_instance:
        _worker_instance.stop()
