"""
API endpoints for Multi-server Command Coordination

REST API endpoints for creating, managing, and executing multi-server
orchestration plans with ML-enhanced risk assessment.
"""

from flask import Blueprint, request, jsonify, current_app
from flask_cors import cross_origin
import json
from datetime import datetime
from typing import Dict, List, Optional

from ...modules.orchestration.multi_server_coordinator import (
    MultiServerCoordinator, ExecutionStrategy, DependencyType
)
from ...modules.command_generation.ml_risk_scorer import MLRiskScorer
from ...modules.security.compliance_checker import SecurityComplianceChecker
from ..middleware.auth import require_auth
from ..middleware.rate_limiter import rate_limit
from ...utils.logging_utils import get_logger

logger = get_logger(__name__)

# Create blueprint
orchestration_bp = Blueprint('orchestration', __name__, url_prefix='/api/v1/orchestration')

# Global coordinator instance (will be initialized in app factory)
coordinator = None


def init_orchestration_api(app):
    """Initialize orchestration API with coordinator"""
    global coordinator
    
    # Initialize ML components
    ml_scorer = MLRiskScorer()
    compliance_checker = SecurityComplianceChecker()
    
    # Initialize coordinator
    coordinator = MultiServerCoordinator(ml_scorer, compliance_checker)
    
    logger.info("Multi-server orchestration API initialized")


@orchestration_bp.route('/plans', methods=['POST'])
@cross_origin()
@require_auth
@rate_limit("10 per minute")
def create_plan():
    """
    Create new orchestration plan
    
    Expected JSON payload:
    {
        "name": "deployment-plan-1",
        "description": "Deploy application to production servers",
        "servers": [
            {
                "hostname": "server1.example.com",
                "ssh_config": {"username": "admin", "port": 22},
                "tags": ["web", "production"],
                "priority": 1,
                "max_concurrent": 2,
                "timeout": 300,
                "retry_count": 3
            }
        ],
        "commands": ["sudo systemctl stop myapp", "sudo systemctl start myapp"],
        "execution_config": {
            "strategy": "rolling",
            "description": "Rolling deployment with health checks",
            "dependencies": [
                {
                    "type": "prerequisite",
                    "source": "server1",
                    "target": "server2",
                    "condition": "health_check_passed"
                }
            ],
            "rollback": {
                "auto_rollback": true,
                "continue_on_failure": false,
                "failure_threshold": 0.3,
                "rolling_batch_size": 2
            }
        },
        "system_context": {
            "environment": "production",
            "deployment_window": "maintenance"
        }
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'servers', 'commands', 'execution_config']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate servers configuration
        if not isinstance(data['servers'], list) or not data['servers']:
            return jsonify({'error': 'servers must be a non-empty list'}), 400
        
        for server in data['servers']:
            if 'hostname' not in server:
                return jsonify({'error': 'Each server must have a hostname'}), 400
        
        # Validate commands
        if not isinstance(data['commands'], list) or not data['commands']:
            return jsonify({'error': 'commands must be a non-empty list'}), 400
        
        # Create orchestration plan
        plan = coordinator.create_orchestration_plan(
            name=data['name'],
            servers=data['servers'],
            commands=data['commands'],
            execution_config=data['execution_config'],
            system_context=data.get('system_context', {})
        )
        
        # Get risk assessment if system context provided
        risk_assessment = None
        if data.get('system_context'):
            risk_assessment = coordinator.get_plan_risk_assessment(
                plan.plan_id, data['system_context']
            )
        
        response = {
            'plan_id': plan.plan_id,
            'name': plan.name,
            'description': plan.description,
            'server_count': len(plan.servers),
            'command_count': len(plan.commands),
            'execution_strategy': plan.execution_strategy.value,
            'execution_phases': plan.execution_phases,
            'estimated_duration': plan.estimated_duration,
            'risk_score': plan.risk_score,
            'created_at': plan.created_at.isoformat(),
            'has_dependencies': len(plan.dependencies) > 0,
            'dependency_count': len(plan.dependencies)
        }
        
        if risk_assessment:
            response['risk_assessment'] = risk_assessment
        
        logger.info(f"Created orchestration plan: {plan.plan_id}")
        return jsonify(response), 201
    
    except ValueError as e:
        logger.error(f"Plan creation failed: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error creating plan: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@orchestration_bp.route('/plans', methods=['GET'])
@cross_origin()
@require_auth
def list_plans():
    """List all orchestration plans with optional filtering"""
    try:
        # Get query parameters
        limit = int(request.args.get('limit', 50))
        limit = min(limit, 200)  # Cap at 200
        
        # Get plan summaries
        plan_summaries = []
        for plan_id in list(coordinator.orchestration_plans.keys())[:limit]:
            summary = coordinator.get_plan_summary(plan_id)
            if summary:
                plan_summaries.append(summary)
        
        return jsonify({
            'plans': plan_summaries,
            'total': len(coordinator.orchestration_plans),
            'returned': len(plan_summaries)
        }), 200
    
    except Exception as e:
        logger.error(f"Error listing plans: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@orchestration_bp.route('/plans/<plan_id>', methods=['GET'])
@cross_origin()
@require_auth
def get_plan(plan_id: str):
    """Get detailed information about specific plan"""
    try:
        if plan_id not in coordinator.orchestration_plans:
            return jsonify({'error': 'Plan not found'}), 404
        
        plan = coordinator.orchestration_plans[plan_id]
        
        # Convert to dict for JSON serialization
        plan_dict = {
            'plan_id': plan.plan_id,
            'name': plan.name,
            'description': plan.description,
            'execution_strategy': plan.execution_strategy.value,
            'servers': [
                {
                    'hostname': server.hostname,
                    'tags': server.tags or [],
                    'priority': server.priority,
                    'max_concurrent_commands': server.max_concurrent_commands,
                    'timeout_seconds': server.timeout_seconds,
                    'retry_count': server.retry_count
                }
                for server in plan.servers
            ],
            'commands': plan.commands,
            'dependencies': [
                {
                    'type': dep.dependency_type.value,
                    'source_server': dep.source_server,
                    'target_server': dep.target_server,
                    'condition': dep.condition,
                    'wait_for_completion': dep.wait_for_completion
                }
                for dep in plan.dependencies
            ],
            'execution_phases': plan.execution_phases,
            'rollback_strategy': plan.rollback_strategy,
            'estimated_duration': plan.estimated_duration,
            'risk_score': plan.risk_score,
            'created_at': plan.created_at.isoformat()
        }
        
        return jsonify(plan_dict), 200
    
    except Exception as e:
        logger.error(f"Error getting plan {plan_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@orchestration_bp.route('/plans/<plan_id>/risk-assessment', methods=['POST'])
@cross_origin()
@require_auth
def get_risk_assessment(plan_id: str):
    """
    Get comprehensive risk assessment for plan
    
    Expected JSON payload:
    {
        "system_context": {
            "environment": "production",
            "deployment_window": "maintenance",
            "system_load": "normal",
            "recent_changes": false
        }
    }
    """
    try:
        if plan_id not in coordinator.orchestration_plans:
            return jsonify({'error': 'Plan not found'}), 404
        
        data = request.get_json()
        system_context = data.get('system_context', {})
        
        # Get risk assessment
        assessment = coordinator.get_plan_risk_assessment(plan_id, system_context)
        
        logger.info(f"Risk assessment requested for plan: {plan_id}")
        return jsonify(assessment), 200
    
    except Exception as e:
        logger.error(f"Error getting risk assessment for {plan_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@orchestration_bp.route('/plans/<plan_id>/simulate', methods=['POST'])
@cross_origin()
@require_auth
def simulate_execution(plan_id: str):
    """Simulate plan execution without actually running commands"""
    try:
        if plan_id not in coordinator.orchestration_plans:
            return jsonify({'error': 'Plan not found'}), 404
        
        # Run simulation
        simulation = coordinator.simulate_plan_execution(plan_id)
        
        logger.info(f"Simulation requested for plan: {plan_id}")
        return jsonify(simulation), 200
    
    except Exception as e:
        logger.error(f"Error simulating plan {plan_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@orchestration_bp.route('/plans/<plan_id>/execute', methods=['POST'])
@cross_origin()
@require_auth
@rate_limit("5 per minute")  # Lower rate limit for execution
def execute_plan(plan_id: str):
    """
    Execute orchestration plan
    
    Expected JSON payload:
    {
        "confirm": true,
        "notes": "Production deployment - ticket #12345"
    }
    """
    try:
        if plan_id not in coordinator.orchestration_plans:
            return jsonify({'error': 'Plan not found'}), 404
        
        data = request.get_json() or {}
        
        # Require explicit confirmation
        if not data.get('confirm'):
            return jsonify({'error': 'Execution requires explicit confirmation'}), 400
        
        # Store execution request info
        execution_notes = data.get('notes', '')
        
        # Start execution (this runs in background)
        def progress_callback(progress_data):
            # In a real implementation, you might want to emit WebSocket events
            # or store progress in a database/cache for polling
            logger.info(f"Plan {plan_id} progress: {progress_data}")
        
        # Execute plan
        results = coordinator.execute_plan(plan_id, progress_callback)
        
        # Return execution results
        response = {
            'execution_id': results['plan_id'],
            'status': results['overall_status'].value,
            'start_time': results['start_time'].isoformat(),
            'end_time': results['end_time'].isoformat() if results['end_time'] else None,
            'total_duration': results.get('total_duration', 0),
            'execution_summary': results.get('execution_summary', {}),
            'phase_count': len(results.get('phase_results', [])),
            'failed_servers': len(results.get('failed_servers', [])),
            'rollback_performed': results.get('rollback_performed', False),
            'notes': execution_notes
        }
        
        # Include detailed results if requested
        if data.get('include_details', False):
            # Convert server results to JSON-serializable format
            server_results = {}
            for server, executions in results.get('server_results', {}).items():
                server_results[server] = [
                    {
                        'execution_id': exec.execution_id,
                        'command': exec.command,
                        'status': exec.status.value,
                        'start_time': exec.start_time.isoformat() if exec.start_time else None,
                        'end_time': exec.end_time.isoformat() if exec.end_time else None,
                        'exit_code': exec.exit_code,
                        'output': exec.output[:1000] if exec.output else '',  # Truncate output
                        'error': exec.error[:1000] if exec.error else '',
                        'retry_count': exec.retry_count
                    }
                    for exec in executions
                ]
            
            response['server_results'] = server_results
            response['phase_results'] = results.get('phase_results', [])
        
        logger.info(f"Plan execution completed: {plan_id}, status: {results['overall_status'].value}")
        return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"Error executing plan {plan_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@orchestration_bp.route('/execution-history', methods=['GET'])
@cross_origin()
@require_auth
def get_execution_history():
    """Get recent execution history"""
    try:
        limit = int(request.args.get('limit', 20))
        limit = min(limit, 100)  # Cap at 100
        
        history = coordinator.get_execution_history(limit)
        
        # Convert to JSON-serializable format
        serialized_history = []
        for entry in history:
            serialized_entry = {
                'plan_id': entry['plan_id'],
                'execution_time': entry['execution_time'].isoformat(),
                'status': entry['results']['overall_status'].value,
                'duration': entry['results'].get('total_duration', 0),
                'summary': entry['results'].get('execution_summary', {})
            }
            serialized_history.append(serialized_entry)
        
        return jsonify({
            'history': serialized_history,
            'returned': len(serialized_history)
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting execution history: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@orchestration_bp.route('/execution-progress/<plan_id>', methods=['GET'])
@cross_origin()
@require_auth
def get_execution_progress(plan_id: str):
    """Get real-time execution progress (polling endpoint)"""
    try:
        # In a real implementation, you might store progress in Redis or similar
        # For now, we'll return the latest execution results if available
        
        history = coordinator.get_execution_history()
        current_execution = None
        
        for entry in history:
            if entry['plan_id'] == plan_id:
                current_execution = entry
                break
        
        if not current_execution:
            return jsonify({'error': 'No execution found for plan'}), 404
        
        results = current_execution['results']
        
        # Return progress information
        progress = {
            'plan_id': plan_id,
            'status': results['overall_status'].value,
            'start_time': results['start_time'].isoformat(),
            'end_time': results['end_time'].isoformat() if results['end_time'] else None,
            'elapsed_time': results.get('total_duration', 0),
            'current_phase': len(results.get('phase_results', [])),
            'total_phases': len(coordinator.orchestration_plans[plan_id].execution_phases) 
                          if plan_id in coordinator.orchestration_plans else 0,
            'completed_servers': len(results.get('server_results', {})),
            'failed_servers': len(results.get('failed_servers', [])),
            'is_complete': results['overall_status'].value in ['completed', 'failed']
        }
        
        return jsonify(progress), 200
    
    except Exception as e:
        logger.error(f"Error getting execution progress for {plan_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@orchestration_bp.route('/plans/<plan_id>', methods=['DELETE'])
@cross_origin()
@require_auth
def delete_plan(plan_id: str):
    """Delete orchestration plan"""
    try:
        if plan_id not in coordinator.orchestration_plans:
            return jsonify({'error': 'Plan not found'}), 404
        
        # Remove plan
        del coordinator.orchestration_plans[plan_id]
        
        logger.info(f"Deleted orchestration plan: {plan_id}")
        return jsonify({'message': 'Plan deleted successfully'}), 200
    
    except Exception as e:
        logger.error(f"Error deleting plan {plan_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@orchestration_bp.route('/strategies', methods=['GET'])
@cross_origin()
@require_auth
def get_execution_strategies():
    """Get available execution strategies and their descriptions"""
    strategies = {
        ExecutionStrategy.SEQUENTIAL.value: {
            'name': 'Sequential',
            'description': 'Execute commands on one server at a time',
            'use_cases': ['Safe deployments', 'Database migrations', 'Configuration changes'],
            'pros': ['Lower risk', 'Easier troubleshooting', 'Resource efficient'],
            'cons': ['Slower execution', 'Longer downtime']
        },
        ExecutionStrategy.PARALLEL.value: {
            'name': 'Parallel',
            'description': 'Execute commands on all servers simultaneously',
            'use_cases': ['Fast deployments', 'Independent updates', 'Scaling operations'],
            'pros': ['Fastest execution', 'Minimal downtime'],
            'cons': ['Higher risk', 'Resource intensive', 'Complex troubleshooting']
        },
        ExecutionStrategy.ROLLING.value: {
            'name': 'Rolling',
            'description': 'Execute commands in batches with health checks',
            'use_cases': ['Zero-downtime deployments', 'Load-balanced services'],
            'pros': ['Balanced risk/speed', 'Zero downtime', 'Can stop on failure'],
            'cons': ['More complex', 'Requires health checks']
        },
        ExecutionStrategy.CANARY.value: {
            'name': 'Canary',
            'description': 'Test on small subset before full deployment',
            'use_cases': ['High-risk changes', 'New features', 'Production testing'],
            'pros': ['Very safe', 'Early failure detection', 'User impact minimized'],
            'cons': ['Slowest execution', 'Complex monitoring required']
        },
        ExecutionStrategy.BLUE_GREEN.value: {
            'name': 'Blue-Green',
            'description': 'Switch between two identical environments',
            'use_cases': ['Major updates', 'Database changes', 'Critical deployments'],
            'pros': ['Instant rollback', 'No downtime', 'Safe testing'],
            'cons': ['Requires duplicate infrastructure', 'Complex setup']
        }
    }
    
    return jsonify({
        'strategies': strategies,
        'dependency_types': {
            DependencyType.PREREQUISITE.value: 'Server must complete before target can start',
            DependencyType.BLOCKING.value: 'Servers cannot run at the same time',
            DependencyType.ORDERING.value: 'Servers must run in specific order',
            DependencyType.CONDITIONAL.value: 'Target runs only if condition is met'
        }
    }), 200


@orchestration_bp.route('/health', methods=['GET'])
@cross_origin()
def health_check():
    """Health check endpoint"""
    try:
        status = {
            'service': 'Multi-server Orchestration API',
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'coordinator_initialized': coordinator is not None,
            'active_plans': len(coordinator.orchestration_plans) if coordinator else 0,
            'execution_history_size': len(coordinator.execution_history) if coordinator else 0
        }
        return jsonify(status), 200
    except Exception as e:
        return jsonify({
            'service': 'Multi-server Orchestration API',
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


# Error handlers
@orchestration_bp.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request'}), 400


@orchestration_bp.errorhandler(401)
def unauthorized(error):
    return jsonify({'error': 'Unauthorized'}), 401


@orchestration_bp.errorhandler(403)
def forbidden(error):
    return jsonify({'error': 'Forbidden'}), 403


@orchestration_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@orchestration_bp.errorhandler(429)
def rate_limit_exceeded(error):
    return jsonify({'error': 'Rate limit exceeded'}), 429


@orchestration_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500