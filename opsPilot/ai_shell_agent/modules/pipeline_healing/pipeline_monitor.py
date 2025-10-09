"""
Pipeline Monitor
Monitors various CI/CD pipeline systems for failures and triggers healing
"""
import json
import threading
import time
from typing import Dict, List, Callable, Optional
from datetime import datetime
from .error_interceptor import ErrorInterceptor
from .autonomous_healer import AutonomousHealer


class PipelineMonitor:
    """Monitors pipeline systems and triggers autonomous healing"""
    
    def __init__(self, error_interceptor: ErrorInterceptor = None, healer: AutonomousHealer = None):
        """
        Initialize pipeline monitor
        
        Args:
            error_interceptor: Error interceptor instance
            healer: Autonomous healer instance
        """
        self.error_interceptor = error_interceptor or ErrorInterceptor()
        self.healer = healer
        self.monitoring_active = False
        self.monitor_thread = None
        self.failure_callbacks = []
        self.healing_callbacks = []
        self.monitored_pipelines = {}
        
    def register_failure_callback(self, callback: Callable):
        """Register callback for pipeline failures"""
        self.failure_callbacks.append(callback)
    
    def register_healing_callback(self, callback: Callable):
        """Register callback for healing events"""
        self.healing_callbacks.append(callback)
    
    def add_pipeline(self, pipeline_id: str, pipeline_config: Dict):
        """
        Add a pipeline to monitor
        
        Args:
            pipeline_id: Unique pipeline identifier
            pipeline_config: Pipeline configuration
        """
        self.monitored_pipelines[pipeline_id] = {
            "config": pipeline_config,
            "status": "active",
            "last_check": None,
            "failure_count": 0,
            "healing_attempts": 0
        }
    
    def remove_pipeline(self, pipeline_id: str):
        """Remove pipeline from monitoring"""
        if pipeline_id in self.monitored_pipelines:
            del self.monitored_pipelines[pipeline_id]
    
    def start_monitoring(self, check_interval: int = 30):
        """
        Start monitoring pipelines
        
        Args:
            check_interval: Check interval in seconds
        """
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(check_interval,),
            daemon=True
        )
        self.monitor_thread.start()
        print(f"🔍 Pipeline monitoring started (interval: {check_interval}s)")
    
    def stop_monitoring(self):
        """Stop monitoring pipelines"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        print("🛑 Pipeline monitoring stopped")
    
    def _monitoring_loop(self, check_interval: int):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                for pipeline_id, pipeline_info in self.monitored_pipelines.items():
                    self._check_pipeline(pipeline_id, pipeline_info)
                
                time.sleep(check_interval)
                
            except Exception as e:
                print(f"❌ Monitoring error: {e}")
                time.sleep(check_interval)
    
    def _check_pipeline(self, pipeline_id: str, pipeline_info: Dict):
        """Check individual pipeline status"""
        config = pipeline_info["config"]
        pipeline_type = config.get("type", "unknown")
        
        try:
            if pipeline_type == "jenkins":
                self._check_jenkins_pipeline(pipeline_id, config)
            elif pipeline_type == "ansible":
                self._check_ansible_pipeline(pipeline_id, config)
            elif pipeline_type == "gitlab":
                self._check_gitlab_pipeline(pipeline_id, config)
            else:
                print(f"⚠️ Unknown pipeline type: {pipeline_type}")
            
            pipeline_info["last_check"] = datetime.now().isoformat()
            
        except Exception as e:
            print(f"❌ Error checking pipeline {pipeline_id}: {e}")
    
    def _check_jenkins_pipeline(self, pipeline_id: str, config: Dict):
        """Check Jenkins pipeline status"""
        # This would integrate with Jenkins API in real implementation
        # For now, simulate pipeline checking
        pass
    
    def _check_ansible_pipeline(self, pipeline_id: str, config: Dict):
        """Check Ansible pipeline status"""
        # This would check Ansible execution logs/status
        # For now, simulate pipeline checking
        pass
    
    def _check_gitlab_pipeline(self, pipeline_id: str, config: Dict):
        """Check GitLab pipeline status"""
        # This would integrate with GitLab API
        # For now, simulate pipeline checking
        pass
    
    def handle_webhook_failure(self, webhook_data: Dict) -> Dict:
        """
        Handle failure webhook from pipeline systems
        
        Args:
            webhook_data: Webhook payload with failure information
            
        Returns:
            Response indicating handling status
        """
        try:
            # Determine source system
            source = webhook_data.get("source", "unknown")
            
            # Process based on source
            if source == "jenkins":
                error_info = self.error_interceptor.capture_jenkins_error(webhook_data)
            elif source == "ansible":
                error_info = self.error_interceptor.capture_ansible_error(webhook_data)
            else:
                # Generic error processing
                error_info = self._process_generic_webhook(webhook_data)
            
            # Notify failure callbacks
            for callback in self.failure_callbacks:
                try:
                    callback(error_info)
                except Exception as e:
                    print(f"❌ Failure callback error: {e}")
            
            # Trigger healing if healer is available
            healing_result = None
            if self.healer and error_info.get("severity") != "low":
                healing_result = self._trigger_healing(error_info, webhook_data)
            
            return {
                "success": True,
                "error_info": error_info,
                "healing_result": healing_result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _process_generic_webhook(self, webhook_data: Dict) -> Dict:
        """Process generic webhook failure"""
        error_info = {
            "timestamp": datetime.now().isoformat(),
            "source": webhook_data.get("source", "webhook"),
            "pipeline_id": webhook_data.get("pipeline_id", "unknown"),
            "stage": webhook_data.get("stage", "unknown"),
            "raw_error": webhook_data.get("error_message", ""),
            "error_category": "unknown",
            "severity": "medium"
        }
        
        # Basic categorization
        raw_error = error_info["raw_error"].lower()
        if "package" in raw_error or "install" in raw_error:
            error_info["error_category"] = "package_management"
        elif "service" in raw_error or "daemon" in raw_error:
            error_info["error_category"] = "service_management"
        elif "permission" in raw_error or "access" in raw_error:
            error_info["error_category"] = "permissions"
        elif "network" in raw_error or "connection" in raw_error:
            error_info["error_category"] = "network"
        
        return error_info
    
    def _trigger_healing(self, error_info: Dict, webhook_data: Dict) -> Dict:
        """Trigger autonomous healing for the error"""
        try:
            # Extract target hosts from webhook data
            target_hosts = webhook_data.get("target_hosts", [])
            if not target_hosts and "host" in error_info:
                target_hosts = [error_info["host"]]
            
            # Attempt healing
            healing_result = self.healer.heal_error(
                error_info=error_info,
                target_hosts=target_hosts
            )
            
            # Notify healing callbacks
            for callback in self.healing_callbacks:
                try:
                    callback(healing_result)
                except Exception as e:
                    print(f"❌ Healing callback error: {e}")
            
            # Update pipeline statistics
            pipeline_id = webhook_data.get("pipeline_id")
            if pipeline_id in self.monitored_pipelines:
                self.monitored_pipelines[pipeline_id]["healing_attempts"] += 1
            
            return healing_result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Healing trigger failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    def get_monitoring_stats(self) -> Dict:
        """Get monitoring statistics"""
        stats = {
            "monitoring_active": self.monitoring_active,
            "monitored_pipelines": len(self.monitored_pipelines),
            "total_failures": len(self.error_interceptor.captured_errors),
            "pipeline_details": {}
        }
        
        for pipeline_id, info in self.monitored_pipelines.items():
            stats["pipeline_details"][pipeline_id] = {
                "status": info["status"],
                "last_check": info["last_check"],
                "failure_count": info["failure_count"],
                "healing_attempts": info["healing_attempts"]
            }
        
        if self.healer:
            stats["healing_success_rate"] = self.healer.get_success_rate()
            stats["healing_history_count"] = len(self.healer.get_healing_history())
        
        return stats
    
    def export_monitoring_data(self, format: str = "json") -> str:
        """Export monitoring data"""
        data = {
            "stats": self.get_monitoring_stats(),
            "captured_errors": self.error_interceptor.get_recent_errors(50),
            "healing_history": self.healer.get_healing_history(20) if self.healer else []
        }
        
        if format == "json":
            return json.dumps(data, indent=2)
        else:
            return str(data)
