"""
Context-Aware Command Learning

Intelligent learning system that analyzes successful command patterns in specific contexts
to improve future command suggestions and reduce trial-and-error cycles.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict
import logging

from ..command_generation.ml_database_manager import MLDatabaseManager

logger = logging.getLogger(__name__)


@dataclass
class CommandContext:
    """Represents the context in which a command was executed"""
    os_distribution: str
    user_role: str
    system_environment: str  # dev/staging/production
    time_of_day: int
    day_of_week: int
    system_load: float
    available_tools: List[str]
    task_category: str  # deployment, maintenance, troubleshooting, etc.
    success_history: List[bool]  # Recent success pattern


@dataclass
class LearnedPattern:
    """Represents a learned command pattern for specific contexts"""
    pattern_id: str
    context_signature: str
    command_template: str
    success_rate: float
    usage_count: int
    alternative_commands: List[str]
    prerequisites: List[str]
    typical_duration: float
    confidence_score: float
    last_updated: datetime
    user_preferences: Dict[str, float]  # User-specific preferences


class ContextSignatureGenerator:
    """Generates unique signatures for different execution contexts"""
    
    def __init__(self):
        self.signature_weights = {
            'os_distribution': 0.3,
            'user_role': 0.2,
            'system_environment': 0.25,
            'task_category': 0.15,
            'time_context': 0.1
        }
    
    def generate_signature(self, context: CommandContext, user_id: str) -> str:
        """Generate a unique signature for the given context"""
        # Normalize time context (morning/afternoon/evening/night)
        time_context = self._get_time_context(context.time_of_day)
        
        # Create signature components
        components = [
            f"os:{context.os_distribution}",
            f"role:{context.user_role}",
            f"env:{context.system_environment}",
            f"task:{context.task_category}",
            f"time:{time_context}",
            f"user:{user_id}"
        ]
        
        return "|".join(components)
    
    def _get_time_context(self, hour: int) -> str:
        """Convert hour to time context"""
        if 6 <= hour < 12:
            return "morning"
        elif 12 <= hour < 18:
            return "afternoon"
        elif 18 <= hour < 22:
            return "evening"
        else:
            return "night"
    
    def calculate_context_similarity(self, sig1: str, sig2: str) -> float:
        """Calculate similarity between two context signatures"""
        components1 = dict(comp.split(':') for comp in sig1.split('|'))
        components2 = dict(comp.split(':') for comp in sig2.split('|'))
        
        similarity = 0.0
        total_weight = 0.0
        
        for key, weight in self.signature_weights.items():
            if key in components1 and key in components2:
                if components1[key] == components2[key]:
                    similarity += weight
                total_weight += weight
        
        return similarity / total_weight if total_weight > 0 else 0.0


class PatternLearner:
    """Learns command patterns from execution history"""
    
    def __init__(self, db_manager: MLDatabaseManager):
        self.db_manager = db_manager
        self.signature_generator = ContextSignatureGenerator()
        self.learned_patterns = {}
        self.context_clusters = defaultdict(list)
    
    def learn_from_executions(self, days_back: int = 90) -> Dict[str, LearnedPattern]:
        """Learn patterns from recent command executions"""
        # Get execution data
        df = self.db_manager.get_training_dataset(days_back=days_back, min_samples=1)
        
        if df.empty:
            return {}
        
        # Group executions by context and command patterns
        context_groups = self._group_by_context(df)
        
        # Learn patterns for each context group
        for context_sig, executions in context_groups.items():
            if len(executions) >= 3:  # Minimum executions to form a pattern
                pattern = self._extract_pattern(context_sig, executions)
                if pattern:
                    self.learned_patterns[pattern.pattern_id] = pattern
        
        logger.info(f"Learned {len(self.learned_patterns)} command patterns")
        return self.learned_patterns
    
    def _group_by_context(self, df) -> Dict[str, List]:
        """Group executions by similar contexts"""
        context_groups = defaultdict(list)
        
        for _, row in df.iterrows():
            try:
                system_context = json.loads(row['system_context']) if isinstance(row['system_context'], str) else row['system_context']
                
                # Extract context information
                context = CommandContext(
                    os_distribution=system_context.get('os_info', {}).get('distribution', 'unknown'),
                    user_role=system_context.get('user_role', 'user'),
                    system_environment=system_context.get('environment', 'unknown'),
                    time_of_day=datetime.fromisoformat(row['timestamp']).hour,
                    day_of_week=datetime.fromisoformat(row['timestamp']).weekday(),
                    system_load=system_context.get('load_avg', {}).get('1min', 0.0),
                    available_tools=system_context.get('available_tools', []),
                    task_category=self._infer_task_category(row['command']),
                    success_history=[]
                )
                
                # Generate context signature
                user_id = row.get('user_id', 'unknown')
                signature = self.signature_generator.generate_signature(context, user_id)
                
                # Group similar contexts
                merged_signature = self._find_or_create_context_group(signature)
                context_groups[merged_signature].append({
                    'command': row['command'],
                    'success': row['execution_success'],
                    'duration': row.get('execution_time_ms', 0),
                    'timestamp': row['timestamp'],
                    'user_id': user_id,
                    'context': context
                })
                
            except Exception as e:
                logger.warning(f"Failed to process execution record: {e}")
                continue
        
        return context_groups
    
    def _find_or_create_context_group(self, signature: str) -> str:
        """Find existing similar context group or create new one"""
        # Look for similar existing signatures
        for existing_sig in self.context_clusters.keys():
            similarity = self.signature_generator.calculate_context_similarity(signature, existing_sig)
            if similarity > 0.8:  # High similarity threshold
                return existing_sig
        
        # Create new group
        return signature
    
    def _infer_task_category(self, command: str) -> str:
        """Infer task category from command pattern"""
        command_lower = command.lower()
        
        # Deployment-related commands
        if any(keyword in command_lower for keyword in ['deploy', 'docker', 'kubectl', 'helm']):
            return 'deployment'
        
        # Maintenance commands
        elif any(keyword in command_lower for keyword in ['systemctl', 'service', 'crontab', 'logrotate']):
            return 'maintenance'
        
        # Troubleshooting commands
        elif any(keyword in command_lower for keyword in ['ps', 'top', 'netstat', 'lsof', 'tail', 'grep']):
            return 'troubleshooting'
        
        # Database operations
        elif any(keyword in command_lower for keyword in ['mysql', 'psql', 'mongo', 'redis']):
            return 'database'
        
        # File operations
        elif any(keyword in command_lower for keyword in ['cp', 'mv', 'rm', 'mkdir', 'chmod', 'chown']):
            return 'file_management'
        
        # Network operations
        elif any(keyword in command_lower for keyword in ['wget', 'curl', 'ssh', 'scp', 'rsync']):
            return 'network'
        
        return 'general'
    
    def _extract_pattern(self, context_signature: str, executions: List[Dict]) -> Optional[LearnedPattern]:
        """Extract learned pattern from execution group"""
        if not executions:
            return None
        
        # Analyze command patterns
        commands = [exec['command'] for exec in executions]
        successful_commands = [exec['command'] for exec in executions if exec['success']]
        
        if not successful_commands:
            return None
        
        # Find most common successful command template
        command_template = self._find_common_template(successful_commands)
        
        # Calculate metrics
        success_rate = len(successful_commands) / len(executions)
        usage_count = len(executions)
        avg_duration = sum(exec.get('duration', 0) for exec in executions) / len(executions)
        
        # Generate alternatives
        alternatives = list(set(successful_commands))[:5]  # Top 5 alternatives
        
        # Calculate confidence based on success rate and usage
        confidence_score = min((success_rate * 0.7) + (min(usage_count / 10, 1.0) * 0.3), 1.0)
        
        # Extract prerequisites
        prerequisites = self._extract_prerequisites(successful_commands)
        
        # Analyze user preferences
        user_preferences = self._analyze_user_preferences(executions)
        
        return LearnedPattern(
            pattern_id=f"pattern_{abs(hash(context_signature))}",
            context_signature=context_signature,
            command_template=command_template,
            success_rate=success_rate,
            usage_count=usage_count,
            alternative_commands=alternatives,
            prerequisites=prerequisites,
            typical_duration=avg_duration / 1000.0,  # Convert to seconds
            confidence_score=confidence_score,
            last_updated=datetime.now(),
            user_preferences=user_preferences
        )
    
    def _find_common_template(self, commands: List[str]) -> str:
        """Find common template from list of commands"""
        if not commands:
            return ""
        
        # For now, return most frequent command
        # In production, would use more sophisticated template extraction
        from collections import Counter
        counter = Counter(commands)
        return counter.most_common(1)[0][0]
    
    def _extract_prerequisites(self, commands: List[str]) -> List[str]:
        """Extract common prerequisites from commands"""
        prerequisites = set()
        
        for command in commands:
            if command.startswith('sudo'):
                prerequisites.add("Administrative privileges required")
            
            if any(tool in command for tool in ['docker', 'kubectl', 'helm']):
                prerequisites.add("Container management tools required")
            
            if any(tool in command for tool in ['mysql', 'psql', 'mongo']):
                prerequisites.add("Database access credentials required")
            
            if 'ssh' in command or 'scp' in command:
                prerequisites.add("SSH access to remote servers required")
        
        return list(prerequisites)
    
    def _analyze_user_preferences(self, executions: List[Dict]) -> Dict[str, float]:
        """Analyze user preferences from execution patterns"""
        preferences = {}
        
        # Analyze time preferences
        hours = [datetime.fromisoformat(exec['timestamp']).hour for exec in executions]
        if hours:
            avg_hour = sum(hours) / len(hours)
            preferences['preferred_time'] = avg_hour
        
        # Analyze success patterns
        recent_successes = [exec['success'] for exec in executions[-5:]]  # Last 5 executions
        if recent_successes:
            preferences['recent_success_rate'] = sum(recent_successes) / len(recent_successes)
        
        return preferences


class ContextAwareCommandSuggester:
    """Provides context-aware command suggestions based on learned patterns"""
    
    def __init__(self, db_manager: MLDatabaseManager):
        self.db_manager = db_manager
        self.pattern_learner = PatternLearner(db_manager)
        self.signature_generator = ContextSignatureGenerator()
        self.learned_patterns = {}
    
    def initialize_learning(self):
        """Initialize the learning system with historical data"""
        self.learned_patterns = self.pattern_learner.learn_from_executions()
        logger.info(f"Initialized with {len(self.learned_patterns)} learned patterns")
    
    def suggest_commands(self, user_request: str, current_context: Dict, 
                        user_id: str = "unknown") -> List[Dict]:
        """
        Suggest commands based on learned patterns and current context
        
        Args:
            user_request: Natural language request
            current_context: Current system and user context
            user_id: User identifier
            
        Returns:
            List of suggested commands with confidence scores
        """
        if not self.learned_patterns:
            self.initialize_learning()
        
        # Create context from current situation
        context = self._build_context_from_dict(current_context)
        context_signature = self.signature_generator.generate_signature(context, user_id)
        
        # Find similar patterns
        similar_patterns = self._find_similar_patterns(context_signature, user_request)
        
        # Generate suggestions
        suggestions = []
        for pattern, similarity in similar_patterns:
            suggestion = {
                'command': pattern.command_template,
                'confidence_score': pattern.confidence_score * similarity,
                'success_rate': pattern.success_rate,
                'typical_duration': pattern.typical_duration,
                'prerequisites': pattern.prerequisites,
                'alternatives': pattern.alternative_commands[:3],
                'usage_count': pattern.usage_count,
                'reasoning': f"Based on {pattern.usage_count} similar executions with {pattern.success_rate:.1%} success rate",
                'context_match': similarity
            }
            suggestions.append(suggestion)
        
        # Sort by confidence score
        suggestions.sort(key=lambda x: x['confidence_score'], reverse=True)
        
        return suggestions[:5]  # Top 5 suggestions
    
    def _build_context_from_dict(self, context_dict: Dict) -> CommandContext:
        """Build CommandContext from dictionary"""
        os_info = context_dict.get('os_info', {})
        
        return CommandContext(
            os_distribution=os_info.get('distribution', 'unknown'),
            user_role=context_dict.get('user_role', 'user'),
            system_environment=context_dict.get('environment', 'unknown'),
            time_of_day=datetime.now().hour,
            day_of_week=datetime.now().weekday(),
            system_load=context_dict.get('load_avg', {}).get('1min', 0.0),
            available_tools=context_dict.get('available_tools', []),
            task_category='general',  # Will be inferred from request
            success_history=[]
        )
    
    def _find_similar_patterns(self, context_signature: str, user_request: str) -> List[Tuple[LearnedPattern, float]]:
        """Find patterns similar to current context"""
        similar_patterns = []
        
        for pattern in self.learned_patterns.values():
            # Calculate context similarity
            context_similarity = self.signature_generator.calculate_context_similarity(
                context_signature, pattern.context_signature
            )
            
            # Calculate request similarity (simple keyword matching for now)
            request_similarity = self._calculate_request_similarity(user_request, pattern.command_template)
            
            # Combined similarity score
            combined_similarity = (context_similarity * 0.6) + (request_similarity * 0.4)
            
            if combined_similarity > 0.3:  # Threshold for relevance
                similar_patterns.append((pattern, combined_similarity))
        
        # Sort by similarity
        similar_patterns.sort(key=lambda x: x[1], reverse=True)
        
        return similar_patterns[:10]  # Top 10 similar patterns
    
    def _calculate_request_similarity(self, request: str, command: str) -> float:
        """Calculate similarity between user request and command"""
        request_words = set(request.lower().split())
        command_words = set(command.lower().split())
        
        # Simple Jaccard similarity
        intersection = request_words.intersection(command_words)
        union = request_words.union(command_words)
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)
    
    def record_suggestion_feedback(self, suggestion_id: str, user_id: str, 
                                 accepted: bool, execution_success: Optional[bool] = None):
        """Record feedback on suggestions for continuous learning"""
        # This would update the learned patterns based on user feedback
        # Implementation depends on how we track suggestion IDs
        pass
    
    def get_learning_stats(self) -> Dict:
        """Get statistics about learned patterns"""
        if not self.learned_patterns:
            return {'total_patterns': 0}
        
        patterns = list(self.learned_patterns.values())
        
        # Calculate statistics
        total_patterns = len(patterns)
        avg_success_rate = sum(p.success_rate for p in patterns) / total_patterns
        avg_confidence = sum(p.confidence_score for p in patterns) / total_patterns
        total_usage = sum(p.usage_count for p in patterns)
        
        # Group by task category
        task_categories = defaultdict(int)
        for pattern in patterns:
            # Extract task category from context signature
            context_parts = dict(part.split(':') for part in pattern.context_signature.split('|'))
            task_category = context_parts.get('task', 'unknown')
            task_categories[task_category] += 1
        
        return {
            'total_patterns': total_patterns,
            'average_success_rate': avg_success_rate,
            'average_confidence': avg_confidence,
            'total_usage_count': total_usage,
            'task_categories': dict(task_categories),
            'last_learning_update': max(p.last_updated for p in patterns).isoformat() if patterns else None
        }
    
    def refresh_learning(self):
        """Refresh learned patterns with latest data"""
        logger.info("Refreshing context-aware learning patterns...")
        self.learned_patterns = self.pattern_learner.learn_from_executions()
        logger.info(f"Learning refresh complete: {len(self.learned_patterns)} patterns")


class ContextAwareLearningSystem:
    """
    Main system that coordinates context-aware command learning.
    Integrates with command generation pipeline to provide intelligent suggestions.
    """
    
    def __init__(self, db_manager: Optional[MLDatabaseManager] = None):
        """Initialize the context-aware learning system"""
        self.db_manager = db_manager or MLDatabaseManager()
        self.suggester = ContextAwareCommandSuggester(self.db_manager)
        self.learning_enabled = True
        
        # Initialize learning in background
        try:
            self.suggester.initialize_learning()
        except Exception as e:
            logger.warning(f"Initial learning failed, will retry later: {e}")
    
    def enhance_command_generation(self, user_request: str, base_ai_response: Dict,
                                 system_context: Dict, user_id: str = "unknown") -> Dict:
        """
        Enhance AI command generation with context-aware suggestions
        
        Args:
            user_request: Original user request
            base_ai_response: Response from base AI system
            system_context: Current system context
            user_id: User identifier
            
        Returns:
            Enhanced response with context-aware suggestions
        """
        if not self.learning_enabled:
            return base_ai_response
        
        try:
            # Get context-aware suggestions
            suggestions = self.suggester.suggest_commands(user_request, system_context, user_id)
            
            if suggestions:
                # Add suggestions to AI response
                base_ai_response['context_aware_suggestions'] = suggestions
                base_ai_response['learning_enhanced'] = True
                
                # If we have a high-confidence suggestion that's different from AI's choice
                top_suggestion = suggestions[0]
                if (top_suggestion['confidence_score'] > 0.8 and 
                    top_suggestion['command'] != base_ai_response.get('final_command')):
                    
                    base_ai_response['alternative_recommendation'] = {
                        'command': top_suggestion['command'],
                        'reasoning': f"Based on learned patterns: {top_suggestion['reasoning']}",
                        'confidence': top_suggestion['confidence_score']
                    }
            else:
                base_ai_response['learning_enhanced'] = False
                base_ai_response['context_aware_suggestions'] = []
            
        except Exception as e:
            logger.error(f"Context-aware enhancement failed: {e}")
            base_ai_response['learning_enhanced'] = False
            base_ai_response['context_aware_suggestions'] = []
        
        return base_ai_response
    
    def get_system_status(self) -> Dict:
        """Get status of the learning system"""
        try:
            stats = self.suggester.get_learning_stats()
            stats['learning_enabled'] = self.learning_enabled
            stats['system_status'] = 'active' if self.learning_enabled else 'disabled'
            return stats
        except Exception as e:
            return {
                'learning_enabled': self.learning_enabled,
                'system_status': 'error',
                'error': str(e)
            }
    
    def trigger_learning_refresh(self):
        """Manually trigger learning refresh"""
        if self.learning_enabled:
            self.suggester.refresh_learning()
    
    def enable_learning(self):
        """Enable context-aware learning"""
        self.learning_enabled = True
        logger.info("Context-aware learning enabled")
    
    def disable_learning(self):
        """Disable context-aware learning"""
        self.learning_enabled = False
        logger.info("Context-aware learning disabled")