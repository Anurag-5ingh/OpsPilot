"""
Smart Documentation Generator

ML-powered system that automatically generates documentation, explanations,
and runbooks for command sequences based on execution patterns and outcomes.
"""

import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum
import logging

from ..command_generation.ml_database_manager import MLDatabaseManager

logger = logging.getLogger(__name__)


class DocumentationType(Enum):
    """Types of documentation that can be generated"""
    RUNBOOK = "runbook"
    TROUBLESHOOTING_GUIDE = "troubleshooting_guide"
    COMMAND_REFERENCE = "command_reference"
    OPERATIONAL_PROCEDURE = "operational_procedure"
    INCIDENT_RESPONSE = "incident_response"
    DEPLOYMENT_GUIDE = "deployment_guide"


class DocumentationFormat(Enum):
    """Output formats for generated documentation"""
    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"
    PLAIN_TEXT = "plain_text"


@dataclass
class CommandStep:
    """Represents a single step in a procedure"""
    step_number: int
    command: str
    description: str
    expected_output: str
    risk_level: str
    prerequisites: List[str]
    troubleshooting_notes: List[str]
    estimated_duration: Optional[str] = None
    rollback_command: Optional[str] = None


@dataclass 
class GeneratedDocumentation:
    """Complete generated documentation"""
    id: str
    title: str
    doc_type: DocumentationType
    description: str
    steps: List[CommandStep]
    prerequisites: List[str]
    warnings: List[str]
    metadata: Dict
    generated_at: str
    confidence_score: float
    sources: List[str]


class PatternAnalyzer:
    """
    Analyzes command execution patterns to identify common workflows
    and operational procedures that can be documented.
    """
    
    def __init__(self, db_manager: MLDatabaseManager):
        self.db_manager = db_manager
        
    def identify_command_sequences(self, days_back: int = 30) -> List[Dict]:
        """
        Identify frequently executed command sequences that form procedures
        
        Returns:
            List of command sequences with metadata
        """
        # Get command execution data
        df = self.db_manager.get_training_dataset(days_back=days_back, min_samples=1)
        
        if df.empty:
            return []
        
        # Group commands by session and user to identify sequences
        sequences = []
        
        for session_id in df['session_id'].unique():
            session_commands = df[df['session_id'] == session_id].sort_values('timestamp')
            
            if len(session_commands) > 1:  # Multi-command sequences
                sequence = {
                    'session_id': session_id,
                    'commands': session_commands['command'].tolist(),
                    'success_rate': session_commands['execution_success'].mean(),
                    'user_id': session_commands['user_id'].iloc[0] if len(session_commands) else 'unknown',
                    'system_context': json.loads(session_commands['system_context'].iloc[0]) if len(session_commands) else {},
                    'frequency': 1
                }
                sequences.append(sequence)
        
        # Find similar sequences and calculate frequency
        pattern_groups = self._group_similar_sequences(sequences)
        
        return pattern_groups
    
    def _group_similar_sequences(self, sequences: List[Dict]) -> List[Dict]:
        """Group similar command sequences together"""
        groups = {}
        
        for seq in sequences:
            # Create pattern signature based on command types
            pattern_sig = self._create_pattern_signature(seq['commands'])
            
            if pattern_sig in groups:
                groups[pattern_sig]['frequency'] += 1
                groups[pattern_sig]['sequences'].append(seq)
                # Update success rate
                total_success = groups[pattern_sig]['avg_success_rate'] * (groups[pattern_sig]['frequency'] - 1)
                total_success += seq['success_rate']
                groups[pattern_sig]['avg_success_rate'] = total_success / groups[pattern_sig]['frequency']
            else:
                groups[pattern_sig] = {
                    'pattern': pattern_sig,
                    'frequency': 1,
                    'avg_success_rate': seq['success_rate'],
                    'sequences': [seq],
                    'sample_commands': seq['commands']
                }
        
        # Filter for frequently used patterns (frequency > 2)
        return [group for group in groups.values() if group['frequency'] > 2]
    
    def _create_pattern_signature(self, commands: List[str]) -> str:
        """Create a signature for command sequence pattern recognition"""
        # Extract command types (first word of each command)
        cmd_types = []
        for cmd in commands:
            cmd_parts = cmd.strip().split()
            if cmd_parts:
                base_cmd = cmd_parts[0].lower()
                # Normalize common variations
                if base_cmd == 'sudo':
                    base_cmd = cmd_parts[1] if len(cmd_parts) > 1 else 'sudo'
                cmd_types.append(base_cmd)
        
        return ' -> '.join(cmd_types)
    
    def analyze_troubleshooting_patterns(self) -> List[Dict]:
        """Analyze patterns in troubleshooting command sequences"""
        df = self.db_manager.get_training_dataset(days_back=90, min_samples=1)
        
        if df.empty:
            return []
        
        # Find sequences that start with failed commands followed by fixes
        troubleshooting_patterns = []
        
        # Group by similar error patterns
        failed_commands = df[df['execution_success'] == False]
        
        for _, failed_cmd in failed_commands.iterrows():
            # Look for subsequent successful commands in same session
            session_data = df[df['session_id'] == failed_cmd['session_id']]
            session_data = session_data.sort_values('timestamp')
            
            failed_index = session_data.index.get_loc(failed_cmd.name)
            subsequent_commands = session_data.iloc[failed_index + 1:]
            successful_fixes = subsequent_commands[subsequent_commands['execution_success'] == True]
            
            if not successful_fixes.empty:
                pattern = {
                    'failed_command': failed_cmd['command'],
                    'error_pattern': self._extract_error_pattern(failed_cmd.get('stderr', '')),
                    'fix_commands': successful_fixes['command'].tolist()[:3],  # First 3 fixes
                    'success_rate': len(successful_fixes) / len(subsequent_commands) if len(subsequent_commands) > 0 else 0
                }
                troubleshooting_patterns.append(pattern)
        
        return troubleshooting_patterns
    
    def _extract_error_pattern(self, error_text: str) -> str:
        """Extract common error patterns from error text"""
        if not error_text:
            return "unknown_error"
        
        # Common error patterns
        patterns = {
            'permission_denied': r'permission denied',
            'command_not_found': r'command not found',
            'no_such_file': r'no such file or directory',
            'connection_refused': r'connection refused',
            'port_in_use': r'address already in use',
            'disk_full': r'no space left on device',
            'service_failed': r'failed to start|service failed'
        }
        
        for pattern_name, regex in patterns.items():
            if re.search(regex, error_text, re.IGNORECASE):
                return pattern_name
        
        return 'unknown_error'


class DocumentationTemplates:
    """Templates for different types of documentation"""
    
    @staticmethod
    def get_runbook_template() -> str:
        return """# {title}

## Overview
{description}

## Prerequisites
{prerequisites}

## Warnings and Cautions
{warnings}

## Procedure Steps

{steps}

## Troubleshooting
{troubleshooting}

## Rollback Procedures
{rollback_procedures}

---
*Generated by Smart Documentation Generator on {generated_at}*
*Confidence Score: {confidence_score}/1.0*
*Based on {source_count} execution patterns*
"""
    
    @staticmethod
    def get_troubleshooting_template() -> str:
        return """# {title} - Troubleshooting Guide

## Problem Description
{description}

## Common Symptoms
{symptoms}

## Diagnostic Steps
{diagnostic_steps}

## Resolution Steps
{resolution_steps}

## Prevention
{prevention_tips}

---
*Auto-generated from {source_count} similar incidents*
*Last updated: {generated_at}*
"""
    
    @staticmethod
    def get_command_reference_template() -> str:
        return """# {title} - Command Reference

## Description
{description}

## Usage Examples
{usage_examples}

## Parameters and Options
{parameters}

## Common Patterns
{common_patterns}

## Safety Notes
{safety_notes}

---
*Generated from {source_count} command executions*
*Success Rate: {success_rate}%*
"""


class SmartDocumentationGenerator:
    """
    Main documentation generator that uses ML insights to create
    intelligent documentation from command execution patterns.
    """
    
    def __init__(self, db_manager: Optional[MLDatabaseManager] = None):
        """Initialize documentation generator"""
        self.db_manager = db_manager or MLDatabaseManager()
        self.pattern_analyzer = PatternAnalyzer(self.db_manager)
        self.templates = DocumentationTemplates()
        self.generated_docs = {}
        
    def generate_runbook_from_pattern(self, pattern: Dict, 
                                    title: Optional[str] = None) -> GeneratedDocumentation:
        """
        Generate runbook documentation from identified command pattern
        
        Args:
            pattern: Command pattern from pattern analyzer
            title: Optional custom title
            
        Returns:
            Generated runbook documentation
        """
        if not title:
            title = f"Procedure: {pattern['pattern'].replace(' -> ', ' → ')}"
        
        # Analyze pattern for documentation
        steps = []
        sample_commands = pattern.get('sample_commands', [])
        
        for i, command in enumerate(sample_commands):
            # Get additional context from database
            cmd_analysis = self._analyze_command_context(command)
            
            step = CommandStep(
                step_number=i + 1,
                command=command,
                description=self._generate_step_description(command, cmd_analysis),
                expected_output=cmd_analysis.get('typical_output', 'Command completes successfully'),
                risk_level=cmd_analysis.get('risk_level', 'low'),
                prerequisites=cmd_analysis.get('prerequisites', []),
                troubleshooting_notes=cmd_analysis.get('troubleshooting_tips', []),
                estimated_duration=cmd_analysis.get('avg_duration', None),
                rollback_command=cmd_analysis.get('rollback_command', None)
            )
            steps.append(step)
        
        # Generate comprehensive documentation
        doc = GeneratedDocumentation(
            id=f"runbook_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            title=title,
            doc_type=DocumentationType.RUNBOOK,
            description=self._generate_runbook_description(pattern),
            steps=steps,
            prerequisites=self._extract_overall_prerequisites(steps),
            warnings=self._generate_warnings(steps, pattern),
            metadata={
                'pattern_frequency': pattern['frequency'],
                'avg_success_rate': pattern['avg_success_rate'],
                'command_count': len(sample_commands),
                'pattern_signature': pattern['pattern']
            },
            generated_at=datetime.now().isoformat(),
            confidence_score=self._calculate_confidence_score(pattern),
            sources=[f"Pattern analysis of {pattern['frequency']} executions"]
        )
        
        self.generated_docs[doc.id] = doc
        return doc
    
    def generate_troubleshooting_guide(self, error_pattern: str, 
                                     title: Optional[str] = None) -> GeneratedDocumentation:
        """
        Generate troubleshooting guide based on historical error resolutions
        
        Args:
            error_pattern: Error pattern to generate guide for
            title: Optional custom title
            
        Returns:
            Generated troubleshooting documentation
        """
        if not title:
            title = f"Troubleshooting: {error_pattern.replace('_', ' ').title()}"
        
        # Find similar troubleshooting patterns
        patterns = self.pattern_analyzer.analyze_troubleshooting_patterns()
        relevant_patterns = [p for p in patterns if p['error_pattern'] == error_pattern]
        
        if not relevant_patterns:
            # Generate generic troubleshooting guide
            return self._generate_generic_troubleshooting_guide(error_pattern, title)
        
        # Combine patterns for comprehensive guide
        diagnostic_steps = []
        resolution_steps = []
        
        step_num = 1
        for pattern in relevant_patterns:
            # Add diagnostic step
            diagnostic_steps.append(CommandStep(
                step_number=step_num,
                command=pattern['failed_command'],
                description=f"Reproduce the error to confirm the issue",
                expected_output="Error should occur consistently",
                risk_level="low",
                prerequisites=[],
                troubleshooting_notes=[f"Original error pattern: {pattern['error_pattern']}"]
            ))
            step_num += 1
            
            # Add resolution steps
            for fix_cmd in pattern['fix_commands']:
                resolution_steps.append(CommandStep(
                    step_number=step_num,
                    command=fix_cmd,
                    description=self._generate_step_description(fix_cmd, {}),
                    expected_output="Issue should be resolved",
                    risk_level=self._assess_command_risk(fix_cmd),
                    prerequisites=[],
                    troubleshooting_notes=[]
                ))
                step_num += 1
        
        all_steps = diagnostic_steps + resolution_steps
        
        doc = GeneratedDocumentation(
            id=f"troubleshoot_{error_pattern}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            title=title,
            doc_type=DocumentationType.TROUBLESHOOTING_GUIDE,
            description=f"Comprehensive troubleshooting guide for {error_pattern} issues based on historical resolutions.",
            steps=all_steps,
            prerequisites=[],
            warnings=self._generate_troubleshooting_warnings(relevant_patterns),
            metadata={
                'error_pattern': error_pattern,
                'pattern_count': len(relevant_patterns),
                'avg_success_rate': sum(p['success_rate'] for p in relevant_patterns) / len(relevant_patterns)
            },
            generated_at=datetime.now().isoformat(),
            confidence_score=self._calculate_troubleshooting_confidence(relevant_patterns),
            sources=[f"Analysis of {len(relevant_patterns)} similar troubleshooting cases"]
        )
        
        self.generated_docs[doc.id] = doc
        return doc
    
    def generate_command_reference(self, command_pattern: str,
                                 title: Optional[str] = None) -> GeneratedDocumentation:
        """
        Generate command reference documentation based on usage patterns
        
        Args:
            command_pattern: Base command to document
            title: Optional custom title
            
        Returns:
            Generated command reference documentation
        """
        if not title:
            title = f"{command_pattern} Command Reference"
        
        # Analyze command usage patterns
        df = self.db_manager.get_training_dataset(days_back=90, min_samples=1)
        
        if df.empty:
            return self._generate_generic_command_reference(command_pattern, title)
        
        # Filter commands matching pattern
        matching_commands = df[df['command'].str.contains(command_pattern, case=False, na=False)]
        
        if matching_commands.empty:
            return self._generate_generic_command_reference(command_pattern, title)
        
        # Analyze usage patterns
        usage_analysis = self._analyze_command_usage(matching_commands)
        
        # Create reference steps
        steps = []
        step_num = 1
        
        for usage_pattern in usage_analysis['common_patterns']:
            step = CommandStep(
                step_number=step_num,
                command=usage_pattern['example'],
                description=usage_pattern['description'],
                expected_output=usage_pattern['typical_output'],
                risk_level=usage_pattern['risk_level'],
                prerequisites=usage_pattern.get('prerequisites', []),
                troubleshooting_notes=usage_pattern.get('notes', [])
            )
            steps.append(step)
            step_num += 1
        
        doc = GeneratedDocumentation(
            id=f"cmdref_{command_pattern}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            title=title,
            doc_type=DocumentationType.COMMAND_REFERENCE,
            description=f"Reference documentation for {command_pattern} based on actual usage patterns.",
            steps=steps,
            prerequisites=[],
            warnings=usage_analysis.get('warnings', []),
            metadata={
                'command_pattern': command_pattern,
                'total_executions': len(matching_commands),
                'success_rate': matching_commands['execution_success'].mean(),
                'unique_variations': matching_commands['command'].nunique()
            },
            generated_at=datetime.now().isoformat(),
            confidence_score=usage_analysis.get('confidence_score', 0.5),
            sources=[f"Analysis of {len(matching_commands)} command executions"]
        )
        
        self.generated_docs[doc.id] = doc
        return doc
    
    def _analyze_command_context(self, command: str) -> Dict:
        """Analyze command context from historical data"""
        df = self.db_manager.get_training_dataset(days_back=60, min_samples=1)
        
        if df.empty:
            return {}
        
        matching_commands = df[df['command'] == command]
        
        if matching_commands.empty:
            return {}
        
        return {
            'success_rate': matching_commands['execution_success'].mean(),
            'avg_duration': f"{matching_commands['execution_time_ms'].mean() / 1000:.1f}s" if not matching_commands['execution_time_ms'].isna().all() else None,
            'risk_level': self._assess_command_risk(command),
            'typical_output': 'Success',
            'prerequisites': [],
            'troubleshooting_tips': []
        }
    
    def _generate_step_description(self, command: str, analysis: Dict) -> str:
        """Generate description for command step"""
        # Extract command type
        cmd_parts = command.strip().split()
        if not cmd_parts:
            return "Execute command"
        
        base_cmd = cmd_parts[0].lower()
        if base_cmd == 'sudo':
            base_cmd = cmd_parts[1] if len(cmd_parts) > 1 else 'sudo'
        
        # Command-specific descriptions
        descriptions = {
            'ls': 'List directory contents',
            'cd': 'Change current directory',
            'mkdir': 'Create directory',
            'rm': 'Remove files or directories',
            'cp': 'Copy files or directories',
            'mv': 'Move or rename files',
            'chmod': 'Change file permissions',
            'chown': 'Change file ownership',
            'systemctl': 'Manage system services',
            'service': 'Control system services',
            'ps': 'Display running processes',
            'top': 'Display system processes',
            'grep': 'Search text patterns',
            'find': 'Search for files and directories',
            'wget': 'Download files from web',
            'curl': 'Transfer data to/from server',
            'ssh': 'Connect to remote server',
            'scp': 'Copy files over SSH',
            'tar': 'Archive files',
            'apt': 'Manage packages (Debian/Ubuntu)',
            'yum': 'Manage packages (RedHat/CentOS)',
            'pip': 'Install Python packages'
        }
        
        base_description = descriptions.get(base_cmd, f"Execute {base_cmd} command")
        
        # Add context if available
        if analysis.get('success_rate'):
            success_rate = analysis['success_rate']
            if success_rate < 0.7:
                base_description += " (Warning: Lower success rate in historical data)"
        
        return base_description
    
    def _assess_command_risk(self, command: str) -> str:
        """Assess risk level of command"""
        high_risk_patterns = [
            r'\brm\s.*-r',  # Recursive delete
            r'\bchmod.*777',  # Dangerous permissions
            r'\biptables.*-F',  # Flush firewall
            r'\bmkfs\.',  # Format filesystem
            r'\bdd\s.*of='  # Direct disk write
        ]
        
        medium_risk_patterns = [
            r'\bsudo\s',  # Requires elevated privileges
            r'\bchmod\s',  # Change permissions
            r'\bchown\s',  # Change ownership
            r'\bsystemctl\s.*(stop|disable)',  # Stop services
            r'\buseradd\s',  # Add users
        ]
        
        for pattern in high_risk_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return 'high'
        
        for pattern in medium_risk_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return 'medium'
        
        return 'low'
    
    def _generate_runbook_description(self, pattern: Dict) -> str:
        """Generate description for runbook"""
        return f"""This runbook documents a commonly executed procedure pattern.
        
**Pattern**: {pattern['pattern']}
**Frequency**: Executed {pattern['frequency']} times
**Success Rate**: {pattern['avg_success_rate']:.1%}

This procedure has been automatically identified from execution patterns and represents a standardized workflow."""
    
    def _extract_overall_prerequisites(self, steps: List[CommandStep]) -> List[str]:
        """Extract overall prerequisites from steps"""
        all_prereqs = set()
        
        for step in steps:
            all_prereqs.update(step.prerequisites)
        
        # Add common prerequisites based on commands
        commands = [step.command for step in steps]
        
        if any('sudo' in cmd for cmd in commands):
            all_prereqs.add("Administrative privileges (sudo access)")
        
        if any(re.search(r'\b(ssh|scp)\s', cmd) for cmd in commands):
            all_prereqs.add("SSH access to target servers")
        
        if any(re.search(r'\b(systemctl|service)\s', cmd) for cmd in commands):
            all_prereqs.add("Service management permissions")
        
        return sorted(list(all_prereqs))
    
    def _generate_warnings(self, steps: List[CommandStep], pattern: Dict) -> List[str]:
        """Generate warnings for runbook"""
        warnings = []
        
        # Check for high-risk commands
        high_risk_steps = [step for step in steps if step.risk_level == 'high']
        if high_risk_steps:
            warnings.append(f"⚠️ This procedure contains {len(high_risk_steps)} high-risk commands")
        
        # Check success rate
        if pattern['avg_success_rate'] < 0.8:
            warnings.append(f"⚠️ Historical success rate is {pattern['avg_success_rate']:.1%} - exercise caution")
        
        # Add command-specific warnings
        commands = [step.command for step in steps]
        
        if any('rm' in cmd for cmd in commands):
            warnings.append("🗑️ This procedure includes file deletion commands - ensure backups are available")
        
        if any(re.search(r'\b(systemctl|service).*stop', cmd) for cmd in commands):
            warnings.append("🛑 This procedure stops services - plan for potential downtime")
        
        return warnings
    
    def _calculate_confidence_score(self, pattern: Dict) -> float:
        """Calculate confidence score for generated documentation"""
        base_score = 0.5
        
        # Higher frequency = higher confidence
        freq_score = min(pattern['frequency'] / 10.0, 0.3)
        
        # Higher success rate = higher confidence
        success_score = pattern['avg_success_rate'] * 0.4
        
        # More commands = potentially lower confidence (more complexity)
        complexity_penalty = min(len(pattern.get('sample_commands', [])) * 0.02, 0.1)
        
        return min(base_score + freq_score + success_score - complexity_penalty, 1.0)
    
    def _generate_generic_troubleshooting_guide(self, error_pattern: str, title: str) -> GeneratedDocumentation:
        """Generate generic troubleshooting guide when no specific patterns found"""
        steps = [
            CommandStep(
                step_number=1,
                command=f"# Check for {error_pattern} symptoms",
                description="Verify the error condition",
                expected_output="Error confirmed",
                risk_level="low",
                prerequisites=[],
                troubleshooting_notes=[]
            ),
            CommandStep(
                step_number=2,
                command="# Check system logs for additional information",
                description="Review logs for related errors",
                expected_output="Additional context found",
                risk_level="low", 
                prerequisites=[],
                troubleshooting_notes=[]
            )
        ]
        
        return GeneratedDocumentation(
            id=f"generic_troubleshoot_{error_pattern}",
            title=title,
            doc_type=DocumentationType.TROUBLESHOOTING_GUIDE,
            description=f"Generic troubleshooting guide for {error_pattern} issues.",
            steps=steps,
            prerequisites=[],
            warnings=["⚠️ This is a generic guide - specific patterns not found in historical data"],
            metadata={'error_pattern': error_pattern, 'generic': True},
            generated_at=datetime.now().isoformat(),
            confidence_score=0.3,
            sources=["Generic troubleshooting patterns"]
        )
    
    def format_documentation(self, doc: GeneratedDocumentation, 
                           format_type: DocumentationFormat) -> str:
        """Format documentation in specified format"""
        if format_type == DocumentationFormat.MARKDOWN:
            return self._format_as_markdown(doc)
        elif format_type == DocumentationFormat.JSON:
            return json.dumps(asdict(doc), indent=2)
        elif format_type == DocumentationFormat.HTML:
            return self._format_as_html(doc)
        elif format_type == DocumentationFormat.PLAIN_TEXT:
            return self._format_as_text(doc)
        else:
            raise ValueError(f"Unsupported format: {format_type}")
    
    def _format_as_markdown(self, doc: GeneratedDocumentation) -> str:
        """Format documentation as Markdown"""
        if doc.doc_type == DocumentationType.RUNBOOK:
            return self._format_runbook_markdown(doc)
        elif doc.doc_type == DocumentationType.TROUBLESHOOTING_GUIDE:
            return self._format_troubleshooting_markdown(doc)
        elif doc.doc_type == DocumentationType.COMMAND_REFERENCE:
            return self._format_reference_markdown(doc)
        else:
            return self._format_generic_markdown(doc)
    
    def _format_runbook_markdown(self, doc: GeneratedDocumentation) -> str:
        """Format runbook as Markdown"""
        md = f"# {doc.title}\n\n"
        md += f"## Overview\n{doc.description}\n\n"
        
        if doc.prerequisites:
            md += "## Prerequisites\n"
            for prereq in doc.prerequisites:
                md += f"- {prereq}\n"
            md += "\n"
        
        if doc.warnings:
            md += "## Warnings and Cautions\n"
            for warning in doc.warnings:
                md += f"- {warning}\n"
            md += "\n"
        
        md += "## Procedure Steps\n\n"
        for step in doc.steps:
            md += f"### Step {step.step_number}: {step.description}\n\n"
            md += f"```bash\n{step.command}\n```\n\n"
            md += f"**Expected Output**: {step.expected_output}\n\n"
            md += f"**Risk Level**: {step.risk_level.upper()}\n\n"
            
            if step.troubleshooting_notes:
                md += "**Troubleshooting Notes**:\n"
                for note in step.troubleshooting_notes:
                    md += f"- {note}\n"
                md += "\n"
        
        md += "---\n"
        md += f"*Generated by Smart Documentation Generator on {doc.generated_at}*\n"
        md += f"*Confidence Score: {doc.confidence_score:.2f}/1.0*\n"
        md += f"*Based on: {', '.join(doc.sources)}*\n"
        
        return md
    
    def _format_troubleshooting_markdown(self, doc: GeneratedDocumentation) -> str:
        """Format troubleshooting guide as Markdown"""
        md = f"# {doc.title}\n\n"
        md += f"## Problem Description\n{doc.description}\n\n"
        
        # Separate diagnostic and resolution steps
        diagnostic_steps = [s for s in doc.steps if 'diagnostic' in s.description.lower() or s.step_number <= len(doc.steps) // 2]
        resolution_steps = [s for s in doc.steps if s not in diagnostic_steps]
        
        if diagnostic_steps:
            md += "## Diagnostic Steps\n\n"
            for step in diagnostic_steps:
                md += f"### {step.step_number}. {step.description}\n\n"
                md += f"```bash\n{step.command}\n```\n\n"
        
        if resolution_steps:
            md += "## Resolution Steps\n\n"
            for step in resolution_steps:
                md += f"### {step.step_number}. {step.description}\n\n"
                md += f"```bash\n{step.command}\n```\n\n"
                if step.risk_level == 'high':
                    md += "⚠️ **High Risk Command** - Review before execution\n\n"
        
        md += "---\n"
        md += f"*Auto-generated from {len(doc.sources)} similar incidents*\n"
        md += f"*Last updated: {doc.generated_at}*\n"
        
        return md
    
    def _format_reference_markdown(self, doc: GeneratedDocumentation) -> str:
        """Format command reference as Markdown"""
        md = f"# {doc.title}\n\n"
        md += f"## Description\n{doc.description}\n\n"
        
        md += "## Usage Examples\n\n"
        for step in doc.steps:
            md += f"### {step.description}\n\n"
            md += f"```bash\n{step.command}\n```\n\n"
            md += f"**Expected Output**: {step.expected_output}\n"
            md += f"**Risk Level**: {step.risk_level.upper()}\n\n"
        
        if doc.metadata.get('success_rate'):
            md += f"## Success Rate\n"
            md += f"Historical success rate: {doc.metadata['success_rate']:.1%}\n\n"
        
        md += "---\n"
        md += f"*Generated from {doc.metadata.get('total_executions', 0)} command executions*\n"
        
        return md
    
    def _format_generic_markdown(self, doc: GeneratedDocumentation) -> str:
        """Generic Markdown formatter"""
        md = f"# {doc.title}\n\n"
        md += f"{doc.description}\n\n"
        
        if doc.steps:
            md += "## Steps\n\n"
            for step in doc.steps:
                md += f"### {step.step_number}. {step.description}\n\n"
                md += f"```bash\n{step.command}\n```\n\n"
        
        return md
    
    def _format_as_html(self, doc: GeneratedDocumentation) -> str:
        """Format documentation as HTML (basic implementation)"""
        markdown = self._format_as_markdown(doc)
        # In a real implementation, would use a proper Markdown to HTML converter
        html = markdown.replace('# ', '<h1>').replace('\n', '<br>\n')
        return f"<html><body>{html}</body></html>"
    
    def _format_as_text(self, doc: GeneratedDocumentation) -> str:
        """Format documentation as plain text"""
        text = f"{doc.title}\n{'=' * len(doc.title)}\n\n"
        text += f"{doc.description}\n\n"
        
        if doc.steps:
            text += "STEPS:\n\n"
            for step in doc.steps:
                text += f"{step.step_number}. {step.description}\n"
                text += f"   Command: {step.command}\n"
                text += f"   Expected: {step.expected_output}\n\n"
        
        return text
    
    def get_generated_documentation(self, doc_id: str) -> Optional[GeneratedDocumentation]:
        """Retrieve generated documentation by ID"""
        return self.generated_docs.get(doc_id)
    
    def list_generated_documentation(self) -> List[Dict]:
        """List all generated documentation with metadata"""
        return [
            {
                'id': doc_id,
                'title': doc.title,
                'type': doc.doc_type.value,
                'generated_at': doc.generated_at,
                'confidence_score': doc.confidence_score
            }
            for doc_id, doc in self.generated_docs.items()
        ]