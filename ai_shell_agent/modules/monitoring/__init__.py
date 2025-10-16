"""
Real-time System Monitoring Module

Proactive system health tracking with real-time metrics collection, anomaly detection,
and performance monitoring. Includes intelligent alerting and automated recommendations.
"""

from .real_time_monitor import (
    RealTimeMonitor,
    MonitoringConfig,
    MetricCollector,
    AnomalyDetector,
    AlertManager,
    SystemMetric,
    SystemAlert,
    AlertSeverity,
    MetricType,
    MonitoringStatus
)

__all__ = [
    'RealTimeMonitor',
    'MonitoringConfig',
    'MetricCollector', 
    'AnomalyDetector',
    'AlertManager',
    'SystemMetric',
    'SystemAlert',
    'AlertSeverity',
    'MetricType',
    'MonitoringStatus'
]

__version__ = "1.0.0"