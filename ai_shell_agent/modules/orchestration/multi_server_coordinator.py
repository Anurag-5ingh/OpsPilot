"""
Multi-server Command Coordination

Orchestration engine for executing commands across multiple servers with
ML-enhanced risk assessment, dependency management, and failure recovery.
"""

import asyncio
import json
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Callable, Any
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import logging
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..ssh.ssh_manager import create_ssh_client
from ..command_generation.ml_risk_scorer import MLRiskScorer
from ..security.compliance_checker import SecurityComplianceChecker

logger = logging.getLogger(__name__)


class ExecutionStrategy(Enum):
    """Execution strategies for multi-server operations"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    ROLLING = "rolling"
    CANARY = "canary"
    BLUE_GREEN = "blue_green"


class ExecutionStatus(Enum):
    """Status of command execution"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"


class DependencyType(Enum):
    """Types of dependencies between servers/commands"""
    PREREQUISITE = "prerequisite"  # Must complete before
    BLOCKING = "blocking"           # Cannot run at same time
    ORDERING = "ordering"           # Must run in specific order
    CONDITIONAL = "conditional"     # Run only if condition met


@dataclass
class ServerTarget:
    """Represents a target server for command execution"""
    hostname: str
    ssh_config: Dict[str, Any]
    tags: List[str] = None
    priority: int = 1
    max_concurrent_commands: int = 1
    timeout_seconds: int = 300
    retry_count: int = 2
    custom_context: Dict[str, Any] = None


@dataclass
class CommandDependency:
    """Represents a dependency between commands or servers"""
    dependency_type: DependencyType
    source_server: str
    target_server: str
    condition: Optional[str] = None
    wait_for_completion: bool = True


@dataclass
class CommandExecution:
    """Represents a command execution on a specific server"""
    execution_id: str
    server: str
    command: str
    status: ExecutionStatus
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    output: str = ""
    error: str = ""
    exit_code: Optional[int] = None
    risk_assessment: Optional[Dict] = None
    compliance_check: Optional[Dict] = None
    retry_count: int = 0
    rollback_command: Optional[str] = None


@dataclass
class OrchestrationPlan:
    """Complete orchestration plan for multi-server execution"""
    plan_id: str
    name: str
    description: str
    execution_strategy: ExecutionStrategy
    servers: List[ServerTarget]
    commands: List[str]
    dependencies: List[CommandDependency]
    execution_phases: List[List[str]]  # Servers grouped by execution phase
    rollback_strategy: Dict[str, Any]
    estimated_duration: int
    risk_score: float
    created_at: datetime


class DependencyResolver:
    """Resolves dependencies and creates execution phases"""
    
    def __init__(self):
        pass
    
    def resolve_dependencies(self, servers: List[ServerTarget], 
                           dependencies: List[CommandDependency]) -> List[List[str]]:
        """
        Resolve dependencies and create execution phases
        
        Returns:
            List of phases, where each phase contains servers that can execute in parallel
        """
        # Build dependency graph
        dependency_graph = defaultdict(set)
        reverse_graph = defaultdict(set)
        
        for dep in dependencies:
            if dep.dependency_type in [DependencyType.PREREQUISITE, DependencyType.ORDERING]:
                dependency_graph[dep.target_server].add(dep.source_server)
                reverse_graph[dep.source_server].add(dep.target_server)
        
        # Topological sort to determine execution order
        server_names = [server.hostname for server in servers]
        in_degree = {server: len(dependency_graph[server]) for server in server_names}
        
        phases = []
        remaining_servers = set(server_names)
        
        while remaining_servers:
            # Find servers with no dependencies
            ready_servers = [server for server in remaining_servers 
                           if in_degree[server] == 0]
            
            if not ready_servers:
                # Circular dependency detected
                logger.warning("Circular dependency detected, breaking cycle")
                ready_servers = list(remaining_servers)[:1]
            
            phases.append(ready_servers)
            
            # Remove ready servers and update in-degrees
            for server in ready_servers:
                remaining_servers.remove(server)
                for dependent in reverse_graph[server]:
                    if dependent in remaining_servers:
                        in_degree[dependent] -= 1
        
        return phases
    
    def validate_dependencies(self, dependencies: List[CommandDependency], 
                            servers: List[ServerTarget]) -> List[str]:
        """Validate dependency configuration and return any issues"""
        issues = []
        server_names = {server.hostname for server in servers}
        
        for dep in dependencies:
            # Check if servers exist
            if dep.source_server not in server_names:
                issues.append(f"Source server '{dep.source_server}' not found in server list")
            
            if dep.target_server not in server_names:
                issues.append(f"Target server '{dep.target_server}' not found in server list")
            
            # Check for self-dependencies
            if dep.source_server == dep.target_server:
                issues.append(f"Server '{dep.source_server}' cannot depend on itself")
        
        return issues


class RiskAssessmentEngine:
    """Assesses risks of multi-server command execution"""
    
    def __init__(self, ml_scorer: MLRiskScorer, compliance_checker: SecurityComplianceChecker):
        self.ml_scorer = ml_scorer
        self.compliance_checker = compliance_checker
    
    def assess_orchestration_risk(self, plan: OrchestrationPlan, 
                                system_context: Dict) -> Dict[str, Any]:
        """
        Assess overall risk of orchestration plan
        
        Returns:
            Comprehensive risk assessment
        """
        assessment = {
            'overall_risk_score': 0.0,
            'risk_factors': [],
            'server_risks': {},
            'command_risks': {},
            'coordination_risks': [],
            'mitigation_suggestions': []
        }
        
        # Assess individual command risks
        command_risks = []
        for command in plan.commands:
            # Get ML risk assessment
            ml_risk = self.ml_scorer.predict_risk_level(command, system_context, None)
            
            # Get compliance assessment
            compliance_result = self.compliance_checker.check_command_compliance(
                command, system_context, {}
            )
            
            command_risk = {
                'command': command,
                'ml_risk_level': ml_risk.get('risk_level', 'unknown'),
                'ml_confidence': ml_risk.get('ml_confidence', 0.0),
                'compliance_violations': len(compliance_result.get('violations', [])),
                'compliance_score': compliance_result.get('compliance_score', 1.0)
            }
            command_risks.append(command_risk)
        
        assessment['command_risks'] = {cmd['command']: cmd for cmd in command_risks}
        
        # Assess server-level risks
        for server in plan.servers:
            server_risk = {
                'concurrent_commands': min(server.max_concurrent_commands, len(plan.commands)),
                'timeout_risk': 'high' if server.timeout_seconds < 60 else 'low',
                'retry_capability': 'good' if server.retry_count >= 2 else 'limited'
            }
            assessment['server_risks'][server.hostname] = server_risk
        
        # Assess coordination risks
        coordination_risks = []
        
        # Check for complex dependencies
        if len(plan.dependencies) > len(plan.servers):
            coordination_risks.append({
                'type': 'complex_dependencies',
                'severity': 'medium',
                'description': 'High number of dependencies may increase failure risk'
            })
        
        # Check execution strategy risks
        if plan.execution_strategy == ExecutionStrategy.PARALLEL and len(plan.servers) > 10:
            coordination_risks.append({
                'type': 'parallel_scale_risk',
                'severity': 'medium',
                'description': 'Parallel execution on many servers increases complexity'
            })
        
        assessment['coordination_risks'] = coordination_risks
        
        # Calculate overall risk score
        ml_risk_scores = [self._risk_level_to_score(cmd.get('ml_risk_level', 'low')) 
                         for cmd in command_risks]
        compliance_scores = [cmd.get('compliance_score', 1.0) for cmd in command_risks]
        
        avg_ml_risk = sum(ml_risk_scores) / len(ml_risk_scores) if ml_risk_scores else 0
        avg_compliance = sum(compliance_scores) / len(compliance_scores) if compliance_scores else 1.0
        
        coordination_penalty = len(coordination_risks) * 0.1
        scale_penalty = min(len(plan.servers) * 0.01, 0.2)  # Penalty for large deployments
        
        assessment['overall_risk_score'] = min(1.0, avg_ml_risk + (1.0 - avg_compliance) + 
                                             coordination_penalty + scale_penalty)
        
        # Generate mitigation suggestions
        assessment['mitigation_suggestions'] = self._generate_mitigation_suggestions(assessment)
        
        return assessment
    
    def _risk_level_to_score(self, risk_level: str) -> float:
        """Convert risk level to numeric score"""
        mapping = {'low': 0.1, 'medium': 0.4, 'high': 0.7, 'critical': 0.9}
        return mapping.get(str(risk_level).lower(), 0.5)
    
    def _generate_mitigation_suggestions(self, assessment: Dict) -> List[str]:
        """Generate risk mitigation suggestions"""
        suggestions = []
        
        if assessment['overall_risk_score'] > 0.7:
            suggestions.append("Consider breaking down into smaller batches")
            suggestions.append("Implement comprehensive rollback procedures")
        
        if assessment['coordination_risks']:
            suggestions.append("Review dependency configuration for optimization")
            suggestions.append("Consider sequential execution for critical operations")
        
        high_risk_commands = [cmd for cmd, data in assessment['command_risks'].items() 
                            if self._risk_level_to_score(data.get('ml_risk_level')) > 0.6]
        
        if high_risk_commands:
            suggestions.append(f"Review high-risk commands: {', '.join(high_risk_commands[:3])}")
        
        return suggestions


class ExecutionEngine:
    """Executes commands across multiple servers with coordination"""
    
    def __init__(self, max_workers: int = 10):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.active_connections = {}
        self.execution_history = deque(maxlen=1000)
    
    def execute_orchestration(self, plan: OrchestrationPlan, 
                           progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Execute orchestration plan across multiple servers
        
        Args:
            plan: Orchestration plan to execute
            progress_callback: Optional callback for progress updates
            
        Returns:
            Execution results and summary
        """
        start_time = datetime.now()
        
        execution_results = {
            'plan_id': plan.plan_id,
            'start_time': start_time,
            'end_time': None,
            'overall_status': ExecutionStatus.RUNNING,
            'server_results': {},
            'phase_results': [],
            'failed_servers': [],
            'rollback_performed': False,
            'execution_summary': {}
        }
        
        try:
            # Execute phases based on strategy
            if plan.execution_strategy == ExecutionStrategy.SEQUENTIAL:
                self._execute_sequential(plan, execution_results, progress_callback)
            elif plan.execution_strategy == ExecutionStrategy.PARALLEL:
                self._execute_parallel(plan, execution_results, progress_callback)
            elif plan.execution_strategy == ExecutionStrategy.ROLLING:
                self._execute_rolling(plan, execution_results, progress_callback)
            else:
                raise ValueError(f"Unsupported execution strategy: {plan.execution_strategy}")
            
            # Determine overall status
            if execution_results['failed_servers']:
                execution_results['overall_status'] = ExecutionStatus.FAILED
                
                # Consider rollback if configured
                if plan.rollback_strategy.get('auto_rollback', False):
                    logger.info("Auto-rollback triggered due to failures")
                    self._perform_rollback(plan, execution_results)
            else:
                execution_results['overall_status'] = ExecutionStatus.COMPLETED
        
        except Exception as e:
            logger.error(f"Orchestration execution failed: {e}")
            execution_results['overall_status'] = ExecutionStatus.FAILED
            execution_results['error'] = str(e)
        
        finally:
            execution_results['end_time'] = datetime.now()
            execution_results['total_duration'] = (
                execution_results['end_time'] - start_time
            ).total_seconds()
            
            # Generate execution summary
            execution_results['execution_summary'] = self._generate_execution_summary(
                execution_results
            )
        
        # Store in history
        self.execution_history.append(execution_results)
        
        return execution_results
    
    def _execute_sequential(self, plan: OrchestrationPlan, results: Dict, 
                          progress_callback: Optional[Callable]):
        """Execute commands sequentially across phases"""
        for phase_idx, phase_servers in enumerate(plan.execution_phases):
            phase_start = datetime.now()
            phase_result = {
                'phase_index': phase_idx,
                'servers': phase_servers,
                'start_time': phase_start,
                'server_results': {}
            }
            
            # Execute all commands on each server in the phase
            for server_name in phase_servers:
                server = next(s for s in plan.servers if s.hostname == server_name)
                server_results = []
                
                for command in plan.commands:
                    exec_result = self._execute_command_on_server(server, command)
                    server_results.append(exec_result)
                    results['server_results'].setdefault(server_name, []).append(exec_result)
                    
                    if exec_result.status == ExecutionStatus.FAILED:
                        results['failed_servers'].append(server_name)
                        if not plan.rollback_strategy.get('continue_on_failure', False):
                            return  # Stop execution on failure
                
                phase_result['server_results'][server_name] = server_results
            
            phase_result['end_time'] = datetime.now()
            phase_result['duration'] = (phase_result['end_time'] - phase_start).total_seconds()
            results['phase_results'].append(phase_result)
            
            if progress_callback:
                progress_callback({
                    'phase': phase_idx + 1,
                    'total_phases': len(plan.execution_phases),
                    'completed_servers': len(phase_result['server_results']),
                    'failed_servers': len(results['failed_servers'])
                })
    
    def _execute_parallel(self, plan: OrchestrationPlan, results: Dict,
                        progress_callback: Optional[Callable]):
        """Execute commands in parallel across all servers"""
        futures = []
        
        for server in plan.servers:
            for command in plan.commands:
                future = self.executor.submit(self._execute_command_on_server, server, command)
                futures.append((future, server.hostname, command))
        
        completed = 0
        for future, server_name, command in as_completed(futures):
            try:
                exec_result = future.result()
                results['server_results'].setdefault(server_name, []).append(exec_result)
                
                if exec_result.status == ExecutionStatus.FAILED:
                    results['failed_servers'].append(server_name)
                
            except Exception as e:
                logger.error(f"Command execution failed on {server_name}: {e}")
                results['failed_servers'].append(server_name)
            
            completed += 1
            if progress_callback:
                progress_callback({
                    'completed': completed,
                    'total': len(futures),
                    'failed_servers': len(set(results['failed_servers']))
                })
    
    def _execute_rolling(self, plan: OrchestrationPlan, results: Dict,
                       progress_callback: Optional[Callable]):
        """Execute commands in rolling fashion with batches"""
        batch_size = plan.rollback_strategy.get('rolling_batch_size', 2)
        servers = [s.hostname for s in plan.servers]
        
        for batch_start in range(0, len(servers), batch_size):
            batch_servers = servers[batch_start:batch_start + batch_size]
            batch_results = {}
            
            # Execute commands on current batch
            futures = []
            for server_name in batch_servers:
                server = next(s for s in plan.servers if s.hostname == server_name)
                for command in plan.commands:
                    future = self.executor.submit(self._execute_command_on_server, server, command)
                    futures.append((future, server_name, command))
            
            # Wait for batch completion
            batch_failed = []
            for future, server_name, command in futures:
                try:
                    exec_result = future.result()
                    results['server_results'].setdefault(server_name, []).append(exec_result)
                    
                    if exec_result.status == ExecutionStatus.FAILED:
                        batch_failed.append(server_name)
                
                except Exception as e:
                    logger.error(f"Rolling execution failed on {server_name}: {e}")
                    batch_failed.append(server_name)
            
            results['failed_servers'].extend(batch_failed)
            
            # Check if we should continue
            failure_threshold = plan.rollback_strategy.get('failure_threshold', 0.5)
            if len(batch_failed) / len(batch_servers) > failure_threshold:
                logger.warning("Rolling deployment stopped due to high failure rate")
                break
            
            if progress_callback:
                progress_callback({
                    'batch': batch_start // batch_size + 1,
                    'total_batches': (len(servers) + batch_size - 1) // batch_size,
                    'failed_in_batch': len(batch_failed)
                })
    
    def _execute_command_on_server(self, server: ServerTarget, command: str) -> CommandExecution:
        """Execute single command on specific server"""
        execution_id = f"{server.hostname}_{int(time.time())}"
        
        execution = CommandExecution(
            execution_id=execution_id,
            server=server.hostname,
            command=command,
            status=ExecutionStatus.RUNNING,
            start_time=datetime.now()
        )
        
        try:
            # Get SSH connection
            ssh_client = self._get_ssh_connection(server)
            if not ssh_client:
                execution.status = ExecutionStatus.FAILED
                execution.error = "Failed to establish SSH connection"
                return execution
            
            # Execute command with timeout
            stdin, stdout, stderr = ssh_client.exec_command(
                command, timeout=server.timeout_seconds
            )
            
            # Read results
            execution.output = stdout.read().decode('utf-8', errors='ignore')
            execution.error = stderr.read().decode('utf-8', errors='ignore')
            execution.exit_code = stdout.channel.recv_exit_status()
            
            # Determine status
            if execution.exit_code == 0:
                execution.status = ExecutionStatus.COMPLETED
            else:
                execution.status = ExecutionStatus.FAILED
        
        except Exception as e:
            execution.status = ExecutionStatus.FAILED
            execution.error = str(e)
            logger.error(f"Command execution failed on {server.hostname}: {e}")
        
        finally:
            execution.end_time = datetime.now()
        
        return execution
    
    def _get_ssh_connection(self, server: ServerTarget):
        """Get or create SSH connection for server"""
        if server.hostname in self.active_connections:
            ssh_client = self.active_connections[server.hostname]
            try:
                # Test connection
                ssh_client.exec_command('echo test', timeout=5)
                return ssh_client
            except:
                try:
                    ssh_client.close()
                except:
                    pass
                del self.active_connections[server.hostname]
        
        # Create new connection
        try:
            ssh_client = create_ssh_client(
                server.hostname,
                server.ssh_config.get('username'),
                server.ssh_config.get('port', 22),
                server.ssh_config.get('password')
            )
            
            if ssh_client:
                self.active_connections[server.hostname] = ssh_client
                return ssh_client
        
        except Exception as e:
            logger.error(f"Failed to create SSH connection to {server.hostname}: {e}")
        
        return None
    
    def _perform_rollback(self, plan: OrchestrationPlan, results: Dict):
        """Perform rollback operations"""
        logger.info("Starting rollback operations")
        
        rollback_commands = []
        for server_name, executions in results['server_results'].items():
            for execution in executions:
                if execution.status == ExecutionStatus.COMPLETED and execution.rollback_command:
                    rollback_commands.append((server_name, execution.rollback_command))
        
        # Execute rollback commands in reverse order
        for server_name, rollback_command in reversed(rollback_commands):
            server = next(s for s in plan.servers if s.hostname == server_name)
            try:
                rollback_result = self._execute_command_on_server(server, rollback_command)
                if rollback_result.status == ExecutionStatus.COMPLETED:
                    logger.info(f"Rollback successful on {server_name}")
                else:
                    logger.error(f"Rollback failed on {server_name}: {rollback_result.error}")
            except Exception as e:
                logger.error(f"Rollback error on {server_name}: {e}")
        
        results['rollback_performed'] = True
    
    def _generate_execution_summary(self, results: Dict) -> Dict:
        """Generate execution summary statistics"""
        total_servers = len(results['server_results'])
        failed_servers = len(results['failed_servers'])
        successful_servers = total_servers - failed_servers
        
        total_commands = sum(len(executions) for executions in results['server_results'].values())
        successful_commands = sum(
            1 for executions in results['server_results'].values()
            for exec in executions if exec.status == ExecutionStatus.COMPLETED
        )
        
        return {
            'total_servers': total_servers,
            'successful_servers': successful_servers,
            'failed_servers': failed_servers,
            'success_rate': successful_servers / total_servers if total_servers > 0 else 0,
            'total_commands': total_commands,
            'successful_commands': successful_commands,
            'command_success_rate': successful_commands / total_commands if total_commands > 0 else 0,
            'total_duration': results.get('total_duration', 0)
        }
    
    def close_connections(self):
        """Close all SSH connections"""
        for hostname, ssh_client in self.active_connections.items():
            try:
                ssh_client.close()
            except:
                pass
        self.active_connections.clear()


class MultiServerCoordinator:
    """
    Main coordinator for multi-server command execution with ML-enhanced
    risk assessment and intelligent orchestration capabilities.
    """
    
    def __init__(self, ml_scorer: Optional[MLRiskScorer] = None,
                 compliance_checker: Optional[SecurityComplianceChecker] = None):
        """Initialize multi-server coordinator"""
        self.ml_scorer = ml_scorer or MLRiskScorer()
        self.compliance_checker = compliance_checker or SecurityComplianceChecker()
        
        # Components
        self.dependency_resolver = DependencyResolver()
        self.risk_engine = RiskAssessmentEngine(self.ml_scorer, self.compliance_checker)
        self.execution_engine = ExecutionEngine()
        
        # State
        self.orchestration_plans = {}
        self.execution_history = deque(maxlen=100)
        
        # Callbacks
        self.progress_callbacks = []
    
    def create_orchestration_plan(self, name: str, servers: List[Dict], 
                                commands: List[str], execution_config: Dict,
                                system_context: Dict = None) -> OrchestrationPlan:
        """
        Create comprehensive orchestration plan
        
        Args:
            name: Plan name
            servers: List of server configurations
            commands: Commands to execute
            execution_config: Execution configuration
            system_context: System context for risk assessment
            
        Returns:
            Complete orchestration plan
        """
        plan_id = f"plan_{int(time.time())}"
        
        # Convert server configs to ServerTarget objects
        server_targets = []
        for server_config in servers:
            server_targets.append(ServerTarget(
                hostname=server_config['hostname'],
                ssh_config=server_config.get('ssh_config', {}),
                tags=server_config.get('tags', []),
                priority=server_config.get('priority', 1),
                max_concurrent_commands=server_config.get('max_concurrent', 1),
                timeout_seconds=server_config.get('timeout', 300),
                retry_count=server_config.get('retry_count', 2),
                custom_context=server_config.get('context', {})
            ))
        
        # Parse dependencies
        dependencies = []
        for dep_config in execution_config.get('dependencies', []):
            dependencies.append(CommandDependency(
                dependency_type=DependencyType(dep_config['type']),
                source_server=dep_config['source'],
                target_server=dep_config['target'],
                condition=dep_config.get('condition'),
                wait_for_completion=dep_config.get('wait', True)
            ))
        
        # Validate dependencies
        dependency_issues = self.dependency_resolver.validate_dependencies(dependencies, server_targets)
        if dependency_issues:
            raise ValueError(f"Dependency validation failed: {'; '.join(dependency_issues)}")
        
        # Resolve execution phases
        execution_phases = self.dependency_resolver.resolve_dependencies(server_targets, dependencies)
        
        # Create plan
        plan = OrchestrationPlan(
            plan_id=plan_id,
            name=name,
            description=execution_config.get('description', ''),
            execution_strategy=ExecutionStrategy(execution_config.get('strategy', 'sequential')),
            servers=server_targets,
            commands=commands,
            dependencies=dependencies,
            execution_phases=execution_phases,
            rollback_strategy=execution_config.get('rollback', {}),
            estimated_duration=self._estimate_duration(server_targets, commands),
            risk_score=0.0,  # Will be calculated
            created_at=datetime.now()
        )
        
        # Assess risks
        if system_context:
            risk_assessment = self.risk_engine.assess_orchestration_risk(plan, system_context)
            plan.risk_score = risk_assessment['overall_risk_score']
        
        # Store plan
        self.orchestration_plans[plan_id] = plan
        
        return plan
    
    def execute_plan(self, plan_id: str, 
                    progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Execute orchestration plan"""
        if plan_id not in self.orchestration_plans:
            raise ValueError(f"Plan {plan_id} not found")
        
        plan = self.orchestration_plans[plan_id]
        
        # Execute with progress tracking
        def combined_callback(progress_data):
            # Call registered callbacks
            for callback in self.progress_callbacks:
                try:
                    callback(plan_id, progress_data)
                except Exception as e:
                    logger.error(f"Progress callback failed: {e}")
            
            # Call specific callback
            if progress_callback:
                progress_callback(progress_data)
        
        results = self.execution_engine.execute_orchestration(plan, combined_callback)
        
        # Store in history
        self.execution_history.append({
            'plan_id': plan_id,
            'execution_time': results['start_time'],
            'results': results
        })
        
        return results
    
    def get_plan_risk_assessment(self, plan_id: str, 
                               system_context: Dict) -> Dict[str, Any]:
        """Get comprehensive risk assessment for plan"""
        if plan_id not in self.orchestration_plans:
            raise ValueError(f"Plan {plan_id} not found")
        
        plan = self.orchestration_plans[plan_id]
        return self.risk_engine.assess_orchestration_risk(plan, system_context)
    
    def simulate_plan_execution(self, plan_id: str) -> Dict[str, Any]:
        """Simulate plan execution without actually running commands"""
        if plan_id not in self.orchestration_plans:
            raise ValueError(f"Plan {plan_id} not found")
        
        plan = self.orchestration_plans[plan_id]
        
        simulation = {
            'plan_id': plan_id,
            'execution_phases': plan.execution_phases,
            'estimated_duration': plan.estimated_duration,
            'server_count': len(plan.servers),
            'command_count': len(plan.commands),
            'dependency_count': len(plan.dependencies),
            'risk_score': plan.risk_score,
            'simulation_warnings': []
        }
        
        # Add warnings based on plan characteristics
        if plan.risk_score > 0.7:
            simulation['simulation_warnings'].append("High risk score detected")
        
        if len(plan.servers) > 20:
            simulation['simulation_warnings'].append("Large number of servers may impact performance")
        
        if plan.execution_strategy == ExecutionStrategy.PARALLEL and len(plan.dependencies) > 0:
            simulation['simulation_warnings'].append("Parallel execution with dependencies may cause conflicts")
        
        return simulation
    
    def _estimate_duration(self, servers: List[ServerTarget], commands: List[str]) -> int:
        """Estimate execution duration in seconds"""
        # Simple estimation - can be enhanced with historical data
        avg_command_time = 30  # seconds per command
        total_commands = len(commands) * len(servers)
        
        # Adjust based on server capabilities
        max_concurrent = max(server.max_concurrent_commands for server in servers)
        parallelization_factor = min(max_concurrent, total_commands) / total_commands
        
        return int(total_commands * avg_command_time * (1 - parallelization_factor * 0.5))
    
    def add_progress_callback(self, callback: Callable[[str, Dict], None]):
        """Add callback for execution progress updates"""
        self.progress_callbacks.append(callback)
    
    def get_execution_history(self, limit: int = 10) -> List[Dict]:
        """Get recent execution history"""
        return list(self.execution_history)[-limit:]
    
    def get_plan_summary(self, plan_id: str) -> Optional[Dict]:
        """Get summary of orchestration plan"""
        if plan_id not in self.orchestration_plans:
            return None
        
        plan = self.orchestration_plans[plan_id]
        return {
            'plan_id': plan.plan_id,
            'name': plan.name,
            'description': plan.description,
            'server_count': len(plan.servers),
            'command_count': len(plan.commands),
            'execution_strategy': plan.execution_strategy.value,
            'risk_score': plan.risk_score,
            'estimated_duration': plan.estimated_duration,
            'created_at': plan.created_at.isoformat(),
            'has_dependencies': len(plan.dependencies) > 0
        }
    
    def cleanup(self):
        """Cleanup resources"""
        self.execution_engine.close_connections()