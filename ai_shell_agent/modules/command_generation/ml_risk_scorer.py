"""
Machine Learning Risk Scorer

Advanced risk assessment system that learns from user behavior patterns,
command outcomes, and system contexts to improve risk scoring accuracy over time.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score
import joblib
import os

from .risk_analyzer import RiskLevel, RiskCategory


@dataclass
class CommandExecution:
    """Record of a command execution for ML training"""
    command: str
    initial_risk_level: str
    user_confirmed: bool
    execution_success: bool
    actual_impact: str  # 'none', 'minor', 'moderate', 'severe'
    system_context: Dict
    timestamp: datetime
    user_feedback: Optional[str] = None


class MLRiskDatabase:
    """Database for storing command execution history and outcomes"""
    
    def __init__(self, db_path: str = "ml_risk_data.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables for ML training data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS command_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command TEXT NOT NULL,
                initial_risk_level TEXT NOT NULL,
                user_confirmed BOOLEAN NOT NULL,
                execution_success BOOLEAN NOT NULL,
                actual_impact TEXT NOT NULL,
                system_context TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                user_feedback TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS model_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_version TEXT NOT NULL,
                accuracy REAL NOT NULL,
                precision_score REAL NOT NULL,
                recall_score REAL NOT NULL,
                training_date TEXT NOT NULL,
                sample_size INTEGER NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_execution(self, execution: CommandExecution):
        """Add command execution record to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO command_executions 
            (command, initial_risk_level, user_confirmed, execution_success, 
             actual_impact, system_context, timestamp, user_feedback)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            execution.command,
            execution.initial_risk_level,
            execution.user_confirmed,
            execution.execution_success,
            execution.actual_impact,
            json.dumps(execution.system_context),
            execution.timestamp.isoformat(),
            execution.user_feedback
        ))
        
        conn.commit()
        conn.close()
    
    def get_training_data(self, days_back: int = 90) -> List[CommandExecution]:
        """Retrieve training data from specified time period"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
        
        cursor.execute('''
            SELECT command, initial_risk_level, user_confirmed, execution_success,
                   actual_impact, system_context, timestamp, user_feedback
            FROM command_executions 
            WHERE timestamp > ?
            ORDER BY timestamp DESC
        ''', (cutoff_date,))
        
        executions = []
        for row in cursor.fetchall():
            executions.append(CommandExecution(
                command=row[0],
                initial_risk_level=row[1],
                user_confirmed=bool(row[2]),
                execution_success=bool(row[3]),
                actual_impact=row[4],
                system_context=json.loads(row[5]),
                timestamp=datetime.fromisoformat(row[6]),
                user_feedback=row[7]
            ))
        
        conn.close()
        return executions


class MLRiskScorer:
    """
    Machine Learning Risk Scorer that improves accuracy over time.
    
    Uses ensemble learning with command text analysis, system context,
    and historical outcomes to provide improved risk assessments.
    """
    
    def __init__(self, model_path: str = "models/risk_scorer_model.joblib"):
        self.model_path = model_path
        self.model = None
        self.vectorizer = None
        self.feature_columns = []
        self.db = MLRiskDatabase()
        
        # Load existing model if available
        if os.path.exists(self.model_path):
            self.load_model()
    
    def extract_features(self, command: str, system_context: Dict) -> Dict:
        """Extract features from command and system context for ML model"""
        features = {
            # Command text features
            'command_length': len(command),
            'word_count': len(command.split()),
            'has_sudo': 1 if 'sudo' in command.lower() else 0,
            'has_rm': 1 if 'rm ' in command.lower() else 0,
            'has_chmod': 1 if 'chmod' in command.lower() else 0,
            'has_pipes': command.count('|'),
            'has_redirects': command.count('>') + command.count('<'),
            'has_wildcards': command.count('*') + command.count('?'),
            
            # System context features
            'is_root_user': 1 if system_context.get('user') == 'root' else 0,
            'system_load': system_context.get('load_avg', {}).get('1min', 0),
            'disk_usage_percent': system_context.get('disk_usage', {}).get('/', {}).get('percent', 0),
            'memory_usage_percent': system_context.get('memory_usage', {}).get('percent', 0),
            
            # Time-based features
            'hour_of_day': datetime.now().hour,
            'is_weekend': 1 if datetime.now().weekday() >= 5 else 0,
            
            # Distribution features
            'is_debian_based': 1 if 'ubuntu' in system_context.get('os_info', {}).get('distribution', '').lower() else 0,
            'is_redhat_based': 1 if any(x in system_context.get('os_info', {}).get('distribution', '').lower() 
                                      for x in ['centos', 'rhel', 'fedora']) else 0,
        }
        
        return features
    
    def prepare_training_data(self, executions: List[CommandExecution]) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare training data from command execution history"""
        features_list = []
        labels = []
        
        # Extract features and labels
        for execution in executions:
            features = self.extract_features(execution.command, execution.system_context)
            features_list.append(features)
            
            # Create label based on actual impact (target variable)
            if execution.actual_impact == 'severe':
                label = 3  # Critical
            elif execution.actual_impact == 'moderate':
                label = 2  # High
            elif execution.actual_impact == 'minor':
                label = 1  # Medium
            else:
                label = 0  # Low
            
            labels.append(label)
        
        # Convert to matrices
        if not features_list:
            return np.array([]), np.array([])
        
        # Get feature names
        self.feature_columns = list(features_list[0].keys())
        
        # Convert features to matrix
        X = np.array([[f[col] for col in self.feature_columns] for f in features_list])
        y = np.array(labels)
        
        return X, y
    
    def train_model(self, min_samples: int = 50) -> Dict:
        """Train ML model on historical command execution data"""
        # Get training data
        executions = self.db.get_training_data(days_back=180)  # 6 months of data
        
        if len(executions) < min_samples:
            return {
                'success': False,
                'error': f'Insufficient training data: {len(executions)} samples (minimum: {min_samples})'
            }
        
        # Prepare training data
        X, y = self.prepare_training_data(executions)
        
        if len(X) == 0:
            return {'success': False, 'error': 'No valid training data found'}
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Train model
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42
        )
        
        self.model.fit(X_train, y_train)
        
        # Evaluate model
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, average='weighted', zero_division=0)
        recall = recall_score(y_test, y_pred, average='weighted', zero_division=0)
        
        # Save model
        self.save_model()
        
        # Store metrics
        self._save_model_metrics(accuracy, precision, recall, len(executions))
        
        return {
            'success': True,
            'metrics': {
                'accuracy': accuracy,
                'precision': precision,
                'recall': recall,
                'training_samples': len(executions),
                'test_samples': len(X_test)
            }
        }
    
    def predict_risk_level(self, command: str, system_context: Dict, 
                          fallback_analyzer) -> Dict:
        """
        Predict risk level using ML model with fallback to rule-based analysis
        
        Args:
            command: Shell command to analyze
            system_context: System context information
            fallback_analyzer: Traditional risk analyzer for fallback
            
        Returns:
            Enhanced risk analysis with ML predictions
        """
        # Get baseline analysis from traditional analyzer
        baseline_analysis = fallback_analyzer.analyze_command(command, system_context)
        
        # If no ML model available, return baseline
        if not self.model or not self.feature_columns:
            baseline_analysis['ml_enhanced'] = False
            baseline_analysis['confidence_source'] = 'rule_based'
            return baseline_analysis
        
        try:
            # Extract features for ML prediction
            features = self.extract_features(command, system_context)
            feature_vector = np.array([[features[col] for col in self.feature_columns]])
            
            # Get ML prediction
            ml_risk_numeric = self.model.predict(feature_vector)[0]
            ml_risk_proba = self.model.predict_proba(feature_vector)[0]
            
            # Convert numeric risk to enum
            risk_mapping = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
            ml_risk_level = risk_mapping[ml_risk_numeric]
            
            # Calculate confidence based on prediction probability
            ml_confidence = float(np.max(ml_risk_proba))
            
            # Combine ML and rule-based predictions
            enhanced_analysis = baseline_analysis.copy()
            enhanced_analysis.update({
                'ml_enhanced': True,
                'ml_risk_level': ml_risk_level,
                'ml_confidence': ml_confidence,
                'rule_based_risk_level': baseline_analysis['risk_level'],
                'confidence_source': 'ml_enhanced'
            })
            
            # Use ML prediction if confidence is high enough
            if ml_confidence > 0.7:
                enhanced_analysis['risk_level'] = ml_risk_level
                enhanced_analysis['requires_confirmation'] = ml_risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
            
            # Add feature importance insights
            feature_importance = dict(zip(self.feature_columns, self.model.feature_importances_))
            top_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:5]
            enhanced_analysis['top_risk_factors'] = [f[0] for f in top_features]
            
            return enhanced_analysis
            
        except Exception as e:
            # Fallback to baseline analysis on ML error
            baseline_analysis['ml_enhanced'] = False
            baseline_analysis['ml_error'] = str(e)
            baseline_analysis['confidence_source'] = 'rule_based_fallback'
            return baseline_analysis
    
    def record_execution_outcome(self, command: str, initial_analysis: Dict, 
                               user_confirmed: bool, execution_success: bool, 
                               actual_impact: str, system_context: Dict,
                               user_feedback: Optional[str] = None):
        """Record command execution outcome for continuous learning"""
        execution = CommandExecution(
            command=command,
            initial_risk_level=initial_analysis['risk_level'].value,
            user_confirmed=user_confirmed,
            execution_success=execution_success,
            actual_impact=actual_impact,
            system_context=system_context,
            timestamp=datetime.now(),
            user_feedback=user_feedback
        )
        
        self.db.add_execution(execution)
    
    def save_model(self):
        """Save trained ML model to disk"""
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        
        model_data = {
            'model': self.model,
            'feature_columns': self.feature_columns,
            'version': '1.0',
            'trained_date': datetime.now().isoformat()
        }
        
        joblib.dump(model_data, self.model_path)
    
    def load_model(self):
        """Load trained ML model from disk"""
        if os.path.exists(self.model_path):
            model_data = joblib.load(self.model_path)
            self.model = model_data['model']
            self.feature_columns = model_data['feature_columns']
    
    def _save_model_metrics(self, accuracy: float, precision: float, 
                          recall: float, sample_size: int):
        """Save model performance metrics to database"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO model_metrics 
            (model_version, accuracy, precision_score, recall_score, training_date, sample_size)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('1.0', accuracy, precision, recall, datetime.now().isoformat(), sample_size))
        
        conn.commit()
        conn.close()
    
    def get_model_performance(self) -> Optional[Dict]:
        """Get latest model performance metrics"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT accuracy, precision_score, recall_score, training_date, sample_size
            FROM model_metrics 
            ORDER BY training_date DESC 
            LIMIT 1
        ''')
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'accuracy': row[0],
                'precision': row[1],
                'recall': row[2],
                'training_date': row[3],
                'sample_size': row[4]
            }
        
        return None
    
    def should_retrain(self) -> bool:
        """Determine if model should be retrained based on new data"""
        # Get new data since last training
        metrics = self.get_model_performance()
        if not metrics:
            return True
        
        last_training = datetime.fromisoformat(metrics['training_date'])
        days_since_training = (datetime.now() - last_training).days
        
        # Retrain if it's been more than 30 days or accuracy is low
        if days_since_training > 30 or metrics['accuracy'] < 0.7:
            return True
        
        # Check if we have enough new data
        recent_executions = self.db.get_training_data(days_back=days_since_training)
        if len(recent_executions) > 50:  # Significant new data available
            return True
        
        return False