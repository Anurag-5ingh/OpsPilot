"""
Predictive Failure Prevention Module

ML-powered failure prediction system that analyzes historical data, system patterns,
and current metrics to predict and prevent potential failures before they occur.
Includes early warning systems and preventive action recommendations.
"""

from .failure_predictor import (
    PredictiveFailurePreventor,
    FailurePredictionModel,
    FeatureExtractor,
    PreventionActionEngine,
    FailurePredictionDatabase,
    FailurePrediction,
    SystemSnapshot,
    FailurePattern,
    PreventionAction,
    FailureType,
    PredictionConfidence
)

__all__ = [
    'PredictiveFailurePreventor',
    'FailurePredictionModel',
    'FeatureExtractor',
    'PreventionActionEngine', 
    'FailurePredictionDatabase',
    'FailurePrediction',
    'SystemSnapshot',
    'FailurePattern',
    'PreventionAction',
    'FailureType',
    'PredictionConfidence'
]

__version__ = "1.0.0"