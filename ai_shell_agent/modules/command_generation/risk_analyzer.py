"""
Command Risk Analyzer

Analyzes shell commands for potential risks, side effects, and system impacts.
Provides detailed warnings and safety assessments for command execution.
"""

import re
from typing import Dict, List, Tuple
from enum import Enum


class RiskLevel(Enum):
    """Risk levels for command execution"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskCategory(Enum):
    """Categories of risks for commands"""
    DESTRUCTIVE = "destructive"
    SYSTEM_MODIFICATION = "system_modification"
    SECURITY = "security"
    NETWORK = "network"
    PERMISSION = "permission"
    SERVICE = "service"
    PACKAGE = "package"
    FILE_OPERATION = "file_operation"


class CommandRiskAnalyzer:
    """
    Analyzes shell commands for potential risks and side effects.
    
    This class identifies dangerous patterns, system modifications, and potential
    impacts of executing shell commands, providing detailed risk assessments.
    """

    def __init__(self):
        """Initialize the command risk analyzer with risk patterns."""
        self.risk_patterns = {
            # CRITICAL RISKS - Commands that can cause severe damage
            RiskLevel.CRITICAL: [
                {
                    'pattern': r'\brm\s+.*-r.*/',
                    'category': RiskCategory.DESTRUCTIVE,
                    'description': 'Recursive deletion of directories',
                    'impacts': ['Permanent data loss', 'System files deletion', 'Unrecoverable damage'],
                    'affected_areas': ['File system', 'User data', 'System configuration']
                },
                {
                    'pattern': r'\bdd\s+.*of=/dev/',
                    'category': RiskCategory.DESTRUCTIVE,
                    'description': 'Direct disk writing operations',
                    'impacts': ['Disk corruption', 'Boot failure', 'Complete data loss'],
                    'affected_areas': ['Entire disk/partition', 'Boot system', 'All stored data']
                },
                {
                    'pattern': r'\bmkfs\.',
                    'category': RiskCategory.DESTRUCTIVE,
                    'description': 'File system formatting',
                    'impacts': ['Complete partition wipe', 'All data destruction', 'System unusable'],
                    'affected_areas': ['Target partition', 'All files on partition', 'Mounted filesystems']
                },
                {
                    'pattern': r':\(\)\{.*;\}\s*;',
                    'category': RiskCategory.DESTRUCTIVE,
                    'description': 'Fork bomb or system DoS',
                    'impacts': ['System freeze', 'Resource exhaustion', 'Service disruption'],
                    'affected_areas': ['System memory', 'CPU resources', 'All running processes']
                },
            ],

            # HIGH RISKS - Commands with significant system impact
            RiskLevel.HIGH: [
                {
                    'pattern': r'\bchmod\s+777',
                    'category': RiskCategory.SECURITY,
                    'description': 'Setting dangerous file permissions',
                    'impacts': ['Security vulnerability', 'Unauthorized access', 'Data exposure'],
                    'affected_areas': ['Target files/directories', 'System security', 'Access controls']
                },
                {
                    'pattern': r'\biptables\s+.*-F',
                    'category': RiskCategory.SECURITY,
                    'description': 'Firewall rule deletion',
                    'impacts': ['Security exposure', 'Network vulnerability', 'Unauthorized access'],
                    'affected_areas': ['Network security', 'Firewall rules', 'System exposure']
                },
                {
                    'pattern': r'\bsudo\s+.*passwd',
                    'category': RiskCategory.SECURITY,
                    'description': 'Password modification',
                    'impacts': ['Account lockout', 'Access loss', 'Security compromise'],
                    'affected_areas': ['User accounts', 'System access', 'Authentication']
                },
                {
                    'pattern': r'\buseradd.*-u\s+0',
                    'category': RiskCategory.SECURITY,
                    'description': 'Creating root-level user',
                    'impacts': ['Privilege escalation', 'Security risk', 'Unauthorized admin access'],
                    'affected_areas': ['User management', 'System security', 'Administrative privileges']
                },
                {
                    'pattern': r'\bkillall\s+-9',
                    'category': RiskCategory.SERVICE,
                    'description': 'Force killing all processes',
                    'impacts': ['Data loss', 'Service interruption', 'System instability'],
                    'affected_areas': ['Running processes', 'System services', 'Unsaved data']
                },
            ],

            # MEDIUM RISKS - Commands with moderate impact
            RiskLevel.MEDIUM: [
                {
                    'pattern': r'\bapt\s+.*autoremove',
                    'category': RiskCategory.PACKAGE,
                    'description': 'Automatic package removal',
                    'impacts': ['Dependency removal', 'Software malfunction', 'System instability'],
                    'affected_areas': ['Installed packages', 'Software dependencies', 'System functionality']
                },
                {
                    'pattern': r'\bsystemctl\s+.*disable',
                    'category': RiskCategory.SERVICE,
                    'description': 'Service disabling',
                    'impacts': ['Service unavailability', 'Boot process changes', 'Functionality loss'],
                    'affected_areas': ['System services', 'Boot sequence', 'Service dependencies']
                },
                {
                    'pattern': r'\biptables\s+.*-A.*DROP',
                    'category': RiskCategory.NETWORK,
                    'description': 'Network traffic blocking',
                    'impacts': ['Network connectivity loss', 'Service inaccessibility', 'Communication failure'],
                    'affected_areas': ['Network connections', 'External services', 'Remote access']
                },
                {
                    'pattern': r'\bcp\s+.*-r.*/',
                    'category': RiskCategory.FILE_OPERATION,
                    'description': 'Recursive file copying',
                    'impacts': ['Disk space consumption', 'File conflicts', 'System slowdown'],
                    'affected_areas': ['File system space', 'Target directories', 'System performance']
                },
                {
                    'pattern': r'\bfind\s+/.*-exec.*rm',
                    'category': RiskCategory.DESTRUCTIVE,
                    'description': 'Mass file deletion',
                    'impacts': ['Multiple file deletion', 'Data loss risk', 'System file removal'],
                    'affected_areas': ['Search path directories', 'Matched files', 'System stability']
                },
            ],

            # LOW RISKS - Commands with minimal but notable impact
            RiskLevel.LOW: [
                {
                    'pattern': r'\bapt\s+.*install',
                    'category': RiskCategory.PACKAGE,
                    'description': 'Package installation',
                    'impacts': ['Disk space usage', 'New dependencies', 'Configuration changes'],
                    'affected_areas': ['Package repository', 'System packages', 'Disk space']
                },
                {
                    'pattern': r'\bsystemctl\s+.*restart',
                    'category': RiskCategory.SERVICE,
                    'description': 'Service restart',
                    'impacts': ['Temporary service downtime', 'Connection interruption', 'Process restart'],
                    'affected_areas': ['Target service', 'Active connections', 'Service dependencies']
                },
                {
                    'pattern': r'\bchown\s+.*:',
                    'category': RiskCategory.PERMISSION,
                    'description': 'File ownership change',
                    'impacts': ['Access permission changes', 'User access modification', 'File security alteration'],
                    'affected_areas': ['Target files/directories', 'User permissions', 'File access']
                },
            ]
        }

        # Additional pattern checks for comprehensive analysis
        self.sudo_patterns = [r'\bsudo\s+', r'\bsu\s+-']
        self.network_patterns = [r'\bcurl\s+', r'\bwget\s+', r'\bssh\s+', r'\bscp\s+']
        self.system_paths = [r'/etc/', r'/var/', r'/usr/', r'/sys/', r'/proc/']

    def analyze_command(self, command: str, system_context: dict = None) -> Dict:
        """
        Analyze a shell command for risks and potential impacts.
        
        Args:
            command: Shell command to analyze
            system_context: Optional system context for enhanced analysis
            
        Returns:
            Dict containing risk analysis results
        """
        analysis = {
            'command': command,
            'risk_level': RiskLevel.LOW,
            'risks_found': [],
            'requires_confirmation': False,
            'warning_message': '',
            'detailed_impacts': [],
            'affected_areas': [],
            'safety_recommendations': [],
            'alternative_suggestions': []
        }

        # Find all matching risk patterns
        risks_found = []
        max_risk_level = RiskLevel.LOW

        for risk_level, patterns in self.risk_patterns.items():
            for pattern_info in patterns:
                if re.search(pattern_info['pattern'], command, re.IGNORECASE):
                    risks_found.append({
                        'level': risk_level,
                        'category': pattern_info['category'],
                        'description': pattern_info['description'],
                        'impacts': pattern_info['impacts'],
                        'affected_areas': pattern_info['affected_areas']
                    })
                    
                    # Update maximum risk level
                    if self._compare_risk_levels(risk_level, max_risk_level) > 0:
                        max_risk_level = risk_level

        analysis['risk_level'] = max_risk_level
        analysis['risks_found'] = risks_found

        # Determine if confirmation is required
        analysis['requires_confirmation'] = max_risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]

        # Generate warning message and recommendations
        if risks_found:
            analysis.update(self._generate_warning_details(risks_found, system_context))

        # Add context-specific analysis
        if system_context:
            analysis.update(self._enhance_with_system_context(command, analysis, system_context))

        return analysis

    def _compare_risk_levels(self, level1: RiskLevel, level2: RiskLevel) -> int:
        """Compare two risk levels, returning 1 if level1 > level2, -1 if level1 < level2, 0 if equal."""
        risk_order = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        return (risk_order.index(level1) > risk_order.index(level2)) - (risk_order.index(level1) < risk_order.index(level2))

    def _generate_warning_details(self, risks_found: List[Dict], system_context: dict = None) -> Dict:
        """Generate detailed warning information based on found risks."""
        details = {
            'warning_message': '',
            'detailed_impacts': [],
            'affected_areas': set(),
            'safety_recommendations': []
        }

        # Collect all impacts and affected areas
        all_impacts = []
        for risk in risks_found:
            all_impacts.extend(risk['impacts'])
            details['affected_areas'].update(risk['affected_areas'])

        details['detailed_impacts'] = list(set(all_impacts))  # Remove duplicates
        details['affected_areas'] = list(details['affected_areas'])

        # Generate main warning message
        if any(risk['level'] == RiskLevel.CRITICAL for risk in risks_found):
            details['warning_message'] = "⚠️ CRITICAL WARNING: This command can cause severe, irreversible damage to your system!"
        elif any(risk['level'] == RiskLevel.HIGH for risk in risks_found):
            details['warning_message'] = "⚠️ HIGH RISK: This command will make significant system changes that could impact security or stability."
        elif any(risk['level'] == RiskLevel.MEDIUM for risk in risks_found):
            details['warning_message'] = "⚠️ CAUTION: This command will modify system components and may have unintended side effects."

        # Generate safety recommendations
        details['safety_recommendations'] = self._generate_safety_recommendations(risks_found)

        return details

    def _generate_safety_recommendations(self, risks_found: List[Dict]) -> List[str]:
        """Generate safety recommendations based on identified risks."""
        recommendations = []

        risk_categories = set(risk['category'] for risk in risks_found)

        if RiskCategory.DESTRUCTIVE in risk_categories:
            recommendations.extend([
                "Create a backup before proceeding",
                "Test the command in a non-production environment first",
                "Consider using safer alternatives if available"
            ])

        if RiskCategory.SECURITY in risk_categories:
            recommendations.extend([
                "Review security implications before execution",
                "Ensure you understand the permission changes",
                "Consider if this creates security vulnerabilities"
            ])

        if RiskCategory.SERVICE in risk_categories:
            recommendations.extend([
                "Check service dependencies before modification",
                "Plan for potential service downtime",
                "Have a rollback plan ready"
            ])

        if RiskCategory.PACKAGE in risk_categories:
            recommendations.extend([
                "Review package dependencies",
                "Check available disk space",
                "Consider using package manager's dry-run option first"
            ])

        # Add general recommendations for high-risk commands
        if any(risk['level'] in [RiskLevel.HIGH, RiskLevel.CRITICAL] for risk in risks_found):
            recommendations.extend([
                "Double-check the command syntax",
                "Ensure you have necessary privileges",
                "Consider the impact on running services"
            ])

        return list(set(recommendations))  # Remove duplicates

    def _enhance_with_system_context(self, command: str, analysis: Dict, system_context: dict) -> Dict:
        """Enhance risk analysis with system-specific context."""
        enhancements = {}

        # Check if command uses system-appropriate tools
        os_info = system_context.get('os_info', {})
        package_managers = system_context.get('package_managers', [])
        service_manager = system_context.get('service_manager', 'unknown')

        # Add system-specific warnings
        additional_warnings = []

        # Package manager context
        if 'apt' in command and 'apt' not in package_managers:
            additional_warnings.append("This command uses 'apt' but it may not be available on this system")

        if 'yum' in command and 'yum' not in package_managers:
            additional_warnings.append("This command uses 'yum' but it may not be available on this system")

        # Service manager context
        if 'systemctl' in command and service_manager != 'systemd':
            additional_warnings.append("This command uses 'systemctl' but systemd may not be available")

        if additional_warnings:
            enhancements['system_compatibility_warnings'] = additional_warnings

        return enhancements

    def generate_safer_alternatives(self, command: str, risks_found: List[Dict], system_context: dict = None) -> List[Dict]:
        """
        Generate safer alternative commands based on identified risks.
        
        Args:
            command: Original risky command
            risks_found: List of identified risks
            system_context: System context for better alternatives
            
        Returns:
            List of alternative command suggestions with explanations
        """
        alternatives = []

        for risk in risks_found:
            if risk['category'] == RiskCategory.DESTRUCTIVE:
                if 'rm' in command and '-r' in command:
                    alternatives.append({
                        'alternative': command.replace('rm ', 'rm -i '),
                        'explanation': 'Add interactive mode to confirm each deletion',
                        'safety_improvement': 'Prevents accidental deletion by asking for confirmation'
                    })
                    alternatives.append({
                        'alternative': f"ls -la {self._extract_target_path(command)} # Review first, then proceed",
                        'explanation': 'List directory contents before deletion',
                        'safety_improvement': 'Allows verification of what will be deleted'
                    })

            elif risk['category'] == RiskCategory.SECURITY:
                if 'chmod 777' in command:
                    alternatives.append({
                        'alternative': command.replace('777', '755'),
                        'explanation': 'Use more restrictive permissions (755 instead of 777)',
                        'safety_improvement': 'Maintains security while providing necessary access'
                    })

            elif risk['category'] == RiskCategory.SERVICE:
                if 'killall -9' in command:
                    service_name = self._extract_service_name(command)
                    alternatives.append({
                        'alternative': f'systemctl stop {service_name}',
                        'explanation': 'Use proper service management instead of force killing',
                        'safety_improvement': 'Allows graceful shutdown and proper cleanup'
                    })

        return alternatives

    def _extract_target_path(self, command: str) -> str:
        """Extract target path from command for safer alternatives."""
        # Simple extraction - can be enhanced
        parts = command.split()
        for i, part in enumerate(parts):
            if part.startswith('/') or part.startswith('./'):
                return part
        return "TARGET_PATH"

    def _extract_service_name(self, command: str) -> str:
        """Extract service name from killall command."""
        parts = command.split()
        for i, part in enumerate(parts):
            if part == 'killall' and i + 1 < len(parts):
                return parts[i + 2] if parts[i + 1] == '-9' else parts[i + 1]
        return "SERVICE_NAME"