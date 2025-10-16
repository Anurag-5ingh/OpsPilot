"""
Command Fallback Analyzer

Analyzes failed command executions, determines failure reasons, and suggests
intelligent alternatives with detailed reasoning.
"""

import re
from typing import Dict, List, Optional
from enum import Enum


class FailureCategory(Enum):
    """Categories of command failures"""
    PERMISSION_DENIED = "permission_denied"
    COMMAND_NOT_FOUND = "command_not_found"
    PACKAGE_NOT_FOUND = "package_not_found"
    SERVICE_NOT_FOUND = "service_not_found"
    FILE_NOT_FOUND = "file_not_found"
    NETWORK_ERROR = "network_error"
    SYNTAX_ERROR = "syntax_error"
    DEPENDENCY_ERROR = "dependency_error"
    RESOURCE_ERROR = "resource_error"
    SYSTEM_INCOMPATIBILITY = "system_incompatibility"


class CommandFallbackAnalyzer:
    """
    Analyzes failed command executions and provides intelligent alternatives.
    
    This class examines command failures, identifies root causes, and suggests
    better alternatives with detailed reasoning and system-aware solutions.
    """

    def __init__(self):
        """Initialize the fallback analyzer with failure patterns."""
        self.failure_patterns = {
            # Permission-related failures
            FailureCategory.PERMISSION_DENIED: [
                r'permission denied',
                r'operation not permitted',
                r'access denied',
                r'insufficient privileges',
                r'must be root',
                r'sudo: .*: command not found'  # When sudo is needed but command not found as root
            ],

            # Command not found errors
            FailureCategory.COMMAND_NOT_FOUND: [
                r'command not found',
                r'no such file or directory.*(/usr/bin|/bin)',
                r'.*: not found',
                r'bash: .*: command not found',
                r'sh: .*: not found'
            ],

            # Package management failures
            FailureCategory.PACKAGE_NOT_FOUND: [
                r'package .* has no installation candidate',
                r'no package matches',
                r'package .* not found',
                r'unable to locate package',
                r'no such package',
                r'nothing provides',
                r'package .* not available'
            ],

            # Service-related failures
            FailureCategory.SERVICE_NOT_FOUND: [
                r'unit .* not found',
                r'service .* not found',
                r'no such service',
                r'unrecognized service',
                r'failed to get unit file',
                r'could not find .* service'
            ],

            # File/directory not found
            FailureCategory.FILE_NOT_FOUND: [
                r'no such file or directory',
                r'cannot stat',
                r'cannot access',
                r'file not found',
                r'directory not found'
            ],

            # Network-related failures
            FailureCategory.NETWORK_ERROR: [
                r'network is unreachable',
                r'connection refused',
                r'connection timed out',
                r'temporary failure in name resolution',
                r'could not resolve host',
                r'failed to fetch',
                r'download failed'
            ],

            # Syntax and usage errors
            FailureCategory.SYNTAX_ERROR: [
                r'invalid option',
                r'unrecognized option',
                r'bad option',
                r'illegal option',
                r'usage:',
                r'invalid argument',
                r'syntax error'
            ],

            # Dependency-related failures
            FailureCategory.DEPENDENCY_ERROR: [
                r'dependency.*not satisfied',
                r'conflicts with',
                r'depends on.*but',
                r'broken dependencies',
                r'unmet dependencies',
                r'requires.*but.*not available'
            ],

            # Resource-related failures
            FailureCategory.RESOURCE_ERROR: [
                r'no space left on device',
                r'disk full',
                r'insufficient space',
                r'out of memory',
                r'resource temporarily unavailable',
                r'too many open files'
            ],

            # System incompatibility
            FailureCategory.SYSTEM_INCOMPATIBILITY: [
                r'not supported on this system',
                r'incompatible.*architecture',
                r'wrong architecture',
                r'not available.*platform'
            ]
        }

        # Common alternative mappings
        self.command_alternatives = {
            'apt': ['apt-get', 'aptitude', 'yum', 'dnf', 'apk', 'zypper', 'pacman'],
            'yum': ['dnf', 'apt', 'apt-get', 'apk', 'zypper', 'pacman'],
            'systemctl': ['service', 'rc-service', 'initctl'],
            'service': ['systemctl', 'rc-service', 'initctl'],
            'vim': ['nano', 'emacs', 'vi'],
            'curl': ['wget', 'lynx'],
            'wget': ['curl', 'lynx'],
            'htop': ['top', 'atop', 'iotop'],
            'docker': ['podman', 'containerd', 'lxc'],
            'git': ['mercurial', 'svn', 'bzr']
        }

    def analyze_failure(self, original_command: str, error_output: str, 
                       system_context: dict = None) -> Dict:
        """
        Analyze a failed command execution and suggest alternatives.
        
        Args:
            original_command: The command that failed
            error_output: Error output/stderr from the failed command
            system_context: System context for better alternatives
            
        Returns:
            Dict containing failure analysis and alternative suggestions
        """
        analysis = {
            'original_command': original_command,
            'error_output': error_output,
            'failure_categories': [],
            'root_cause_analysis': '',
            'alternative_solutions': [],
            'system_specific_fixes': [],
            'confidence_score': 0.0,
            'requires_system_changes': False
        }

        # Identify failure categories
        identified_failures = self._identify_failure_categories(error_output)
        analysis['failure_categories'] = identified_failures

        # Generate root cause analysis
        analysis['root_cause_analysis'] = self._generate_root_cause_analysis(
            original_command, error_output, identified_failures, system_context
        )

        # Generate alternative solutions
        analysis['alternative_solutions'] = self._generate_alternative_solutions(
            original_command, identified_failures, system_context
        )

        # Add system-specific fixes
        if system_context:
            analysis['system_specific_fixes'] = self._generate_system_specific_fixes(
                original_command, identified_failures, system_context
            )

        # Calculate confidence score
        analysis['confidence_score'] = self._calculate_confidence_score(
            identified_failures, system_context
        )

        return analysis

    def _identify_failure_categories(self, error_output: str) -> List[FailureCategory]:
        """Identify categories of failure based on error output."""
        identified = []
        error_lower = error_output.lower()

        for category, patterns in self.failure_patterns.items():
            for pattern in patterns:
                if re.search(pattern, error_lower, re.IGNORECASE):
                    if category not in identified:
                        identified.append(category)
                    break

        return identified

    def _generate_root_cause_analysis(self, command: str, error: str, 
                                    failures: List[FailureCategory], 
                                    system_context: dict = None) -> str:
        """Generate detailed root cause analysis."""
        if not failures:
            return "Unable to determine the specific cause of failure from the error output."

        analysis_parts = []

        for failure in failures:
            if failure == FailureCategory.PERMISSION_DENIED:
                analysis_parts.append(
                    "The command failed due to insufficient permissions. "
                    "The user likely needs elevated privileges (sudo) or proper file permissions."
                )

            elif failure == FailureCategory.COMMAND_NOT_FOUND:
                cmd_name = self._extract_command_name(command)
                analysis_parts.append(
                    f"The command '{cmd_name}' is not installed or not available in the system PATH. "
                    f"This could be because the required package is not installed."
                )

            elif failure == FailureCategory.PACKAGE_NOT_FOUND:
                analysis_parts.append(
                    "The requested package is not available in the configured repositories. "
                    "This could be due to incorrect package name, missing repositories, or outdated package cache."
                )

            elif failure == FailureCategory.SERVICE_NOT_FOUND:
                service_name = self._extract_service_name(command)
                analysis_parts.append(
                    f"The service '{service_name}' is not installed or not recognized by the service manager. "
                    f"The service might have a different name or may not be installed."
                )

            elif failure == FailureCategory.NETWORK_ERROR:
                analysis_parts.append(
                    "The command failed due to network connectivity issues. "
                    "This could be caused by firewall restrictions, DNS problems, or network outages."
                )

            elif failure == FailureCategory.SYSTEM_INCOMPATIBILITY:
                if system_context:
                    os_info = system_context.get('os_info', {})
                    os_name = os_info.get('distribution', 'this system')
                    analysis_parts.append(
                        f"The command or package is not compatible with {os_name}. "
                        f"Different distributions may have different package names or command variations."
                    )
                else:
                    analysis_parts.append(
                        "The command or package is not compatible with the current system. "
                        "Different systems may require different approaches."
                    )

        return " ".join(analysis_parts)

    def _generate_alternative_solutions(self, command: str, failures: List[FailureCategory], 
                                      system_context: dict = None) -> List[Dict]:
        """Generate alternative command solutions based on failure analysis."""
        alternatives = []

        for failure in failures:
            if failure == FailureCategory.PERMISSION_DENIED:
                alternatives.extend(self._get_permission_alternatives(command))

            elif failure == FailureCategory.COMMAND_NOT_FOUND:
                alternatives.extend(self._get_command_alternatives(command, system_context))

            elif failure == FailureCategory.PACKAGE_NOT_FOUND:
                alternatives.extend(self._get_package_alternatives(command, system_context))

            elif failure == FailureCategory.SERVICE_NOT_FOUND:
                alternatives.extend(self._get_service_alternatives(command, system_context))

            elif failure == FailureCategory.NETWORK_ERROR:
                alternatives.extend(self._get_network_alternatives(command))

        # Remove duplicates based on alternative command
        seen_commands = set()
        unique_alternatives = []
        for alt in alternatives:
            if alt['alternative_command'] not in seen_commands:
                unique_alternatives.append(alt)
                seen_commands.add(alt['alternative_command'])

        return unique_alternatives[:5]  # Limit to top 5 alternatives

    def _get_permission_alternatives(self, command: str) -> List[Dict]:
        """Generate alternatives for permission-denied failures."""
        alternatives = []

        if not command.strip().startswith('sudo'):
            alternatives.append({
                'alternative_command': f'sudo {command}',
                'reasoning': 'Add sudo to execute with administrative privileges',
                'success_probability': 0.8,
                'side_effects': ['Requires admin password', 'Executes with root privileges']
            })

        # Check if it's a file permission issue
        if any(op in command for op in ['chmod', 'chown', 'mkdir', 'touch', 'rm']):
            alternatives.append({
                'alternative_command': f'ls -la $(dirname {self._extract_file_path(command)})',
                'reasoning': 'Check file/directory permissions before proceeding',
                'success_probability': 0.9,
                'side_effects': ['Read-only operation', 'Shows permission details']
            })

        return alternatives

    def _get_command_alternatives(self, command: str, system_context: dict = None) -> List[Dict]:
        """Generate alternatives for command-not-found failures."""
        alternatives = []
        cmd_name = self._extract_command_name(command)

        # Check for known alternatives
        if cmd_name in self.command_alternatives:
            for alt_cmd in self.command_alternatives[cmd_name]:
                # Check if alternative is available on system
                if system_context and self._is_command_available(alt_cmd, system_context):
                    alternatives.append({
                        'alternative_command': command.replace(cmd_name, alt_cmd, 1),
                        'reasoning': f'Use {alt_cmd} instead of {cmd_name} (available on this system)',
                        'success_probability': 0.7,
                        'side_effects': [f'Different syntax from {cmd_name}', 'May have different options']
                    })

        # Suggest installation
        if system_context:
            install_cmd = self._get_install_command(cmd_name, system_context)
            if install_cmd:
                alternatives.append({
                    'alternative_command': install_cmd,
                    'reasoning': f'Install {cmd_name} package first',
                    'success_probability': 0.8,
                    'side_effects': ['Downloads and installs package', 'Requires internet connection']
                })

        return alternatives

    def _get_package_alternatives(self, command: str, system_context: dict = None) -> List[Dict]:
        """Generate alternatives for package-not-found failures."""
        alternatives = []
        package_name = self._extract_package_name(command)

        # Suggest updating package cache
        if system_context:
            update_cmd = self._get_update_command(system_context)
            if update_cmd:
                alternatives.append({
                    'alternative_command': f'{update_cmd} && {command}',
                    'reasoning': 'Update package cache and retry installation',
                    'success_probability': 0.6,
                    'side_effects': ['Downloads latest package lists', 'May take time']
                })

        # Suggest searching for similar packages
        if system_context:
            search_cmd = self._get_search_command(package_name, system_context)
            if search_cmd:
                alternatives.append({
                    'alternative_command': search_cmd,
                    'reasoning': f'Search for packages similar to "{package_name}"',
                    'success_probability': 0.8,
                    'side_effects': ['Shows available packages', 'Read-only operation']
                })

        return alternatives

    def _get_service_alternatives(self, command: str, system_context: dict = None) -> List[Dict]:
        """Generate alternatives for service-not-found failures."""
        alternatives = []
        service_name = self._extract_service_name(command)

        # Try different service managers
        if system_context:
            service_manager = system_context.get('service_manager', 'unknown')
            
            if 'systemctl' in command and service_manager != 'systemd':
                alternatives.append({
                    'alternative_command': command.replace('systemctl', 'service').replace(' start ', ' ').replace(' stop ', ' ').replace(' restart ', ' '),
                    'reasoning': 'Use traditional service command instead of systemctl',
                    'success_probability': 0.7,
                    'side_effects': ['Different syntax', 'May not support all systemctl features']
                })

        # Suggest listing available services
        alternatives.append({
            'alternative_command': 'systemctl list-unit-files --type=service | grep -i ' + service_name,
            'reasoning': f'Search for services containing "{service_name}"',
            'success_probability': 0.8,
            'side_effects': ['Shows available services', 'Read-only operation']
        })

        return alternatives

    def _get_network_alternatives(self, command: str) -> List[Dict]:
        """Generate alternatives for network-related failures."""
        alternatives = []

        # Test connectivity first
        alternatives.append({
            'alternative_command': 'ping -c 3 8.8.8.8',
            'reasoning': 'Test basic internet connectivity',
            'success_probability': 0.9,
            'side_effects': ['Network test only', 'Shows connectivity status']
        })

        # Try alternative tools
        if 'curl' in command:
            alternatives.append({
                'alternative_command': command.replace('curl', 'wget'),
                'reasoning': 'Use wget instead of curl for downloading',
                'success_probability': 0.6,
                'side_effects': ['Different command syntax', 'May have different options']
            })

        return alternatives

    def _generate_system_specific_fixes(self, command: str, failures: List[FailureCategory], 
                                      system_context: dict) -> List[Dict]:
        """Generate system-specific fixes based on context."""
        fixes = []
        
        os_info = system_context.get('os_info', {})
        os_distribution = os_info.get('distribution', '').lower()
        package_managers = system_context.get('package_managers', [])

        # Distribution-specific package fixes
        if FailureCategory.PACKAGE_NOT_FOUND in failures:
            package_name = self._extract_package_name(command)
            
            if 'ubuntu' in os_distribution or 'debian' in os_distribution:
                fixes.append({
                    'fix_type': 'distribution_specific',
                    'commands': [f'apt search {package_name}', f'apt-cache policy {package_name}'],
                    'explanation': 'Search for the package in Ubuntu/Debian repositories',
                    'why_this_works': 'Different distributions may have different package names'
                })
            
            elif 'centos' in os_distribution or 'rhel' in os_distribution:
                fixes.append({
                    'fix_type': 'distribution_specific', 
                    'commands': [f'yum search {package_name}', f'dnf search {package_name}'],
                    'explanation': 'Search for the package in CentOS/RHEL repositories',
                    'why_this_works': 'Red Hat systems use different package names than Debian systems'
                })

        return fixes

    def _calculate_confidence_score(self, failures: List[FailureCategory], 
                                  system_context: dict = None) -> float:
        """Calculate confidence score for the analysis."""
        base_score = 0.5
        
        # Higher confidence if we identified specific failure categories
        if failures:
            base_score += 0.3
        
        # Higher confidence if we have system context
        if system_context:
            base_score += 0.2
        
        # Adjust based on number of identified failures
        if len(failures) == 1:
            base_score += 0.1  # More confident with single clear failure
        elif len(failures) > 3:
            base_score -= 0.1  # Less confident with many failure types
        
        return min(base_score, 1.0)

    def _extract_command_name(self, command: str) -> str:
        """Extract the main command name from a command string."""
        # Remove sudo if present
        cmd = command.strip()
        if cmd.startswith('sudo '):
            cmd = cmd[5:].strip()
        
        # Get first word (command name)
        return cmd.split()[0] if cmd.split() else ''

    def _extract_package_name(self, command: str) -> str:
        """Extract package name from installation commands."""
        parts = command.split()
        for i, part in enumerate(parts):
            if part in ['install', 'add', 'get'] and i + 1 < len(parts):
                return parts[i + 1]
        return ''

    def _extract_service_name(self, command: str) -> str:
        """Extract service name from service management commands."""
        parts = command.split()
        for i, part in enumerate(parts):
            if part in ['start', 'stop', 'restart', 'enable', 'disable', 'status'] and i + 1 < len(parts):
                return parts[i + 1]
        return ''

    def _extract_file_path(self, command: str) -> str:
        """Extract file path from command."""
        parts = command.split()
        for part in parts:
            if '/' in part:
                return part
        return '.'

    def _is_command_available(self, command: str, system_context: dict) -> bool:
        """Check if a command is available on the system."""
        # This would need to be enhanced with actual system checking
        # For now, return True as placeholder
        return True

    def _get_install_command(self, package: str, system_context: dict) -> Optional[str]:
        """Get appropriate install command for the system."""
        package_managers = system_context.get('package_managers', [])
        
        if 'apt' in package_managers:
            return f'sudo apt install {package}'
        elif 'yum' in package_managers:
            return f'sudo yum install {package}'
        elif 'dnf' in package_managers:
            return f'sudo dnf install {package}'
        elif 'apk' in package_managers:
            return f'sudo apk add {package}'
        
        return None

    def _get_update_command(self, system_context: dict) -> Optional[str]:
        """Get appropriate update command for the system."""
        package_managers = system_context.get('package_managers', [])
        
        if 'apt' in package_managers:
            return 'sudo apt update'
        elif 'yum' in package_managers:
            return 'sudo yum check-update'
        elif 'dnf' in package_managers:
            return 'sudo dnf check-update'
        elif 'apk' in package_managers:
            return 'sudo apk update'
        
        return None

    def _get_search_command(self, package: str, system_context: dict) -> Optional[str]:
        """Get appropriate search command for the system."""
        package_managers = system_context.get('package_managers', [])
        
        if 'apt' in package_managers:
            return f'apt search {package}'
        elif 'yum' in package_managers:
            return f'yum search {package}'
        elif 'dnf' in package_managers:
            return f'dnf search {package}'
        elif 'apk' in package_managers:
            return f'apk search {package}'
        
        return None