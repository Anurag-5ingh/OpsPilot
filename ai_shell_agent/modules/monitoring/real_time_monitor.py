"""
Real-time System Monitoring

Proactive system health tracking with real-time metrics collection, anomaly detection,
and performance monitoring. Includes intelligent alerting and automated recommendations.
"""

import asyncio
import json
import threading
import time
import psutil
import platform
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from collections import deque, defaultdict
import logging
import statistics
from pathlib import Path
import subprocess
import socket
import requests

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib

from ...utils.logging_utils import get_logger

logger = get_logger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(Enum):
    """Types of system metrics"""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    PROCESS = "process"
    SERVICE = "service"
    CUSTOM = "custom"


class MonitoringStatus(Enum):
    """Monitoring system status"""
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class SystemMetric:
    """System metric data point"""
    metric_name: str
    metric_type: MetricType
    value: float
    unit: str
    timestamp: datetime
    hostname: str
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'metric_name': self.metric_name,
            'metric_type': self.metric_type.value,
            'value': self.value,
            'unit': self.unit,
            'timestamp': self.timestamp.isoformat(),
            'hostname': self.hostname,
            'metadata': self.metadata or {}
        }


@dataclass
class SystemAlert:
    """System alert/notification"""
    alert_id: str
    title: str
    description: str
    severity: AlertSeverity
    metric_name: str
    current_value: float
    threshold_value: float
    timestamp: datetime
    hostname: str
    recommendations: List[str] = None
    auto_resolve: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'alert_id': self.alert_id,
            'title': self.title,
            'description': self.description,
            'severity': self.severity.value,
            'metric_name': self.metric_name,
            'current_value': self.current_value,
            'threshold_value': self.threshold_value,
            'timestamp': self.timestamp.isoformat(),
            'hostname': self.hostname,
            'recommendations': self.recommendations or [],
            'auto_resolve': self.auto_resolve
        }


@dataclass
class MonitoringConfig:
    """Configuration for monitoring system"""
    collection_interval: int = 30  # seconds
    retention_hours: int = 24
    anomaly_detection_enabled: bool = True
    alert_thresholds: Dict[str, float] = None
    monitored_services: List[str] = None
    custom_metrics: List[str] = None
    notification_channels: List[str] = None


class MetricCollector:
    """Collects system metrics from various sources"""
    
    def __init__(self):
        self.hostname = platform.node()
        self.collectors = {
            MetricType.CPU: self._collect_cpu_metrics,
            MetricType.MEMORY: self._collect_memory_metrics,
            MetricType.DISK: self._collect_disk_metrics,
            MetricType.NETWORK: self._collect_network_metrics,
            MetricType.PROCESS: self._collect_process_metrics,
            MetricType.SERVICE: self._collect_service_metrics
        }
    
    def collect_all_metrics(self) -> List[SystemMetric]:
        """Collect all available system metrics"""
        metrics = []
        timestamp = datetime.now()
        
        for metric_type, collector_func in self.collectors.items():
            try:
                metric_data = collector_func(timestamp)
                metrics.extend(metric_data)
            except Exception as e:
                logger.error(f"Error collecting {metric_type.value} metrics: {e}")
        
        return metrics
    
    def _collect_cpu_metrics(self, timestamp: datetime) -> List[SystemMetric]:
        """Collect CPU-related metrics"""
        metrics = []
        
        try:
            # CPU usage percentage
            cpu_percent = psutil.cpu_percent(interval=1)
            metrics.append(SystemMetric(
                metric_name="cpu.usage_percent",
                metric_type=MetricType.CPU,
                value=cpu_percent,
                unit="percent",
                timestamp=timestamp,
                hostname=self.hostname
            ))
            
            # Per-core CPU usage
            cpu_per_core = psutil.cpu_percent(interval=1, percpu=True)
            for i, usage in enumerate(cpu_per_core):
                metrics.append(SystemMetric(
                    metric_name=f"cpu.core_{i}.usage_percent",
                    metric_type=MetricType.CPU,
                    value=usage,
                    unit="percent",
                    timestamp=timestamp,
                    hostname=self.hostname
                ))
            
            # Load average (Unix-like systems)
            try:
                load_avg = psutil.getloadavg()
                for i, avg in enumerate(['1min', '5min', '15min']):
                    metrics.append(SystemMetric(
                        metric_name=f"cpu.load_avg.{avg}",
                        metric_type=MetricType.CPU,
                        value=load_avg[i],
                        unit="count",
                        timestamp=timestamp,
                        hostname=self.hostname
                    ))
            except AttributeError:
                # Windows doesn't have getloadavg
                pass
            
            # CPU frequency
            cpu_freq = psutil.cpu_freq()
            if cpu_freq:
                metrics.append(SystemMetric(
                    metric_name="cpu.frequency.current",
                    metric_type=MetricType.CPU,
                    value=cpu_freq.current,
                    unit="MHz",
                    timestamp=timestamp,
                    hostname=self.hostname
                ))
        
        except Exception as e:
            logger.error(f"Error collecting CPU metrics: {e}")
        
        return metrics
    
    def _collect_memory_metrics(self, timestamp: datetime) -> List[SystemMetric]:
        """Collect memory-related metrics"""
        metrics = []
        
        try:
            # Virtual memory
            vmem = psutil.virtual_memory()
            metrics.extend([
                SystemMetric("memory.total", MetricType.MEMORY, vmem.total, "bytes", timestamp, self.hostname),
                SystemMetric("memory.available", MetricType.MEMORY, vmem.available, "bytes", timestamp, self.hostname),
                SystemMetric("memory.used", MetricType.MEMORY, vmem.used, "bytes", timestamp, self.hostname),
                SystemMetric("memory.usage_percent", MetricType.MEMORY, vmem.percent, "percent", timestamp, self.hostname),
                SystemMetric("memory.free", MetricType.MEMORY, vmem.free, "bytes", timestamp, self.hostname)
            ])
            
            # Swap memory
            swap = psutil.swap_memory()
            metrics.extend([
                SystemMetric("swap.total", MetricType.MEMORY, swap.total, "bytes", timestamp, self.hostname),
                SystemMetric("swap.used", MetricType.MEMORY, swap.used, "bytes", timestamp, self.hostname),
                SystemMetric("swap.free", MetricType.MEMORY, swap.free, "bytes", timestamp, self.hostname),
                SystemMetric("swap.usage_percent", MetricType.MEMORY, swap.percent, "percent", timestamp, self.hostname)
            ])
        
        except Exception as e:
            logger.error(f"Error collecting memory metrics: {e}")
        
        return metrics
    
    def _collect_disk_metrics(self, timestamp: datetime) -> List[SystemMetric]:
        """Collect disk-related metrics"""
        metrics = []
        
        try:
            # Disk usage for each partition
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    device = partition.device.replace(':', '').replace('\\', '_').replace('/', '_')
                    
                    metrics.extend([
                        SystemMetric(f"disk.{device}.total", MetricType.DISK, usage.total, "bytes", timestamp, self.hostname),
                        SystemMetric(f"disk.{device}.used", MetricType.DISK, usage.used, "bytes", timestamp, self.hostname),
                        SystemMetric(f"disk.{device}.free", MetricType.DISK, usage.free, "bytes", timestamp, self.hostname),
                        SystemMetric(f"disk.{device}.usage_percent", MetricType.DISK, 
                                   (usage.used / usage.total) * 100 if usage.total > 0 else 0, 
                                   "percent", timestamp, self.hostname)
                    ])
                except (PermissionError, FileNotFoundError):
                    continue
            
            # Disk I/O statistics
            disk_io = psutil.disk_io_counters()
            if disk_io:
                metrics.extend([
                    SystemMetric("disk.io.read_count", MetricType.DISK, disk_io.read_count, "count", timestamp, self.hostname),
                    SystemMetric("disk.io.write_count", MetricType.DISK, disk_io.write_count, "count", timestamp, self.hostname),
                    SystemMetric("disk.io.read_bytes", MetricType.DISK, disk_io.read_bytes, "bytes", timestamp, self.hostname),
                    SystemMetric("disk.io.write_bytes", MetricType.DISK, disk_io.write_bytes, "bytes", timestamp, self.hostname),
                    SystemMetric("disk.io.read_time", MetricType.DISK, disk_io.read_time, "ms", timestamp, self.hostname),
                    SystemMetric("disk.io.write_time", MetricType.DISK, disk_io.write_time, "ms", timestamp, self.hostname)
                ])
        
        except Exception as e:
            logger.error(f"Error collecting disk metrics: {e}")
        
        return metrics
    
    def _collect_network_metrics(self, timestamp: datetime) -> List[SystemMetric]:
        """Collect network-related metrics"""
        metrics = []
        
        try:
            # Network I/O statistics
            net_io = psutil.net_io_counters()
            if net_io:
                metrics.extend([
                    SystemMetric("network.bytes_sent", MetricType.NETWORK, net_io.bytes_sent, "bytes", timestamp, self.hostname),
                    SystemMetric("network.bytes_recv", MetricType.NETWORK, net_io.bytes_recv, "bytes", timestamp, self.hostname),
                    SystemMetric("network.packets_sent", MetricType.NETWORK, net_io.packets_sent, "count", timestamp, self.hostname),
                    SystemMetric("network.packets_recv", MetricType.NETWORK, net_io.packets_recv, "count", timestamp, self.hostname),
                    SystemMetric("network.errin", MetricType.NETWORK, net_io.errin, "count", timestamp, self.hostname),
                    SystemMetric("network.errout", MetricType.NETWORK, net_io.errout, "count", timestamp, self.hostname),
                    SystemMetric("network.dropin", MetricType.NETWORK, net_io.dropin, "count", timestamp, self.hostname),
                    SystemMetric("network.dropout", MetricType.NETWORK, net_io.dropout, "count", timestamp, self.hostname)
                ])
            
            # Network connections
            connections = psutil.net_connections()
            connection_states = defaultdict(int)
            for conn in connections:
                connection_states[conn.status] += 1
            
            for state, count in connection_states.items():
                metrics.append(SystemMetric(
                    f"network.connections.{state.lower()}",
                    MetricType.NETWORK,
                    count,
                    "count",
                    timestamp,
                    self.hostname
                ))
        
        except Exception as e:
            logger.error(f"Error collecting network metrics: {e}")
        
        return metrics
    
    def _collect_process_metrics(self, timestamp: datetime) -> List[SystemMetric]:
        """Collect process-related metrics"""
        metrics = []
        
        try:
            # Process count
            process_count = len(psutil.pids())
            metrics.append(SystemMetric(
                "process.count",
                MetricType.PROCESS,
                process_count,
                "count",
                timestamp,
                self.hostname
            ))
            
            # Top processes by CPU and Memory
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # Sort by CPU usage and take top 5
            cpu_sorted = sorted(processes, key=lambda x: x.get('cpu_percent', 0), reverse=True)[:5]
            for i, proc in enumerate(cpu_sorted):
                metrics.append(SystemMetric(
                    f"process.top_cpu.{i}.usage",
                    MetricType.PROCESS,
                    proc.get('cpu_percent', 0),
                    "percent",
                    timestamp,
                    self.hostname,
                    metadata={'process_name': proc.get('name', 'unknown'), 'pid': proc.get('pid')}
                ))
            
            # Sort by Memory usage and take top 5
            mem_sorted = sorted(processes, key=lambda x: x.get('memory_percent', 0), reverse=True)[:5]
            for i, proc in enumerate(mem_sorted):
                metrics.append(SystemMetric(
                    f"process.top_memory.{i}.usage",
                    MetricType.PROCESS,
                    proc.get('memory_percent', 0),
                    "percent",
                    timestamp,
                    self.hostname,
                    metadata={'process_name': proc.get('name', 'unknown'), 'pid': proc.get('pid')}
                ))
        
        except Exception as e:
            logger.error(f"Error collecting process metrics: {e}")
        
        return metrics
    
    def _collect_service_metrics(self, timestamp: datetime) -> List[SystemMetric]:
        """Collect service status metrics"""
        metrics = []
        
        try:
            # Check common services (platform-dependent)
            if platform.system().lower() == 'linux':
                services_to_check = ['ssh', 'nginx', 'apache2', 'mysql', 'postgresql', 'redis', 'docker']
            elif platform.system().lower() == 'windows':
                services_to_check = ['W32Time', 'Spooler', 'MSSQLSERVER', 'IIS', 'Docker Desktop Service']
            else:
                services_to_check = []
            
            for service_name in services_to_check:
                try:
                    status = self._check_service_status(service_name)
                    metrics.append(SystemMetric(
                        f"service.{service_name}.status",
                        MetricType.SERVICE,
                        1.0 if status else 0.0,
                        "boolean",
                        timestamp,
                        self.hostname,
                        metadata={'service_name': service_name}
                    ))
                except Exception:
                    # Service doesn't exist or can't be checked
                    pass
        
        except Exception as e:
            logger.error(f"Error collecting service metrics: {e}")
        
        return metrics
    
    def _check_service_status(self, service_name: str) -> bool:
        """Check if a service is running"""
        try:
            if platform.system().lower() == 'linux':
                result = subprocess.run(['systemctl', 'is-active', service_name], 
                                      capture_output=True, text=True, timeout=5)
                return result.returncode == 0
            elif platform.system().lower() == 'windows':
                result = subprocess.run(['sc', 'query', service_name], 
                                      capture_output=True, text=True, timeout=5)
                return 'RUNNING' in result.stdout
            else:
                return False
        except Exception:
            return False


class AnomalyDetector:
    """Detects anomalies in system metrics using ML"""
    
    def __init__(self, contamination: float = 0.1):
        self.contamination = contamination
        self.models = {}
        self.scalers = {}
        self.training_data = defaultdict(list)
        self.min_training_samples = 50
        
    def add_training_data(self, metric: SystemMetric):
        """Add metric data for training anomaly detection models"""
        key = f"{metric.metric_name}_{metric.hostname}"
        self.training_data[key].append([metric.value, metric.timestamp.timestamp()])
        
        # Keep only recent data for training (sliding window)
        cutoff_time = (datetime.now() - timedelta(hours=24)).timestamp()
        self.training_data[key] = [
            data for data in self.training_data[key] if data[1] >= cutoff_time
        ]
    
    def train_models(self):
        """Train anomaly detection models for each metric"""
        for key, data in self.training_data.items():
            if len(data) >= self.min_training_samples:
                try:
                    # Prepare training data
                    values = [point[0] for point in data]
                    X = np.array(values).reshape(-1, 1)
                    
                    # Scale the data
                    scaler = StandardScaler()
                    X_scaled = scaler.fit_transform(X)
                    
                    # Train Isolation Forest
                    model = IsolationForest(
                        contamination=self.contamination,
                        random_state=42,
                        n_estimators=100
                    )
                    model.fit(X_scaled)
                    
                    # Store model and scaler
                    self.models[key] = model
                    self.scalers[key] = scaler
                    
                    logger.debug(f"Trained anomaly detection model for {key}")
                
                except Exception as e:
                    logger.error(f"Failed to train model for {key}: {e}")
    
    def detect_anomaly(self, metric: SystemMetric) -> Tuple[bool, float]:
        """
        Detect if a metric value is anomalous
        
        Returns:
            (is_anomaly, anomaly_score)
        """
        key = f"{metric.metric_name}_{metric.hostname}"
        
        if key not in self.models or key not in self.scalers:
            return False, 0.0
        
        try:
            # Prepare data
            X = np.array([[metric.value]])
            X_scaled = self.scalers[key].transform(X)
            
            # Predict anomaly
            is_anomaly = self.models[key].predict(X_scaled)[0] == -1
            anomaly_score = abs(self.models[key].decision_function(X_scaled)[0])
            
            return is_anomaly, anomaly_score
        
        except Exception as e:
            logger.error(f"Error detecting anomaly for {key}: {e}")
            return False, 0.0
    
    def save_models(self, model_dir: Path):
        """Save trained models to disk"""
        try:
            model_dir.mkdir(parents=True, exist_ok=True)
            
            for key, model in self.models.items():
                model_file = model_dir / f"{key}_model.joblib"
                scaler_file = model_dir / f"{key}_scaler.joblib"
                
                joblib.dump(model, model_file)
                joblib.dump(self.scalers[key], scaler_file)
            
            logger.info(f"Saved {len(self.models)} anomaly detection models")
        
        except Exception as e:
            logger.error(f"Error saving models: {e}")
    
    def load_models(self, model_dir: Path):
        """Load trained models from disk"""
        try:
            if not model_dir.exists():
                return
            
            model_files = list(model_dir.glob("*_model.joblib"))
            
            for model_file in model_files:
                key = model_file.stem.replace('_model', '')
                scaler_file = model_dir / f"{key}_scaler.joblib"
                
                if scaler_file.exists():
                    self.models[key] = joblib.load(model_file)
                    self.scalers[key] = joblib.load(scaler_file)
            
            logger.info(f"Loaded {len(self.models)} anomaly detection models")
        
        except Exception as e:
            logger.error(f"Error loading models: {e}")


class AlertManager:
    """Manages system alerts and notifications"""
    
    def __init__(self):
        self.active_alerts = {}
        self.alert_history = deque(maxlen=1000)
        self.alert_thresholds = self._get_default_thresholds()
        self.notification_callbacks = []
    
    def _get_default_thresholds(self) -> Dict[str, Dict[str, float]]:
        """Get default alert thresholds"""
        return {
            'cpu.usage_percent': {'warning': 80.0, 'critical': 95.0},
            'memory.usage_percent': {'warning': 85.0, 'critical': 95.0},
            'disk.*.usage_percent': {'warning': 85.0, 'critical': 95.0},
            'cpu.load_avg.1min': {'warning': 5.0, 'critical': 10.0},
            'swap.usage_percent': {'warning': 50.0, 'critical': 80.0}
        }
    
    def check_thresholds(self, metrics: List[SystemMetric]) -> List[SystemAlert]:
        """Check metrics against thresholds and generate alerts"""
        alerts = []
        
        for metric in metrics:
            # Check threshold-based alerts
            threshold_alert = self._check_threshold_alert(metric)
            if threshold_alert:
                alerts.append(threshold_alert)
        
        return alerts
    
    def _check_threshold_alert(self, metric: SystemMetric) -> Optional[SystemAlert]:
        """Check if metric exceeds threshold"""
        # Find matching threshold pattern
        threshold_config = None
        
        for pattern, config in self.alert_thresholds.items():
            if self._metric_matches_pattern(metric.metric_name, pattern):
                threshold_config = config
                break
        
        if not threshold_config:
            return None
        
        # Determine severity
        severity = None
        threshold_value = None
        
        if metric.value >= threshold_config.get('critical', float('inf')):
            severity = AlertSeverity.CRITICAL
            threshold_value = threshold_config['critical']
        elif metric.value >= threshold_config.get('warning', float('inf')):
            severity = AlertSeverity.WARNING
            threshold_value = threshold_config['warning']
        
        if severity is None:
            return None
        
        # Generate alert ID
        alert_id = f"{metric.hostname}_{metric.metric_name}_{severity.value}"
        
        # Check if this alert is already active
        if alert_id in self.active_alerts:
            return None
        
        # Create alert
        alert = SystemAlert(
            alert_id=alert_id,
            title=f"{severity.value.title()}: {metric.metric_name}",
            description=f"{metric.metric_name} is {metric.value:.1f}{metric.unit} (threshold: {threshold_value})",
            severity=severity,
            metric_name=metric.metric_name,
            current_value=metric.value,
            threshold_value=threshold_value,
            timestamp=metric.timestamp,
            hostname=metric.hostname,
            recommendations=self._get_recommendations(metric),
            auto_resolve=True
        )
        
        return alert
    
    def _metric_matches_pattern(self, metric_name: str, pattern: str) -> bool:
        """Check if metric name matches threshold pattern"""
        if '*' in pattern:
            pattern_parts = pattern.split('*')
            if len(pattern_parts) == 2:
                prefix, suffix = pattern_parts
                return metric_name.startswith(prefix) and metric_name.endswith(suffix)
        
        return metric_name == pattern
    
    def _get_recommendations(self, metric: SystemMetric) -> List[str]:
        """Get recommendations based on metric type and value"""
        recommendations = []
        
        if metric.metric_name.startswith('cpu'):
            recommendations.extend([
                "Check for high CPU processes using 'top' or 'htop'",
                "Consider killing unnecessary processes",
                "Review resource-intensive applications",
                "Check for runaway processes or infinite loops"
            ])
        
        elif metric.metric_name.startswith('memory'):
            recommendations.extend([
                "Identify memory-heavy processes using 'ps aux --sort=-%mem'",
                "Clear system cache if safe: 'echo 3 > /proc/sys/vm/drop_caches'",
                "Check for memory leaks in applications",
                "Consider adding more RAM or optimizing applications"
            ])
        
        elif metric.metric_name.startswith('disk'):
            recommendations.extend([
                "Clean up log files and temporary files",
                "Use 'du -sh *' to identify large directories",
                "Consider archiving or deleting old files",
                "Check for core dumps or crash files"
            ])
        
        elif metric.metric_name.startswith('network'):
            recommendations.extend([
                "Check network connections with 'netstat -tuln'",
                "Monitor bandwidth usage",
                "Look for unusual network activity",
                "Check firewall rules and security"
            ])
        
        return recommendations[:3]  # Limit to top 3 recommendations
    
    def add_alert(self, alert: SystemAlert):
        """Add an alert to the system"""
        self.active_alerts[alert.alert_id] = alert
        self.alert_history.append(alert)
        
        # Notify callbacks
        for callback in self.notification_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Notification callback failed: {e}")
        
        logger.info(f"Added {alert.severity.value} alert: {alert.title}")
    
    def resolve_alert(self, alert_id: str, reason: str = "Auto-resolved"):
        """Resolve an active alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            del self.active_alerts[alert_id]
            
            logger.info(f"Resolved alert: {alert.title} ({reason})")
    
    def check_auto_resolve(self, metrics: List[SystemMetric]):
        """Check if any active alerts should be auto-resolved"""
        to_resolve = []
        
        for alert_id, alert in self.active_alerts.items():
            if not alert.auto_resolve:
                continue
            
            # Find corresponding current metric
            current_metric = None
            for metric in metrics:
                if (metric.metric_name == alert.metric_name and 
                    metric.hostname == alert.hostname):
                    current_metric = metric
                    break
            
            if current_metric:
                # Check if value is now below threshold
                if alert.severity == AlertSeverity.CRITICAL:
                    resolve_threshold = alert.threshold_value * 0.9  # 90% of critical threshold
                else:
                    resolve_threshold = alert.threshold_value * 0.85  # 85% of warning threshold
                
                if current_metric.value < resolve_threshold:
                    to_resolve.append((alert_id, f"Value dropped to {current_metric.value:.1f}"))
        
        # Resolve alerts
        for alert_id, reason in to_resolve:
            self.resolve_alert(alert_id, reason)
    
    def get_active_alerts(self) -> List[SystemAlert]:
        """Get all active alerts"""
        return list(self.active_alerts.values())
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of alert status"""
        active_alerts = list(self.active_alerts.values())
        
        severity_counts = defaultdict(int)
        for alert in active_alerts:
            severity_counts[alert.severity.value] += 1
        
        return {
            'total_active': len(active_alerts),
            'by_severity': dict(severity_counts),
            'total_history': len(self.alert_history),
            'latest_alert': active_alerts[-1].timestamp.isoformat() if active_alerts else None
        }
    
    def add_notification_callback(self, callback: Callable[[SystemAlert], None]):
        """Add notification callback for alerts"""
        self.notification_callbacks.append(callback)


class RealTimeMonitor:
    """
    Main real-time system monitoring system with proactive health tracking,
    anomaly detection, and intelligent alerting.
    """
    
    def __init__(self, config: Optional[MonitoringConfig] = None, 
                 model_dir: Optional[str] = None):
        """Initialize real-time monitoring system"""
        self.config = config or MonitoringConfig()
        self.model_dir = Path(model_dir or "monitoring_models")
        
        # Components
        self.metric_collector = MetricCollector()
        self.anomaly_detector = AnomalyDetector()
        self.alert_manager = AlertManager()
        
        # State
        self.status = MonitoringStatus.STOPPED
        self.metrics_history = deque(maxlen=10000)  # Store recent metrics
        self.last_collection_time = datetime.min
        
        # Threading
        self.monitoring_thread = None
        self.stop_event = threading.Event()
        
        # Callbacks
        self.metric_callbacks = []
        self.alert_callbacks = []
        
        # Load existing models
        self.anomaly_detector.load_models(self.model_dir)
        
        logger.info("Real-time monitor initialized")
    
    def start_monitoring(self):
        """Start the monitoring system"""
        if self.status == MonitoringStatus.RUNNING:
            logger.warning("Monitoring is already running")
            return
        
        self.status = MonitoringStatus.STARTING
        self.stop_event.clear()
        
        # Start monitoring thread
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        self.status = MonitoringStatus.RUNNING
        logger.info("Real-time monitoring started")
    
    def stop_monitoring(self):
        """Stop the monitoring system"""
        if self.status != MonitoringStatus.RUNNING:
            return
        
        self.status = MonitoringStatus.STOPPING
        self.stop_event.set()
        
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=10)
        
        # Save models before stopping
        self.anomaly_detector.save_models(self.model_dir)
        
        self.status = MonitoringStatus.STOPPED
        logger.info("Real-time monitoring stopped")
    
    def pause_monitoring(self):
        """Pause monitoring (keeps thread alive but stops collection)"""
        if self.status == MonitoringStatus.RUNNING:
            self.status = MonitoringStatus.PAUSED
            logger.info("Real-time monitoring paused")
    
    def resume_monitoring(self):
        """Resume monitoring from paused state"""
        if self.status == MonitoringStatus.PAUSED:
            self.status = MonitoringStatus.RUNNING
            logger.info("Real-time monitoring resumed")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        logger.info("Monitoring loop started")
        
        model_training_counter = 0
        
        while not self.stop_event.is_set():
            try:
                if self.status == MonitoringStatus.RUNNING:
                    # Collect metrics
                    metrics = self.metric_collector.collect_all_metrics()
                    
                    if metrics:
                        # Store metrics
                        self.metrics_history.extend(metrics)
                        self.last_collection_time = datetime.now()
                        
                        # Add to anomaly detection training data
                        for metric in metrics:
                            self.anomaly_detector.add_training_data(metric)
                        
                        # Check for anomalies
                        anomalies = []
                        for metric in metrics:
                            is_anomaly, score = self.anomaly_detector.detect_anomaly(metric)
                            if is_anomaly:
                                anomalies.append((metric, score))
                        
                        # Generate threshold-based alerts
                        threshold_alerts = self.alert_manager.check_thresholds(metrics)
                        
                        # Generate anomaly-based alerts
                        anomaly_alerts = self._create_anomaly_alerts(anomalies)
                        
                        # Add all alerts
                        for alert in threshold_alerts + anomaly_alerts:
                            self.alert_manager.add_alert(alert)
                        
                        # Check for alert resolution
                        self.alert_manager.check_auto_resolve(metrics)
                        
                        # Notify callbacks
                        for callback in self.metric_callbacks:
                            try:
                                callback(metrics)
                            except Exception as e:
                                logger.error(f"Metric callback failed: {e}")
                        
                        # Train models periodically
                        model_training_counter += 1
                        if model_training_counter >= 10:  # Every 10 cycles
                            self.anomaly_detector.train_models()
                            model_training_counter = 0
                
                # Clean up old metrics
                self._cleanup_old_metrics()
                
                # Wait for next collection
                time.sleep(self.config.collection_interval)
            
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                self.status = MonitoringStatus.ERROR
                time.sleep(10)  # Wait before retrying
        
        logger.info("Monitoring loop stopped")
    
    def _create_anomaly_alerts(self, anomalies: List[Tuple[SystemMetric, float]]) -> List[SystemAlert]:
        """Create alerts for detected anomalies"""
        alerts = []
        
        for metric, anomaly_score in anomalies:
            alert_id = f"{metric.hostname}_{metric.metric_name}_anomaly"
            
            # Don't create duplicate anomaly alerts
            if alert_id in self.alert_manager.active_alerts:
                continue
            
            severity = AlertSeverity.WARNING if anomaly_score < 0.7 else AlertSeverity.ERROR
            
            alert = SystemAlert(
                alert_id=alert_id,
                title=f"Anomaly Detected: {metric.metric_name}",
                description=f"Unusual value detected for {metric.metric_name}: {metric.value:.1f}{metric.unit} (anomaly score: {anomaly_score:.2f})",
                severity=severity,
                metric_name=metric.metric_name,
                current_value=metric.value,
                threshold_value=anomaly_score,
                timestamp=metric.timestamp,
                hostname=metric.hostname,
                recommendations=["Investigate recent changes", "Check system logs", "Monitor for patterns"],
                auto_resolve=True
            )
            
            alerts.append(alert)
        
        return alerts
    
    def _cleanup_old_metrics(self):
        """Remove old metrics from memory"""
        cutoff_time = datetime.now() - timedelta(hours=self.config.retention_hours)
        
        # Clean metrics history
        while self.metrics_history and self.metrics_history[0].timestamp < cutoff_time:
            self.metrics_history.popleft()
    
    def get_current_metrics(self, metric_types: Optional[List[MetricType]] = None) -> List[SystemMetric]:
        """Get most recent metrics"""
        if not self.metrics_history:
            return []
        
        # Get latest metrics (from last collection)
        latest_time = self.metrics_history[-1].timestamp
        threshold = latest_time - timedelta(seconds=self.config.collection_interval * 2)
        
        recent_metrics = [
            metric for metric in self.metrics_history 
            if metric.timestamp >= threshold
        ]
        
        # Filter by metric types if specified
        if metric_types:
            recent_metrics = [
                metric for metric in recent_metrics 
                if metric.metric_type in metric_types
            ]
        
        return recent_metrics
    
    def get_metric_history(self, metric_name: str, hours_back: int = 1) -> List[SystemMetric]:
        """Get historical data for a specific metric"""
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        
        return [
            metric for metric in self.metrics_history 
            if metric.metric_name == metric_name and metric.timestamp >= cutoff_time
        ]
    
    def get_system_health_summary(self) -> Dict[str, Any]:
        """Get overall system health summary"""
        current_metrics = self.get_current_metrics()
        active_alerts = self.alert_manager.get_active_alerts()
        
        # Calculate health score (0-100)
        health_score = 100
        
        # Penalize for active alerts
        for alert in active_alerts:
            if alert.severity == AlertSeverity.CRITICAL:
                health_score -= 20
            elif alert.severity == AlertSeverity.ERROR:
                health_score -= 10
            elif alert.severity == AlertSeverity.WARNING:
                health_score -= 5
        
        health_score = max(0, health_score)
        
        # Determine status
        if health_score >= 90:
            status = "healthy"
        elif health_score >= 70:
            status = "warning"
        elif health_score >= 50:
            status = "degraded"
        else:
            status = "critical"
        
        # Key metrics
        key_metrics = {}
        for metric in current_metrics:
            if metric.metric_name in ['cpu.usage_percent', 'memory.usage_percent', 'disk.usage_percent']:
                key_metrics[metric.metric_name] = {
                    'value': metric.value,
                    'unit': metric.unit,
                    'timestamp': metric.timestamp.isoformat()
                }
        
        return {
            'health_score': health_score,
            'status': status,
            'monitoring_status': self.status.value,
            'last_collection': self.last_collection_time.isoformat() if self.last_collection_time > datetime.min else None,
            'active_alerts_count': len(active_alerts),
            'metrics_collected': len(self.metrics_history),
            'key_metrics': key_metrics,
            'alert_summary': self.alert_manager.get_alert_summary()
        }
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get detailed monitoring system status"""
        return {
            'status': self.status.value,
            'uptime': (datetime.now() - self.last_collection_time).total_seconds() if self.last_collection_time > datetime.min else 0,
            'collection_interval': self.config.collection_interval,
            'retention_hours': self.config.retention_hours,
            'anomaly_detection_enabled': self.config.anomaly_detection_enabled,
            'metrics_in_memory': len(self.metrics_history),
            'trained_models': len(self.anomaly_detector.models),
            'active_alerts': len(self.alert_manager.active_alerts),
            'alert_history_size': len(self.alert_manager.alert_history)
        }
    
    def add_metric_callback(self, callback: Callable[[List[SystemMetric]], None]):
        """Add callback for new metrics"""
        self.metric_callbacks.append(callback)
    
    def add_alert_callback(self, callback: Callable[[SystemAlert], None]):
        """Add callback for new alerts"""
        self.alert_manager.add_notification_callback(callback)
    
    def set_alert_threshold(self, metric_pattern: str, warning: float = None, critical: float = None):
        """Set custom alert thresholds"""
        if metric_pattern not in self.alert_manager.alert_thresholds:
            self.alert_manager.alert_thresholds[metric_pattern] = {}
        
        if warning is not None:
            self.alert_manager.alert_thresholds[metric_pattern]['warning'] = warning
        if critical is not None:
            self.alert_manager.alert_thresholds[metric_pattern]['critical'] = critical
        
        logger.info(f"Updated alert thresholds for {metric_pattern}")
    
    def cleanup(self):
        """Cleanup monitoring system"""
        self.stop_monitoring()
        logger.info("Real-time monitor cleanup completed")