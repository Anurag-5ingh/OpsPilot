"""
Predictive Failure Prevention

ML-powered failure prediction system that analyzes historical data, system patterns,
and current metrics to predict and prevent potential failures before they occur.
Includes early warning systems and preventive action recommendations.
"""

import json
import threading
import time
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Callable, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import logging
from pathlib import Path
import pickle
import hashlib

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.feature_selection import SelectKBest, f_classif
import joblib

from ...utils.logging_utils import get_logger

logger = get_logger(__name__)


class FailureType(Enum):
    """Types of system failures"""
    DISK_SPACE = "disk_space"
    MEMORY_EXHAUSTION = "memory_exhaustion" 
    CPU_OVERLOAD = "cpu_overload"
    SERVICE_CRASH = "service_crash"
    NETWORK_CONGESTION = "network_congestion"
    PROCESS_HANG = "process_hang"
    SECURITY_BREACH = "security_breach"
    CONFIGURATION_ERROR = "configuration_error"
    DEPENDENCY_FAILURE = "dependency_failure"
    PERFORMANCE_DEGRADATION = "performance_degradation"


class PredictionConfidence(Enum):
    """Confidence levels for predictions"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class PreventionAction(Enum):
    """Types of preventive actions"""
    ALERT_ONLY = "alert_only"
    AUTO_CLEANUP = "auto_cleanup"
    SCALE_RESOURCES = "scale_resources"
    RESTART_SERVICE = "restart_service"
    APPLY_CONFIGURATION = "apply_configuration"
    KILL_PROCESS = "kill_process"
    BLOCK_TRAFFIC = "block_traffic"
    BACKUP_DATA = "backup_data"
    NOTIFY_ADMIN = "notify_admin"


@dataclass
class FailurePattern:
    """Pattern that leads to system failures"""
    pattern_id: str
    failure_type: FailureType
    preconditions: Dict[str, Any]
    time_to_failure: int  # seconds
    occurrence_count: int
    success_prevention_count: int
    confidence_score: float
    last_occurrence: datetime
    prevention_actions: List[PreventionAction]
    feature_importance: Dict[str, float]


@dataclass
class FailurePrediction:
    """Prediction of potential failure"""
    prediction_id: str
    failure_type: FailureType
    confidence: PredictionConfidence
    probability: float
    estimated_time_to_failure: int  # seconds
    contributing_factors: Dict[str, float]
    recommended_actions: List[Dict[str, Any]]
    timestamp: datetime
    hostname: str
    is_critical: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'prediction_id': self.prediction_id,
            'failure_type': self.failure_type.value,
            'confidence': self.confidence.value,
            'probability': self.probability,
            'estimated_time_to_failure': self.estimated_time_to_failure,
            'contributing_factors': self.contributing_factors,
            'recommended_actions': self.recommended_actions,
            'timestamp': self.timestamp.isoformat(),
            'hostname': self.hostname,
            'is_critical': self.is_critical
        }


@dataclass
class PreventionAction:
    """Preventive action to take"""
    action_id: str
    action_type: PreventionAction
    command: str
    description: str
    risk_level: int  # 1-10 scale
    estimated_effectiveness: float
    prerequisites: List[str]
    rollback_command: Optional[str] = None
    auto_execute: bool = False


@dataclass
class SystemSnapshot:
    """Snapshot of system state at a point in time"""
    timestamp: datetime
    hostname: str
    metrics: Dict[str, float]
    processes: List[Dict[str, Any]]
    services: List[Dict[str, Any]]
    network_connections: List[Dict[str, Any]]
    disk_usage: Dict[str, float]
    system_load: Dict[str, float]
    recent_events: List[Dict[str, Any]]


class FeatureExtractor:
    """Extracts features for failure prediction models"""
    
    def __init__(self):
        self.feature_history = defaultdict(deque)
        self.window_sizes = [5, 10, 30, 60]  # minutes
        
    def extract_features(self, snapshot: SystemSnapshot, 
                        history: List[SystemSnapshot]) -> Dict[str, float]:
        """Extract features from system snapshot and history"""
        features = {}
        
        # Current state features
        features.update(self._extract_current_state_features(snapshot))
        
        # Trend features
        features.update(self._extract_trend_features(snapshot, history))
        
        # Pattern features
        features.update(self._extract_pattern_features(snapshot, history))
        
        # Time-based features
        features.update(self._extract_temporal_features(snapshot))
        
        return features
    
    def _extract_current_state_features(self, snapshot: SystemSnapshot) -> Dict[str, float]:
        """Extract features from current system state"""
        features = {}
        
        # System metrics
        for metric_name, value in snapshot.metrics.items():
            features[f"current_{metric_name}"] = value
        
        # Process count and resource usage
        if snapshot.processes:
            features['process_count'] = len(snapshot.processes)
            features['high_cpu_processes'] = len([p for p in snapshot.processes 
                                                 if p.get('cpu_percent', 0) > 50])
            features['high_mem_processes'] = len([p for p in snapshot.processes 
                                                 if p.get('memory_percent', 0) > 20])
        
        # Service status
        if snapshot.services:
            features['total_services'] = len(snapshot.services)
            features['running_services'] = len([s for s in snapshot.services 
                                              if s.get('status') == 'running'])
            features['failed_services'] = len([s for s in snapshot.services 
                                             if s.get('status') in ['failed', 'error']])
        
        # Network connections
        if snapshot.network_connections:
            features['total_connections'] = len(snapshot.network_connections)
            features['established_connections'] = len([c for c in snapshot.network_connections 
                                                     if c.get('status') == 'ESTABLISHED'])
            features['listening_ports'] = len([c for c in snapshot.network_connections 
                                             if c.get('status') == 'LISTEN'])
        
        # Disk usage patterns
        for disk, usage in snapshot.disk_usage.items():
            features[f"disk_{disk}_usage"] = usage
        
        # System load
        for load_type, value in snapshot.system_load.items():
            features[f"load_{load_type}"] = value
        
        return features
    
    def _extract_trend_features(self, current: SystemSnapshot, 
                               history: List[SystemSnapshot]) -> Dict[str, float]:
        """Extract trend-based features"""
        features = {}
        
        if len(history) < 2:
            return features
        
        # Sort history by timestamp
        sorted_history = sorted(history, key=lambda x: x.timestamp)
        
        # Calculate trends for key metrics
        key_metrics = ['cpu.usage_percent', 'memory.usage_percent', 'disk.usage_percent']
        
        for metric in key_metrics:
            metric_values = [snap.metrics.get(metric, 0) for snap in sorted_history[-10:]]
            
            if len(metric_values) >= 3:
                # Linear trend
                x = np.arange(len(metric_values))
                trend_coef = np.polyfit(x, metric_values, 1)[0]
                features[f"{metric}_trend"] = trend_coef
                
                # Rate of change
                recent_change = metric_values[-1] - metric_values[-2] if len(metric_values) >= 2 else 0
                features[f"{metric}_rate_change"] = recent_change
                
                # Volatility
                volatility = np.std(metric_values) if len(metric_values) > 1 else 0
                features[f"{metric}_volatility"] = volatility
                
                # Moving average deviation
                ma = np.mean(metric_values)
                deviation = abs(metric_values[-1] - ma) / ma if ma > 0 else 0
                features[f"{metric}_ma_deviation"] = deviation
        
        return features
    
    def _extract_pattern_features(self, current: SystemSnapshot, 
                                 history: List[SystemSnapshot]) -> Dict[str, float]:
        """Extract pattern-based features"""
        features = {}
        
        if len(history) < 5:
            return features
        
        # Look for repeating patterns
        sorted_history = sorted(history, key=lambda x: x.timestamp)[-20:]  # Last 20 snapshots
        
        # CPU spike patterns
        cpu_values = [snap.metrics.get('cpu.usage_percent', 0) for snap in sorted_history]
        features['cpu_spike_frequency'] = len([v for v in cpu_values if v > 90]) / len(cpu_values)
        
        # Memory growth patterns
        mem_values = [snap.metrics.get('memory.usage_percent', 0) for snap in sorted_history]
        if len(mem_values) >= 5:
            # Check if memory is consistently growing
            growing_points = 0
            for i in range(1, len(mem_values)):
                if mem_values[i] > mem_values[i-1]:
                    growing_points += 1
            features['memory_growth_consistency'] = growing_points / (len(mem_values) - 1)
        
        # Service restart patterns
        service_events = []
        for snap in sorted_history:
            for event in snap.recent_events:
                if 'service' in event.get('type', '').lower():
                    service_events.append(event)
        
        features['service_event_frequency'] = len(service_events) / max(len(sorted_history), 1)
        
        # Process creation/termination patterns
        process_counts = [len(snap.processes) for snap in sorted_history if snap.processes]
        if process_counts:
            features['process_count_volatility'] = np.std(process_counts)
            features['process_count_trend'] = (process_counts[-1] - process_counts[0]) / len(process_counts)
        
        return features
    
    def _extract_temporal_features(self, snapshot: SystemSnapshot) -> Dict[str, float]:
        """Extract time-based features"""
        features = {}
        
        current_time = snapshot.timestamp
        
        # Hour of day (0-23)
        features['hour_of_day'] = current_time.hour
        
        # Day of week (0-6)
        features['day_of_week'] = current_time.weekday()
        
        # Business hours indicator
        features['is_business_hours'] = 1 if 9 <= current_time.hour <= 17 else 0
        
        # Weekend indicator
        features['is_weekend'] = 1 if current_time.weekday() >= 5 else 0
        
        # Month of year
        features['month_of_year'] = current_time.month
        
        return features


class FailurePredictionModel:
    """ML models for predicting different types of failures"""
    
    def __init__(self, failure_type: FailureType):
        self.failure_type = failure_type
        self.models = {
            'rf': RandomForestClassifier(n_estimators=100, random_state=42),
            'gb': GradientBoostingClassifier(n_estimators=100, random_state=42),
            'lr': LogisticRegression(random_state=42, max_iter=1000)
        }
        self.scaler = StandardScaler()
        self.feature_selector = SelectKBest(f_classif, k=20)
        self.label_encoder = LabelEncoder()
        
        self.is_trained = False
        self.feature_names = []
        self.model_performance = {}
        self.feature_importance = {}
    
    def train(self, X: pd.DataFrame, y: pd.Series, test_size: float = 0.2):
        """Train the failure prediction models"""
        logger.info(f"Training failure prediction model for {self.failure_type.value}")
        
        if len(X) < 10:
            logger.warning("Insufficient training data")
            return
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Select features
        X_train_selected = self.feature_selector.fit_transform(X_train_scaled, y_train)
        X_test_selected = self.feature_selector.transform(X_test_scaled)
        
        # Store feature names
        feature_mask = self.feature_selector.get_support()
        self.feature_names = X.columns[feature_mask].tolist()
        
        # Train each model
        for model_name, model in self.models.items():
            try:
                # Train model
                model.fit(X_train_selected, y_train)
                
                # Evaluate model
                train_score = model.score(X_train_selected, y_train)
                test_score = model.score(X_test_selected, y_test)
                
                # Cross validation
                cv_scores = cross_val_score(model, X_train_selected, y_train, cv=5)
                
                # ROC AUC for binary classification
                y_pred_proba = model.predict_proba(X_test_selected)[:, 1]
                auc_score = roc_auc_score(y_test, y_pred_proba)
                
                self.model_performance[model_name] = {
                    'train_score': train_score,
                    'test_score': test_score,
                    'cv_mean': cv_scores.mean(),
                    'cv_std': cv_scores.std(),
                    'auc_score': auc_score
                }
                
                # Feature importance (for tree-based models)
                if hasattr(model, 'feature_importances_'):
                    importance_dict = dict(zip(self.feature_names, model.feature_importances_))
                    self.feature_importance[model_name] = importance_dict
                
                logger.info(f"{model_name} - Train: {train_score:.3f}, Test: {test_score:.3f}, AUC: {auc_score:.3f}")
            
            except Exception as e:
                logger.error(f"Error training {model_name} for {self.failure_type.value}: {e}")
        
        self.is_trained = True
        logger.info(f"Training completed for {self.failure_type.value}")
    
    def predict(self, X: pd.DataFrame) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        Predict failure probability
        
        Returns:
            (probabilities_by_model, feature_contributions)
        """
        if not self.is_trained:
            return {}, {}
        
        # Scale features
        X_scaled = self.scaler.transform(X)
        
        # Select features
        X_selected = self.feature_selector.transform(X_scaled)
        
        # Make predictions with each model
        probabilities = {}
        for model_name, model in self.models.items():
            try:
                prob = model.predict_proba(X_selected)[0, 1]  # Probability of positive class
                probabilities[model_name] = prob
            except Exception as e:
                logger.error(f"Error predicting with {model_name}: {e}")
                probabilities[model_name] = 0.0
        
        # Calculate feature contributions (using Random Forest as primary)
        feature_contributions = {}
        if 'rf' in self.models and 'rf' in self.feature_importance:
            for i, feature_name in enumerate(self.feature_names):
                contribution = X_selected[0, i] * self.feature_importance['rf'].get(feature_name, 0)
                feature_contributions[feature_name] = contribution
        
        return probabilities, feature_contributions
    
    def get_ensemble_prediction(self, X: pd.DataFrame) -> float:
        """Get ensemble prediction from all models"""
        probabilities, _ = self.predict(X)
        
        if not probabilities:
            return 0.0
        
        # Weighted average based on model performance
        weights = {}
        for model_name in probabilities.keys():
            perf = self.model_performance.get(model_name, {})
            # Weight by AUC score
            weights[model_name] = perf.get('auc_score', 0.5)
        
        total_weight = sum(weights.values())
        if total_weight == 0:
            return np.mean(list(probabilities.values()))
        
        weighted_sum = sum(prob * weights[model_name] for model_name, prob in probabilities.items())
        return weighted_sum / total_weight
    
    def save_model(self, model_path: Path):
        """Save trained model to disk"""
        try:
            model_data = {
                'failure_type': self.failure_type.value,
                'models': self.models,
                'scaler': self.scaler,
                'feature_selector': self.feature_selector,
                'feature_names': self.feature_names,
                'model_performance': self.model_performance,
                'feature_importance': self.feature_importance,
                'is_trained': self.is_trained
            }
            
            with open(model_path, 'wb') as f:
                pickle.dump(model_data, f)
            
            logger.info(f"Saved model for {self.failure_type.value} to {model_path}")
        
        except Exception as e:
            logger.error(f"Error saving model: {e}")
    
    def load_model(self, model_path: Path):
        """Load trained model from disk"""
        try:
            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)
            
            self.models = model_data['models']
            self.scaler = model_data['scaler']
            self.feature_selector = model_data['feature_selector']
            self.feature_names = model_data['feature_names']
            self.model_performance = model_data['model_performance']
            self.feature_importance = model_data['feature_importance']
            self.is_trained = model_data['is_trained']
            
            logger.info(f"Loaded model for {self.failure_type.value} from {model_path}")
        
        except Exception as e:
            logger.error(f"Error loading model: {e}")


class PreventionActionEngine:
    """Engine for recommending and executing preventive actions"""
    
    def __init__(self):
        self.action_templates = self._load_action_templates()
        self.execution_history = deque(maxlen=1000)
        self.success_rates = defaultdict(lambda: {'successes': 0, 'total': 0})
    
    def _load_action_templates(self) -> Dict[FailureType, List[PreventionAction]]:
        """Load prevention action templates for each failure type"""
        templates = {
            FailureType.DISK_SPACE: [
                PreventionAction(
                    action_id="cleanup_logs",
                    action_type=PreventionAction.AUTO_CLEANUP,
                    command="find /var/log -name '*.log' -type f -mtime +7 -delete",
                    description="Clean up old log files",
                    risk_level=2,
                    estimated_effectiveness=0.7,
                    prerequisites=["root_access"],
                    rollback_command=None,
                    auto_execute=True
                ),
                PreventionAction(
                    action_id="cleanup_temp",
                    action_type=PreventionAction.AUTO_CLEANUP,
                    command="rm -rf /tmp/* /var/tmp/*",
                    description="Clean temporary files",
                    risk_level=3,
                    estimated_effectiveness=0.5,
                    prerequisites=["root_access"],
                    auto_execute=False
                )
            ],
            
            FailureType.MEMORY_EXHAUSTION: [
                PreventionAction(
                    action_id="restart_memory_hogs",
                    action_type=PreventionAction.RESTART_SERVICE,
                    command="systemctl restart $(ps aux --sort=-%mem | head -2 | tail -1 | awk '{print $11}')",
                    description="Restart highest memory consuming service",
                    risk_level=5,
                    estimated_effectiveness=0.8,
                    prerequisites=["service_management"],
                    auto_execute=False
                ),
                PreventionAction(
                    action_id="clear_caches",
                    action_type=PreventionAction.AUTO_CLEANUP,
                    command="echo 3 > /proc/sys/vm/drop_caches",
                    description="Clear system caches",
                    risk_level=2,
                    estimated_effectiveness=0.6,
                    prerequisites=["root_access"],
                    auto_execute=True
                )
            ],
            
            FailureType.CPU_OVERLOAD: [
                PreventionAction(
                    action_id="kill_cpu_hogs",
                    action_type=PreventionAction.KILL_PROCESS,
                    command="kill -TERM $(ps -eo pid,pcpu --sort=-pcpu | head -2 | tail -1 | awk '{print $1}')",
                    description="Terminate highest CPU consuming process",
                    risk_level=7,
                    estimated_effectiveness=0.9,
                    prerequisites=["process_management"],
                    auto_execute=False
                ),
                PreventionAction(
                    action_id="nice_cpu_hogs",
                    action_type=PreventionAction.APPLY_CONFIGURATION,
                    command="renice +10 $(ps -eo pid,pcpu --sort=-pcpu | head -5 | tail -4 | awk '{print $1}')",
                    description="Lower priority of CPU-intensive processes",
                    risk_level=3,
                    estimated_effectiveness=0.6,
                    prerequisites=["process_management"],
                    auto_execute=True
                )
            ]
        }
        
        return templates
    
    def recommend_actions(self, prediction: FailurePrediction, 
                         current_state: SystemSnapshot) -> List[PreventionAction]:
        """Recommend preventive actions based on failure prediction"""
        failure_type = prediction.failure_type
        
        if failure_type not in self.action_templates:
            return []
        
        # Get all potential actions for this failure type
        potential_actions = self.action_templates[failure_type].copy()
        
        # Score actions based on current context
        scored_actions = []
        for action in potential_actions:
            score = self._score_action(action, prediction, current_state)
            if score > 0.3:  # Threshold for relevance
                scored_actions.append((action, score))
        
        # Sort by score and return top actions
        scored_actions.sort(key=lambda x: x[1], reverse=True)
        recommended_actions = [action for action, score in scored_actions[:5]]
        
        # Update with historical success rates
        for action in recommended_actions:
            success_rate = self._get_success_rate(action.action_id)
            action.estimated_effectiveness *= success_rate
        
        return recommended_actions
    
    def _score_action(self, action: PreventionAction, prediction: FailurePrediction,
                     current_state: SystemSnapshot) -> float:
        """Score an action based on context and prediction"""
        score = action.estimated_effectiveness
        
        # Adjust based on prediction confidence
        confidence_multipliers = {
            PredictionConfidence.LOW: 0.5,
            PredictionConfidence.MEDIUM: 0.7,
            PredictionConfidence.HIGH: 0.9,
            PredictionConfidence.VERY_HIGH: 1.0
        }
        score *= confidence_multipliers.get(prediction.confidence, 0.5)
        
        # Adjust based on time to failure
        if prediction.estimated_time_to_failure < 300:  # Less than 5 minutes
            score *= 1.2  # More urgent
        elif prediction.estimated_time_to_failure > 3600:  # More than 1 hour
            score *= 0.8  # Less urgent
        
        # Adjust based on risk level
        if action.risk_level > 5:
            score *= 0.7  # Penalize high-risk actions
        
        # Adjust based on current system state
        if action.action_type == PreventionAction.RESTART_SERVICE:
            # Check if service is actually running
            running_services = len([s for s in current_state.services 
                                  if s.get('status') == 'running'])
            if running_services < 3:  # Too few services running
                score *= 0.5
        
        return score
    
    def _get_success_rate(self, action_id: str) -> float:
        """Get historical success rate for an action"""
        stats = self.success_rates[action_id]
        if stats['total'] == 0:
            return 1.0  # No history, assume success
        
        return stats['successes'] / stats['total']
    
    def execute_action(self, action: PreventionAction, 
                      dry_run: bool = False) -> Dict[str, Any]:
        """Execute a preventive action"""
        execution_result = {
            'action_id': action.action_id,
            'action_type': action.action_type.value,
            'command': action.command,
            'timestamp': datetime.now(),
            'success': False,
            'output': '',
            'error': '',
            'dry_run': dry_run
        }
        
        try:
            if dry_run:
                logger.info(f"DRY RUN: Would execute {action.command}")
                execution_result['success'] = True
                execution_result['output'] = f"DRY RUN: {action.description}"
            else:
                # Here you would implement actual command execution
                # For safety, we'll just log the command
                logger.info(f"Would execute preventive action: {action.command}")
                execution_result['success'] = True
                execution_result['output'] = f"Simulated execution: {action.description}"
                
                # Update success statistics
                self.success_rates[action.action_id]['total'] += 1
                if execution_result['success']:
                    self.success_rates[action.action_id]['successes'] += 1
            
            # Store in execution history
            self.execution_history.append(execution_result)
            
        except Exception as e:
            execution_result['error'] = str(e)
            logger.error(f"Error executing preventive action {action.action_id}: {e}")
        
        return execution_result


class FailurePredictionDatabase:
    """Database for storing failure predictions and outcomes"""
    
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
                    CREATE TABLE IF NOT EXISTS system_snapshots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        hostname TEXT NOT NULL,
                        metrics TEXT NOT NULL,
                        processes TEXT,
                        services TEXT,
                        network_connections TEXT,
                        disk_usage TEXT,
                        system_load TEXT,
                        recent_events TEXT
                    );
                    
                    CREATE TABLE IF NOT EXISTS failure_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        hostname TEXT NOT NULL,
                        failure_type TEXT NOT NULL,
                        description TEXT,
                        severity INTEGER,
                        resolved_timestamp TEXT,
                        resolution_method TEXT,
                        impact_duration INTEGER
                    );
                    
                    CREATE TABLE IF NOT EXISTS predictions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        prediction_id TEXT UNIQUE NOT NULL,
                        timestamp TEXT NOT NULL,
                        hostname TEXT NOT NULL,
                        failure_type TEXT NOT NULL,
                        confidence TEXT NOT NULL,
                        probability REAL NOT NULL,
                        estimated_time_to_failure INTEGER,
                        contributing_factors TEXT,
                        outcome TEXT,
                        prevented BOOLEAN DEFAULT FALSE
                    );
                    
                    CREATE TABLE IF NOT EXISTS prevention_actions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        action_id TEXT NOT NULL,
                        prediction_id TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        action_type TEXT NOT NULL,
                        command TEXT NOT NULL,
                        success BOOLEAN NOT NULL,
                        output TEXT,
                        error TEXT,
                        FOREIGN KEY (prediction_id) REFERENCES predictions(prediction_id)
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp ON system_snapshots(timestamp);
                    CREATE INDEX IF NOT EXISTS idx_snapshots_hostname ON system_snapshots(hostname);
                    CREATE INDEX IF NOT EXISTS idx_failures_timestamp ON failure_events(timestamp);
                    CREATE INDEX IF NOT EXISTS idx_predictions_timestamp ON predictions(timestamp);
                """)
                conn.commit()
            finally:
                conn.close()
    
    def store_snapshot(self, snapshot: SystemSnapshot):
        """Store system snapshot"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute("""
                    INSERT INTO system_snapshots 
                    (timestamp, hostname, metrics, processes, services, 
                     network_connections, disk_usage, system_load, recent_events)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    snapshot.timestamp.isoformat(),
                    snapshot.hostname,
                    json.dumps(snapshot.metrics),
                    json.dumps(snapshot.processes) if snapshot.processes else None,
                    json.dumps(snapshot.services) if snapshot.services else None,
                    json.dumps(snapshot.network_connections) if snapshot.network_connections else None,
                    json.dumps(snapshot.disk_usage),
                    json.dumps(snapshot.system_load),
                    json.dumps(snapshot.recent_events)
                ))
                conn.commit()
            finally:
                conn.close()
    
    def get_snapshots(self, hostname: Optional[str] = None, 
                     since: Optional[datetime] = None,
                     limit: int = 1000) -> List[SystemSnapshot]:
        """Retrieve system snapshots"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                query = "SELECT * FROM system_snapshots WHERE 1=1"
                params = []
                
                if hostname:
                    query += " AND hostname = ?"
                    params.append(hostname)
                
                if since:
                    query += " AND timestamp >= ?"
                    params.append(since.isoformat())
                
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                
                snapshots = []
                for row in rows:
                    snapshot = SystemSnapshot(
                        timestamp=datetime.fromisoformat(row[1]),
                        hostname=row[2],
                        metrics=json.loads(row[3]),
                        processes=json.loads(row[4]) if row[4] else [],
                        services=json.loads(row[5]) if row[5] else [],
                        network_connections=json.loads(row[6]) if row[6] else [],
                        disk_usage=json.loads(row[7]),
                        system_load=json.loads(row[8]),
                        recent_events=json.loads(row[9])
                    )
                    snapshots.append(snapshot)
                
                return snapshots
            finally:
                conn.close()
    
    def store_prediction(self, prediction: FailurePrediction):
        """Store failure prediction"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO predictions 
                    (prediction_id, timestamp, hostname, failure_type, confidence, 
                     probability, estimated_time_to_failure, contributing_factors)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    prediction.prediction_id,
                    prediction.timestamp.isoformat(),
                    prediction.hostname,
                    prediction.failure_type.value,
                    prediction.confidence.value,
                    prediction.probability,
                    prediction.estimated_time_to_failure,
                    json.dumps(prediction.contributing_factors)
                ))
                conn.commit()
            finally:
                conn.close()


class PredictiveFailurePreventor:
    """
    Main predictive failure prevention system that analyzes system patterns
    and prevents failures before they occur.
    """
    
    def __init__(self, db_path: str = None, model_dir: str = None):
        """Initialize predictive failure prevention system"""
        self.db_path = db_path or "failure_prediction.db"
        self.model_dir = Path(model_dir or "prediction_models")
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        # Components
        self.database = FailurePredictionDatabase(self.db_path)
        self.feature_extractor = FeatureExtractor()
        self.prevention_engine = PreventionActionEngine()
        
        # Models for different failure types
        self.models = {}
        for failure_type in FailureType:
            self.models[failure_type] = FailurePredictionModel(failure_type)
        
        # State
        self.active_predictions = {}
        self.prediction_history = deque(maxlen=1000)
        
        # Threading for background tasks
        self.monitoring_thread = None
        self.stop_event = threading.Event()
        
        # Callbacks
        self.prediction_callbacks = []
        self.prevention_callbacks = []
        
        # Load existing models
        self._load_models()
        
        logger.info("Predictive failure prevention system initialized")
    
    def start_monitoring(self):
        """Start continuous monitoring for failure prediction"""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            logger.warning("Monitoring is already running")
            return
        
        self.stop_event.clear()
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        logger.info("Started predictive failure monitoring")
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.stop_event.set()
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=10)
        
        # Save models
        self._save_models()
        
        logger.info("Stopped predictive failure monitoring")
    
    def add_system_snapshot(self, snapshot: SystemSnapshot):
        """Add system snapshot for analysis"""
        # Store in database
        self.database.store_snapshot(snapshot)
        
        # Make predictions
        predictions = self.predict_failures(snapshot)
        
        # Handle predictions
        for prediction in predictions:
            self._handle_prediction(prediction, snapshot)
    
    def predict_failures(self, snapshot: SystemSnapshot) -> List[FailurePrediction]:
        """Predict potential failures from system snapshot"""
        predictions = []
        
        # Get historical data for trend analysis
        history = self.database.get_snapshots(
            hostname=snapshot.hostname,
            since=datetime.now() - timedelta(hours=2),
            limit=50
        )
        
        # Extract features
        features = self.feature_extractor.extract_features(snapshot, history)
        feature_df = pd.DataFrame([features])
        
        # Make predictions with each model
        for failure_type, model in self.models.items():
            if not model.is_trained:
                continue
            
            try:
                # Get ensemble prediction
                probability = model.get_ensemble_prediction(feature_df)
                
                if probability > 0.1:  # Minimum threshold
                    # Get feature contributions
                    _, feature_contributions = model.predict(feature_df)
                    
                    # Determine confidence level
                    confidence = self._determine_confidence(probability, feature_contributions)
                    
                    # Estimate time to failure
                    time_to_failure = self._estimate_time_to_failure(
                        probability, feature_contributions, failure_type
                    )
                    
                    # Create prediction
                    prediction_id = f"{snapshot.hostname}_{failure_type.value}_{int(snapshot.timestamp.timestamp())}"
                    
                    prediction = FailurePrediction(
                        prediction_id=prediction_id,
                        failure_type=failure_type,
                        confidence=confidence,
                        probability=probability,
                        estimated_time_to_failure=time_to_failure,
                        contributing_factors=feature_contributions,
                        recommended_actions=[],  # Will be filled later
                        timestamp=snapshot.timestamp,
                        hostname=snapshot.hostname,
                        is_critical=probability > 0.8 and time_to_failure < 1800  # 30 minutes
                    )
                    
                    predictions.append(prediction)
            
            except Exception as e:
                logger.error(f"Error predicting {failure_type.value}: {e}")
        
        return predictions
    
    def _handle_prediction(self, prediction: FailurePrediction, snapshot: SystemSnapshot):
        """Handle a failure prediction"""
        # Store prediction
        self.database.store_prediction(prediction)
        self.prediction_history.append(prediction)
        
        # Get recommended actions
        recommended_actions = self.prevention_engine.recommend_actions(prediction, snapshot)
        prediction.recommended_actions = [asdict(action) for action in recommended_actions]
        
        # Store as active prediction
        self.active_predictions[prediction.prediction_id] = prediction
        
        # Notify callbacks
        for callback in self.prediction_callbacks:
            try:
                callback(prediction)
            except Exception as e:
                logger.error(f"Prediction callback failed: {e}")
        
        # Auto-execute safe preventive actions
        for action in recommended_actions:
            if action.auto_execute and action.risk_level <= 3:
                try:
                    result = self.prevention_engine.execute_action(action, dry_run=False)
                    logger.info(f"Auto-executed preventive action: {action.action_id}")
                    
                    # Notify prevention callbacks
                    for callback in self.prevention_callbacks:
                        try:
                            callback(action, result)
                        except Exception as e:
                            logger.error(f"Prevention callback failed: {e}")
                
                except Exception as e:
                    logger.error(f"Error auto-executing action {action.action_id}: {e}")
        
        logger.info(f"Handled prediction: {prediction.failure_type.value} "
                   f"({prediction.confidence.value}, {prediction.probability:.2f})")
    
    def _determine_confidence(self, probability: float, 
                            feature_contributions: Dict[str, float]) -> PredictionConfidence:
        """Determine confidence level based on probability and features"""
        if probability >= 0.9:
            return PredictionConfidence.VERY_HIGH
        elif probability >= 0.7:
            return PredictionConfidence.HIGH
        elif probability >= 0.4:
            return PredictionConfidence.MEDIUM
        else:
            return PredictionConfidence.LOW
    
    def _estimate_time_to_failure(self, probability: float, 
                                 feature_contributions: Dict[str, float],
                                 failure_type: FailureType) -> int:
        """Estimate time to failure in seconds"""
        # Base estimation based on failure type
        base_times = {
            FailureType.DISK_SPACE: 3600,  # 1 hour
            FailureType.MEMORY_EXHAUSTION: 1800,  # 30 minutes
            FailureType.CPU_OVERLOAD: 600,  # 10 minutes
            FailureType.SERVICE_CRASH: 900,  # 15 minutes
            FailureType.NETWORK_CONGESTION: 1200,  # 20 minutes
            FailureType.PROCESS_HANG: 300,  # 5 minutes
        }
        
        base_time = base_times.get(failure_type, 1800)
        
        # Adjust based on probability (higher probability = less time)
        time_factor = 1.0 - (probability * 0.7)
        
        # Adjust based on trend features
        trend_factor = 1.0
        for feature_name, contribution in feature_contributions.items():
            if 'trend' in feature_name and contribution > 0:
                trend_factor *= 0.8  # Negative trends reduce time to failure
        
        estimated_time = int(base_time * time_factor * trend_factor)
        return max(60, estimated_time)  # Minimum 1 minute
    
    def train_models(self, days_back: int = 30):
        """Train failure prediction models with historical data"""
        logger.info("Training failure prediction models...")
        
        # Get training data
        since = datetime.now() - timedelta(days=days_back)
        snapshots = self.database.get_snapshots(since=since, limit=5000)
        
        if len(snapshots) < 50:
            logger.warning("Insufficient training data")
            return
        
        # Prepare training data for each failure type
        for failure_type in FailureType:
            try:
                # Create features and labels
                X_data = []
                y_data = []
                
                for i, snapshot in enumerate(snapshots[:-1]):  # Exclude last snapshot
                    # Get future snapshots to determine if failure occurred
                    future_snapshots = snapshots[i+1:i+10]  # Next 10 snapshots
                    
                    # Extract features
                    features = self.feature_extractor.extract_features(snapshot, snapshots[:i])
                    
                    # Determine if failure occurred (simplified logic)
                    failure_occurred = self._check_failure_occurred(
                        failure_type, snapshot, future_snapshots
                    )
                    
                    X_data.append(features)
                    y_data.append(1 if failure_occurred else 0)
                
                if len(X_data) > 20:  # Minimum samples
                    X_df = pd.DataFrame(X_data)
                    y_series = pd.Series(y_data)
                    
                    # Train model
                    self.models[failure_type].train(X_df, y_series)
            
            except Exception as e:
                logger.error(f"Error training model for {failure_type.value}: {e}")
        
        logger.info("Model training completed")
    
    def _check_failure_occurred(self, failure_type: FailureType, 
                               current_snapshot: SystemSnapshot,
                               future_snapshots: List[SystemSnapshot]) -> bool:
        """Check if a failure of given type occurred in future snapshots"""
        # Simplified failure detection logic
        # In production, this would use actual failure events from logs/monitoring
        
        if failure_type == FailureType.DISK_SPACE:
            # Check if any disk usage exceeded 95%
            for snapshot in future_snapshots:
                for disk, usage in snapshot.disk_usage.items():
                    if usage > 95:
                        return True
        
        elif failure_type == FailureType.MEMORY_EXHAUSTION:
            # Check if memory usage exceeded 98%
            for snapshot in future_snapshots:
                mem_usage = snapshot.metrics.get('memory.usage_percent', 0)
                if mem_usage > 98:
                    return True
        
        elif failure_type == FailureType.CPU_OVERLOAD:
            # Check for sustained high CPU usage
            high_cpu_count = 0
            for snapshot in future_snapshots:
                cpu_usage = snapshot.metrics.get('cpu.usage_percent', 0)
                if cpu_usage > 95:
                    high_cpu_count += 1
            if high_cpu_count >= 3:  # 3 consecutive high CPU readings
                return True
        
        return False
    
    def get_active_predictions(self) -> List[FailurePrediction]:
        """Get currently active predictions"""
        # Clean up old predictions
        current_time = datetime.now()
        expired_predictions = []
        
        for pred_id, prediction in self.active_predictions.items():
            # Remove predictions older than their estimated time to failure
            if (current_time - prediction.timestamp).total_seconds() > prediction.estimated_time_to_failure:
                expired_predictions.append(pred_id)
        
        for pred_id in expired_predictions:
            del self.active_predictions[pred_id]
        
        return list(self.active_predictions.values())
    
    def get_prediction_statistics(self) -> Dict[str, Any]:
        """Get statistics about prediction accuracy and performance"""
        stats = {
            'total_predictions': len(self.prediction_history),
            'active_predictions': len(self.active_predictions),
            'predictions_by_type': defaultdict(int),
            'predictions_by_confidence': defaultdict(int),
            'model_performance': {}
        }
        
        # Count predictions by type and confidence
        for prediction in self.prediction_history:
            stats['predictions_by_type'][prediction.failure_type.value] += 1
            stats['predictions_by_confidence'][prediction.confidence.value] += 1
        
        # Get model performance
        for failure_type, model in self.models.items():
            if model.is_trained:
                stats['model_performance'][failure_type.value] = model.model_performance
        
        return dict(stats)
    
    def _monitoring_loop(self):
        """Background monitoring loop"""
        logger.info("Started predictive monitoring loop")
        
        while not self.stop_event.is_set():
            try:
                # Retrain models periodically (every 24 hours)
                if hasattr(self, '_last_training'):
                    if (datetime.now() - self._last_training).total_seconds() > 86400:
                        self.train_models()
                        self._last_training = datetime.now()
                else:
                    self._last_training = datetime.now()
                
                # Clean up old predictions
                self.get_active_predictions()  # This cleans up old predictions
                
                time.sleep(300)  # Check every 5 minutes
            
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)
        
        logger.info("Stopped predictive monitoring loop")
    
    def _save_models(self):
        """Save trained models to disk"""
        for failure_type, model in self.models.items():
            if model.is_trained:
                model_path = self.model_dir / f"{failure_type.value}_model.pkl"
                model.save_model(model_path)
    
    def _load_models(self):
        """Load trained models from disk"""
        for failure_type, model in self.models.items():
            model_path = self.model_dir / f"{failure_type.value}_model.pkl"
            if model_path.exists():
                model.load_model(model_path)
    
    def add_prediction_callback(self, callback: Callable[[FailurePrediction], None]):
        """Add callback for new predictions"""
        self.prediction_callbacks.append(callback)
    
    def add_prevention_callback(self, callback: Callable[[PreventionAction, Dict], None]):
        """Add callback for prevention actions"""
        self.prevention_callbacks.append(callback)
    
    def cleanup(self):
        """Cleanup resources"""
        self.stop_monitoring()
        logger.info("Predictive failure prevention system cleanup completed")