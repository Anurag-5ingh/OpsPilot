"""
Real-time System Monitoring

Continuous monitoring of system state changes to provide dynamic context
for ML features, predictive analysis, and intelligent decision making.
"""

import asyncio
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict
from collections import deque, defaultdict
from enum import Enum
import logging
import psutil
import socket
from concurrent.futures import ThreadPoolExecutor

from ..ssh.ssh_manager import create_ssh_client

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Severity levels for system alerts"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class MonitoringMetricType(Enum):
    """Types of monitoring metrics"""
    SYSTEM_RESOURCE = "system_resource"
    NETWORK_STATUS = "network_status"
    SERVICE_STATUS = "service_status"
    DISK_USAGE = "disk_usage"
    PROCESS_STATUS = "process_status"
    SECURITY_EVENT = "security_event"


@dataclass
class SystemMetric:
    """Represents a system metric measurement"""
    metric_type: MonitoringMetricType
    name: str
    value: Any
    unit: str
    timestamp: datetime
    host: str
    threshold_exceeded: bool = False
    severity: AlertSeverity = AlertSeverity.INFO


@dataclass
class SystemAlert:
    """Represents a system alert"""
    alert_id: str
    metric_name: str
    message: str
    severity: AlertSeverity
    current_value: Any
    threshold_value: Any
    host: str
    timestamp: datetime
    resolved: bool = False
    resolution_timestamp: Optional[datetime] = None


@dataclass
class HostConfiguration:
    """Configuration for monitoring a specific host"""
    hostname: str
    ssh_config: Dict[str, Any]
    monitoring_enabled: bool = True
    collection_interval: int = 30  # seconds
    metrics_to_collect: List[str] = None
    custom_commands: Dict[str, str] = None
    thresholds: Dict[str, Dict] = None


class SystemMetricCollector:
    """Collects system metrics from monitored hosts"""
    
    def __init__(self):
        self.ssh_connections = {}
        self.metric_cache = {}
        
    def collect_local_metrics(self) -> List[SystemMetric]:
        """Collect metrics from local system using psutil"""
        metrics = []
        timestamp = datetime.now()
        
        try:
            # CPU Usage
            cpu_percent = psutil.cpu_percent(interval=1)
            metrics.append(SystemMetric(
                metric_type=MonitoringMetricType.SYSTEM_RESOURCE,
                name="cpu_usage",
                value=cpu_percent,
                unit="percent",
                timestamp=timestamp,
                host="localhost"
            ))
            
            # Memory Usage
            memory = psutil.virtual_memory()
            metrics.append(SystemMetric(
                metric_type=MonitoringMetricType.SYSTEM_RESOURCE,
                name="memory_usage",
                value=memory.percent,
                unit="percent",
                timestamp=timestamp,
                host="localhost"
            ))
            
            # Disk Usage
            for disk in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(disk.mountpoint)
                    # Avoid backslash in f-string expressions; pre-sanitize mountpoint
                    _mp = disk.mountpoint.replace('/', '_').replace('\\', '_')
                    metrics.append(SystemMetric(
                        metric_type=MonitoringMetricType.DISK_USAGE,
                        name=f"disk_usage_{_mp}",
                        value=usage.percent,
                        unit="percent",
                        timestamp=timestamp,
                        host="localhost"
                    ))
                except PermissionError:
                    continue
            
            # Network Connections
            network_connections = len(psutil.net_connections())
            metrics.append(SystemMetric(
                metric_type=MonitoringMetricType.NETWORK_STATUS,
                name="active_connections",
                value=network_connections,
                unit="count",
                timestamp=timestamp,
                host="localhost"
            ))
            
            # Load Average (Unix-like systems only)
            try:
                load_avg = psutil.getloadavg()
                for i, interval in enumerate(['1min', '5min', '15min']):
                    metrics.append(SystemMetric(
                        metric_type=MonitoringMetricType.SYSTEM_RESOURCE,
                        name=f"load_avg_{interval}",
                        value=load_avg[i],
                        unit="load",
                        timestamp=timestamp,
                        host="localhost"
                    ))
            except (AttributeError, OSError):
                # Not available on Windows
                pass
            
        except Exception as e:
            logger.error(f"Failed to collect local metrics: {e}")
        
        return metrics
    
    def collect_remote_metrics(self, host_config: HostConfiguration) -> List[SystemMetric]:
        """Collect metrics from remote host via SSH"""
        metrics = []
        timestamp = datetime.now()
        hostname = host_config.hostname
        
        try:
            # Get or create SSH connection
            ssh_client = self._get_ssh_connection(host_config)
            if not ssh_client:
                return metrics
            
            # Collect system metrics
            commands = {
                'cpu_usage': "top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1",
                'memory_usage': "free | grep Mem | awk '{printf \"%.1f\", $3/$2 * 100.0}'",
                'disk_usage': "df -h / | tail -1 | awk '{print $5}' | cut -d'%' -f1",
                'load_avg': "uptime | awk -F'load average:' '{print $2}'",
                'active_processes': "ps aux | wc -l"
            }
            
            for metric_name, command in commands.items():
                try:
                    stdin, stdout, stderr = ssh_client.exec_command(command, timeout=10)
                    output = stdout.read().decode().strip()
                    error = stderr.read().decode().strip()
                    
                    if not error and output:
                        # Parse output based on metric type
                        value = self._parse_metric_output(metric_name, output)
                        if value is not None:
                            metrics.append(SystemMetric(
                                metric_type=self._get_metric_type(metric_name),
                                name=metric_name,
                                value=value,
                                unit=self._get_metric_unit(metric_name),
                                timestamp=timestamp,
                                host=hostname
                            ))
                
                except Exception as e:
                    logger.warning(f"Failed to collect {metric_name} from {hostname}: {e}")
            
            # Collect custom metrics if configured
            if host_config.custom_commands:
                for metric_name, command in host_config.custom_commands.items():
                    try:
                        stdin, stdout, stderr = ssh_client.exec_command(command, timeout=15)
                        output = stdout.read().decode().strip()
                        
                        if output:
                            metrics.append(SystemMetric(
                                metric_type=MonitoringMetricType.SYSTEM_RESOURCE,
                                name=f"custom_{metric_name}",
                                value=output,
                                unit="custom",
                                timestamp=timestamp,
                                host=hostname
                            ))
                    except Exception as e:
                        logger.warning(f"Failed to collect custom metric {metric_name}: {e}")
        
        except Exception as e:
            logger.error(f"Failed to collect metrics from {hostname}: {e}")
        
        return metrics
    
    def _get_ssh_connection(self, host_config: HostConfiguration):
        """Get or create SSH connection for host"""
        hostname = host_config.hostname
        
        # Check if connection exists and is alive
        if hostname in self.ssh_connections:
            ssh_client = self.ssh_connections[hostname]
            try:
                # Test connection
                ssh_client.exec_command('echo test', timeout=5)
                return ssh_client
            except:
                # Connection is dead, remove it
                try:
                    ssh_client.close()
                except:
                    pass
                del self.ssh_connections[hostname]
        
        # Create new connection
        try:
            ssh_client = create_ssh_client(
                hostname,
                host_config.ssh_config.get('username'),
                host_config.ssh_config.get('port', 22),
                host_config.ssh_config.get('password')
            )
            
            if ssh_client:
                self.ssh_connections[hostname] = ssh_client
                return ssh_client
        
        except Exception as e:
            logger.error(f"Failed to create SSH connection to {hostname}: {e}")
        
        return None
    
    def _parse_metric_output(self, metric_name: str, output: str) -> Optional[float]:
        """Parse command output to extract metric value"""
        try:
            if metric_name in ['cpu_usage', 'memory_usage', 'disk_usage']:
                return float(output)
            elif metric_name == 'active_processes':
                return int(output)
            elif metric_name == 'load_avg':
                # Parse load average: "1.23, 1.45, 1.67"
                parts = output.split(',')
                if parts:
                    return float(parts[0].strip())
        except (ValueError, IndexError):
            pass
        
        return None
    
    def _get_metric_type(self, metric_name: str) -> MonitoringMetricType:
        """Get metric type for metric name"""
        if metric_name in ['cpu_usage', 'memory_usage', 'load_avg']:
            return MonitoringMetricType.SYSTEM_RESOURCE
        elif metric_name == 'disk_usage':
            return MonitoringMetricType.DISK_USAGE
        elif metric_name == 'active_processes':
            return MonitoringMetricType.PROCESS_STATUS
        else:
            return MonitoringMetricType.SYSTEM_RESOURCE
    
    def _get_metric_unit(self, metric_name: str) -> str:
        """Get unit for metric name"""
        if metric_name in ['cpu_usage', 'memory_usage', 'disk_usage']:
            return "percent"
        elif metric_name == 'load_avg':
            return "load"
        elif metric_name == 'active_processes':
            return "count"
        else:
            return "value"
    
    def close_connections(self):
        """Close all SSH connections"""
        for hostname, ssh_client in self.ssh_connections.items():
            try:
                ssh_client.close()
            except:
                pass
        self.ssh_connections.clear()


class AlertManager:
    """Manages system alerts and notifications"""
    
    def __init__(self):
        self.active_alerts = {}
        self.alert_history = deque(maxlen=1000)
        self.alert_callbacks = []
        
    def check_thresholds(self, metrics: List[SystemMetric], 
                        thresholds: Dict[str, Dict]) -> List[SystemAlert]:
        """Check metrics against thresholds and generate alerts"""
        alerts = []
        
        for metric in metrics:
            metric_key = f"{metric.host}:{metric.name}"
            threshold_config = thresholds.get(metric.name, {})
            
            if not threshold_config:
                continue
            
            # Check if threshold is exceeded
            threshold_exceeded = False
            severity = AlertSeverity.INFO
            threshold_value = None
            
            # Check different threshold types
            if 'critical' in threshold_config and isinstance(metric.value, (int, float)):
                critical_threshold = threshold_config['critical']
                if metric.value >= critical_threshold:
                    threshold_exceeded = True
                    severity = AlertSeverity.CRITICAL
                    threshold_value = critical_threshold
            
            elif 'warning' in threshold_config and isinstance(metric.value, (int, float)):
                warning_threshold = threshold_config['warning']
                if metric.value >= warning_threshold:
                    threshold_exceeded = True
                    severity = AlertSeverity.WARNING
                    threshold_value = warning_threshold
            
            # Update metric
            metric.threshold_exceeded = threshold_exceeded
            metric.severity = severity
            
            # Generate alert if threshold exceeded
            if threshold_exceeded:
                # Check if alert already exists
                if metric_key in self.active_alerts:
                    continue  # Alert already active
                
                alert = SystemAlert(
                    alert_id=f"{metric_key}_{int(time.time())}",
                    metric_name=metric.name,
                    message=f"{metric.name} on {metric.host} exceeded threshold: {metric.value}{metric.unit} >= {threshold_value}",
                    severity=severity,
                    current_value=metric.value,
                    threshold_value=threshold_value,
                    host=metric.host,
                    timestamp=metric.timestamp
                )
                
                self.active_alerts[metric_key] = alert
                alerts.append(alert)
                
                # Notify callbacks
                self._notify_alert_callbacks(alert)
            
            else:
                # Check if we should resolve an existing alert
                if metric_key in self.active_alerts:
                    alert = self.active_alerts[metric_key]
                    alert.resolved = True
                    alert.resolution_timestamp = datetime.now()
                    
                    self.alert_history.append(alert)
                    del self.active_alerts[metric_key]
        
        return alerts
    
    def add_alert_callback(self, callback: Callable[[SystemAlert], None]):
        """Add callback function to be notified of new alerts"""
        self.alert_callbacks.append(callback)
    
    def _notify_alert_callbacks(self, alert: SystemAlert):
        """Notify all registered callbacks of new alert"""
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
    
    def get_active_alerts(self) -> List[SystemAlert]:
        """Get list of currently active alerts"""
        return list(self.active_alerts.values())
    
    def get_alert_history(self, hours_back: int = 24) -> List[SystemAlert]:
        """Get alert history for specified time period"""
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        return [alert for alert in self.alert_history 
               if alert.timestamp >= cutoff_time]


class RealTimeSystemMonitor:
    """
    Main real-time system monitoring system that coordinates metric collection,
    alerting, and provides context for ML systems.
    """
    
    def __init__(self):
        self.is_running = False
        self.monitoring_thread = None
        self.executor = ThreadPoolExecutor(max_workers=5)
        
        # Components
        self.metric_collector = SystemMetricCollector()
        self.alert_manager = AlertManager()
        
        # Configuration
        self.monitored_hosts = {}
        self.global_thresholds = {
            'cpu_usage': {'warning': 80.0, 'critical': 95.0},
            'memory_usage': {'warning': 85.0, 'critical': 95.0},
            'disk_usage': {'warning': 80.0, 'critical': 90.0},
            'load_avg_1min': {'warning': 2.0, 'critical': 5.0}
        }
        
        # Data storage
        self.metrics_history = defaultdict(lambda: deque(maxlen=1000))
        self.system_snapshots = deque(maxlen=100)
        
        # Callbacks for real-time updates
        self.metric_callbacks = []
        self.context_change_callbacks = []
    
    def add_host(self, hostname: str, ssh_config: Dict[str, Any], 
                monitoring_config: Optional[Dict] = None):
        """Add a host to monitor"""
        config = HostConfiguration(
            hostname=hostname,
            ssh_config=ssh_config,
            monitoring_enabled=monitoring_config.get('enabled', True) if monitoring_config else True,
            collection_interval=monitoring_config.get('interval', 30) if monitoring_config else 30,
            metrics_to_collect=monitoring_config.get('metrics') if monitoring_config else None,
            custom_commands=monitoring_config.get('custom_commands') if monitoring_config else None,
            thresholds=monitoring_config.get('thresholds') if monitoring_config else None
        )
        
        self.monitored_hosts[hostname] = config
        logger.info(f"Added host {hostname} to monitoring")
    
    def remove_host(self, hostname: str):
        """Remove a host from monitoring"""
        if hostname in self.monitored_hosts:
            del self.monitored_hosts[hostname]
            logger.info(f"Removed host {hostname} from monitoring")
    
    def start_monitoring(self):
        """Start real-time monitoring"""
        if self.is_running:
            logger.warning("Monitoring is already running")
            return
        
        self.is_running = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        logger.info("Real-time monitoring started")
    
    def stop_monitoring(self):
        """Stop real-time monitoring"""
        if not self.is_running:
            return
        
        self.is_running = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        self.metric_collector.close_connections()
        self.executor.shutdown(wait=True)
        logger.info("Real-time monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                # Collect metrics from all hosts
                all_metrics = []
                
                # Collect local metrics
                local_metrics = self.metric_collector.collect_local_metrics()
                all_metrics.extend(local_metrics)
                
                # Collect remote metrics in parallel
                futures = []
                for hostname, host_config in self.monitored_hosts.items():
                    if host_config.monitoring_enabled:
                        future = self.executor.submit(
                            self.metric_collector.collect_remote_metrics, 
                            host_config
                        )
                        futures.append(future)
                
                # Gather results
                for future in futures:
                    try:
                        remote_metrics = future.result(timeout=30)
                        all_metrics.extend(remote_metrics)
                    except Exception as e:
                        logger.error(f"Failed to collect remote metrics: {e}")
                
                # Process metrics
                if all_metrics:
                    self._process_metrics(all_metrics)
                
                # Sleep until next collection interval
                time.sleep(min(30, min(host.collection_interval 
                                     for host in self.monitored_hosts.values()) 
                              if self.monitored_hosts else 30))
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)  # Brief pause before retrying
    
    def _process_metrics(self, metrics: List[SystemMetric]):
        """Process collected metrics"""
        # Store metrics in history
        for metric in metrics:
            key = f"{metric.host}:{metric.name}"
            self.metrics_history[key].append(metric)
        
        # Check thresholds and generate alerts
        alerts = self.alert_manager.check_thresholds(metrics, self.global_thresholds)
        
        # Create system snapshot
        snapshot = {
            'timestamp': datetime.now(),
            'metrics': [asdict(metric) for metric in metrics],
            'active_alerts': len(self.alert_manager.get_active_alerts())
        }
        self.system_snapshots.append(snapshot)
        
        # Notify metric callbacks
        self._notify_metric_callbacks(metrics)
        
        # Check for significant context changes
        if self._detect_context_changes(metrics):
            self._notify_context_change_callbacks(self.get_current_context())
    
    def _detect_context_changes(self, current_metrics: List[SystemMetric]) -> bool:
        """Detect significant changes in system context"""
        # Simple change detection - can be enhanced
        if len(self.system_snapshots) < 2:
            return False
        
        previous_snapshot = self.system_snapshots[-2]
        current_snapshot = self.system_snapshots[-1]
        
        # Check if alert count changed significantly
        if abs(current_snapshot['active_alerts'] - previous_snapshot['active_alerts']) > 0:
            return True
        
        # Check for significant metric changes (>20% change)
        # This is a simplified implementation
        return False
    
    def _notify_metric_callbacks(self, metrics: List[SystemMetric]):
        """Notify registered callbacks of new metrics"""
        for callback in self.metric_callbacks:
            try:
                callback(metrics)
            except Exception as e:
                logger.error(f"Metric callback failed: {e}")
    
    def _notify_context_change_callbacks(self, context: Dict):
        """Notify registered callbacks of context changes"""
        for callback in self.context_change_callbacks:
            try:
                callback(context)
            except Exception as e:
                logger.error(f"Context change callback failed: {e}")
    
    def add_metric_callback(self, callback: Callable[[List[SystemMetric]], None]):
        """Add callback for metric updates"""
        self.metric_callbacks.append(callback)
    
    def add_context_change_callback(self, callback: Callable[[Dict], None]):
        """Add callback for context changes"""
        self.context_change_callbacks.append(callback)
    
    def get_current_metrics(self, hostname: Optional[str] = None) -> List[SystemMetric]:
        """Get current metrics for host(s)"""
        current_metrics = []
        
        for key, metric_deque in self.metrics_history.items():
            if metric_deque:
                latest_metric = metric_deque[-1]
                if hostname is None or latest_metric.host == hostname:
                    current_metrics.append(latest_metric)
        
        return current_metrics
    
    def get_metric_history(self, metric_name: str, hostname: str, 
                          hours_back: int = 24) -> List[SystemMetric]:
        """Get historical data for specific metric"""
        key = f"{hostname}:{metric_name}"
        if key not in self.metrics_history:
            return []
        
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        return [metric for metric in self.metrics_history[key] 
               if metric.timestamp >= cutoff_time]
    
    def get_current_context(self) -> Dict:
        """Get current system context for ML features"""
        context = {
            'timestamp': datetime.now().isoformat(),
            'hosts': {},
            'alerts': {
                'active_count': len(self.alert_manager.get_active_alerts()),
                'critical_count': len([a for a in self.alert_manager.get_active_alerts() 
                                     if a.severity == AlertSeverity.CRITICAL]),
                'warning_count': len([a for a in self.alert_manager.get_active_alerts() 
                                    if a.severity == AlertSeverity.WARNING])
            },
            'system_health': 'healthy'  # Will be calculated based on metrics
        }
        
        # Add per-host context
        for hostname in list(self.monitored_hosts.keys()) + ['localhost']:
            host_metrics = self.get_current_metrics(hostname)
            if host_metrics:
                host_context = {}
                for metric in host_metrics:
                    host_context[metric.name] = {
                        'value': metric.value,
                        'unit': metric.unit,
                        'threshold_exceeded': metric.threshold_exceeded,
                        'timestamp': metric.timestamp.isoformat()
                    }
                context['hosts'][hostname] = host_context
        
        # Determine overall system health
        active_alerts = self.alert_manager.get_active_alerts()
        if any(alert.severity == AlertSeverity.CRITICAL for alert in active_alerts):
            context['system_health'] = 'critical'
        elif any(alert.severity == AlertSeverity.WARNING for alert in active_alerts):
            context['system_health'] = 'warning'
        elif len(active_alerts) > 0:
            context['system_health'] = 'degraded'
        
        return context
    
    def get_monitoring_stats(self) -> Dict:
        """Get monitoring system statistics"""
        return {
            'is_running': self.is_running,
            'monitored_hosts': len(self.monitored_hosts),
            'total_metrics_collected': sum(len(deque) for deque in self.metrics_history.values()),
            'active_alerts': len(self.alert_manager.get_active_alerts()),
            'alert_history_count': len(self.alert_manager.alert_history),
            'last_collection': max((deque[-1].timestamp for deque in self.metrics_history.values() 
                                  if deque), default=None)
        }
    
    def set_thresholds(self, thresholds: Dict[str, Dict]):
        """Update global thresholds"""
        self.global_thresholds.update(thresholds)
        logger.info("Updated monitoring thresholds")
    
    def get_system_trends(self, hours_back: int = 24) -> Dict:
        """Get system trends and predictions"""
        trends = {}
        
        for hostname in list(self.monitored_hosts.keys()) + ['localhost']:
            host_trends = {}
            
            # Analyze key metrics trends
            for metric_name in ['cpu_usage', 'memory_usage', 'disk_usage']:
                history = self.get_metric_history(metric_name, hostname, hours_back)
                if len(history) >= 2:
                    # Simple trend calculation
                    recent_avg = sum(m.value for m in history[-5:]) / len(history[-5:])
                    older_avg = sum(m.value for m in history[:5]) / len(history[:5])
                    trend = (recent_avg - older_avg) / older_avg * 100
                    
                    host_trends[metric_name] = {
                        'trend_percentage': trend,
                        'direction': 'increasing' if trend > 5 else 'decreasing' if trend < -5 else 'stable',
                        'recent_average': recent_avg,
                        'data_points': len(history)
                    }
            
            if host_trends:
                trends[hostname] = host_trends
        
        return trends