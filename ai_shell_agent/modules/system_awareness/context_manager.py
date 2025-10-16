"""
System Context Manager

Manages server profiles and enhances AI prompts with system-specific context
for more accurate command generation and troubleshooting.
"""

import json
import time
from typing import Dict, List, Optional
from .server_profiler import ServerProfiler


class SystemContextManager:
    """
    Manages system context and enhances AI prompts with server-specific information.
    
    This class profiles servers, caches their information, and provides system-aware
    prompt enhancement for both command generation and troubleshooting.
    """

    def __init__(self):
        """Initialize the system context manager."""
        self.profiler = ServerProfiler()
        self.profiles = {}  # Cache of server profiles by host
        self.current_profile = None
        self.profile_cache_duration = 3600  # 1 hour cache

    def initialize_context(self, ssh_client, host_identifier: str = None, force_refresh: bool = False) -> Dict:
        """
        Initialize system context for a server connection.
        
        Args:
            ssh_client: Active SSH client connection
            host_identifier: Unique identifier for the server (IP/hostname)
            force_refresh: Whether to ignore cached profile
            
        Returns:
            Dict: Server profile information
        """
        if not host_identifier:
            # Try to get hostname from the server
            host_identifier = self.profiler._get_hostname(ssh_client)
        
        # Check for cached profile
        if (not force_refresh and 
            host_identifier in self.profiles and 
            self._is_profile_valid(self.profiles[host_identifier])):
            
            profile = self.profiles[host_identifier]
            self.current_profile = profile
            return profile
        
        # Profile the server
        profile = self.profiler.profile_server(ssh_client, force_refresh)
        profile['host_identifier'] = host_identifier
        
        # Cache the profile
        self.profiles[host_identifier] = profile
        self.current_profile = profile
        
        return profile

    def get_current_profile(self) -> Optional[Dict]:
        """Get the currently active server profile."""
        return self.current_profile

    def get_system_summary(self) -> str:
        """
        Get a human-readable summary of the current server profile.
        
        Returns:
            str: Summary of server capabilities and configuration
        """
        if not self.current_profile:
            return "No server profile available"
        
        profile = self.current_profile
        
        summary_parts = []
        
        # OS Information
        os_info = profile.get('os_info', {})
        if os_info.get('distribution') != 'unknown':
            summary_parts.append(f"OS: {os_info.get('pretty_name', os_info.get('distribution', 'Unknown'))}")
        
        # Package managers
        package_managers = profile.get('package_managers', [])
        if package_managers:
            summary_parts.append(f"Package Manager: {', '.join(package_managers)}")
        
        # Service manager
        service_manager = profile.get('service_manager', 'unknown')
        if service_manager != 'unknown':
            summary_parts.append(f"Service Manager: {service_manager}")
        
        # Key software
        software = profile.get('installed_software', {})
        software_summary = []
        for category, tools in software.items():
            if tools:
                software_summary.append(f"{category}: {', '.join(tools[:3])}")  # Show first 3
        
        if software_summary:
            summary_parts.append(f"Software: {'; '.join(software_summary)}")
        
        # Confidence
        confidence = profile.get('confidence_score', 0)
        summary_parts.append(f"Profile Confidence: {confidence:.0%}")
        
        return " | ".join(summary_parts)

    def enhance_ai_prompt(self, base_prompt: str, task_type: str, **kwargs) -> str:
        """
        Enhance AI prompt with system-specific context.
        
        Args:
            base_prompt: Original prompt template
            task_type: Type of task ('command_generation' or 'troubleshooting')
            **kwargs: Additional context like user_request, error_text, etc.
            
        Returns:
            str: Enhanced prompt with system context
        """
        if not self.current_profile:
            return base_prompt
        
        # Build system context section
        context_section = self._build_system_context_section()
        
        # Task-specific enhancements
        if task_type == 'command_generation':
            enhanced_prompt = self._enhance_command_prompt(base_prompt, context_section, **kwargs)
        elif task_type == 'troubleshooting':
            enhanced_prompt = self._enhance_troubleshooting_prompt(base_prompt, context_section, **kwargs)
        else:
            enhanced_prompt = f"{base_prompt}\n\n{context_section}"
        
        return enhanced_prompt

    def get_command_suggestions(self, category: str) -> List[str]:
        """
        Get server-specific command suggestions for a category.
        
        Args:
            category: Command category (e.g., 'package', 'service', 'network')
            
        Returns:
            List[str]: Suggested commands based on server profile
        """
        if not self.current_profile:
            return []
        
        suggestions = []
        
        if category == 'package':
            suggestions.extend(self._get_package_suggestions())
        elif category == 'service':
            suggestions.extend(self._get_service_suggestions())
        elif category == 'network':
            suggestions.extend(self._get_network_suggestions())
        elif category == 'monitoring':
            suggestions.extend(self._get_monitoring_suggestions())
        
        return suggestions

    def _is_profile_valid(self, profile: Dict) -> bool:
        """Check if a cached profile is still valid."""
        if 'timestamp' not in profile:
            return False
        
        profile_age = time.time() - profile['timestamp']
        return profile_age < self.profile_cache_duration

    def _build_system_context_section(self) -> str:
        """Build the system context section for AI prompt enhancement."""
        profile = self.current_profile
        
        context_parts = ["=== SERVER SYSTEM CONTEXT ==="]
        
        # Operating System
        os_info = profile.get('os_info', {})
        if os_info.get('distribution') != 'unknown':
            context_parts.append(f"Operating System: {os_info.get('distribution')} {os_info.get('version', '')}")
            context_parts.append(f"Kernel: {os_info.get('kernel', 'unknown')}")
        
        # Package Management
        package_managers = profile.get('package_managers', [])
        if package_managers:
            context_parts.append(f"Available Package Managers: {', '.join(package_managers)}")
            primary_pm = package_managers[0] if package_managers else 'unknown'
            context_parts.append(f"Primary Package Manager: {primary_pm}")
        
        # Service Management
        service_manager = profile.get('service_manager', 'unknown')
        context_parts.append(f"Service Manager: {service_manager}")
        
        # Installed Software
        software = profile.get('installed_software', {})
        for category, tools in software.items():
            if tools:
                context_parts.append(f"Available {category.replace('_', ' ').title()}: {', '.join(tools)}")
        
        # Security Context
        security = profile.get('security_info', {})
        if security.get('has_sudo'):
            context_parts.append("Sudo Access: Available")
        if security.get('firewall'):
            context_parts.append(f"Firewall: {security['firewall']}")
        
        # System Capabilities
        capabilities = profile.get('capabilities', [])
        if capabilities:
            context_parts.append(f"System Capabilities: {', '.join(capabilities)}")
        
        context_parts.append("=== END SYSTEM CONTEXT ===")
        
        return "\n".join(context_parts)

    def _enhance_command_prompt(self, base_prompt: str, context_section: str, **kwargs) -> str:
        """Enhance command generation prompt with system context."""
        user_request = kwargs.get('user_request', '')
        
        enhancement = f"""
{context_section}

IMPORTANT: Use the above server context to generate commands that are:
1. Compatible with the detected operating system ({self.current_profile.get('os_info', {}).get('distribution', 'unknown')})
2. Use the correct package manager ({', '.join(self.current_profile.get('package_managers', ['apt']))})
3. Use the appropriate service manager ({self.current_profile.get('service_manager', 'systemd')})
4. Leverage available software and tools listed above
5. Consider security context (sudo availability: {self.current_profile.get('security_info', {}).get('has_sudo', False)})

For the user request: "{user_request}"
Generate commands that are specifically optimized for this server configuration.
"""
        
        return f"{base_prompt}\n{enhancement}"

    def _enhance_troubleshooting_prompt(self, base_prompt: str, context_section: str, **kwargs) -> str:
        """Enhance troubleshooting prompt with system context."""
        error_text = kwargs.get('error_text', '')
        additional_context = kwargs.get('additional_context', {})
        
        enhancement = f"""
{context_section}

TROUBLESHOOTING CONTEXT:
When analyzing the error and generating diagnostic/fix commands, consider:
1. OS-specific error patterns and solutions for {self.current_profile.get('os_info', {}).get('distribution', 'unknown')}
2. Use package manager commands appropriate for this system: {', '.join(self.current_profile.get('package_managers', ['apt']))}
3. Use service management commands for {self.current_profile.get('service_manager', 'systemd')}
4. Consider available software that might be involved: {self._get_relevant_software_context()}
5. Account for security constraints (sudo: {self.current_profile.get('security_info', {}).get('has_sudo', False)})

Error to troubleshoot: "{error_text}"
Provide system-aware diagnostic and fix commands optimized for this specific server configuration.
"""
        
        return f"{base_prompt}\n{enhancement}"

    def _get_relevant_software_context(self) -> str:
        """Get relevant software context for troubleshooting."""
        software = self.current_profile.get('installed_software', {})
        relevant = []
        
        for category, tools in software.items():
            if tools:
                relevant.extend(tools[:2])  # First 2 from each category
        
        return ', '.join(relevant) if relevant else 'standard system tools'

    def _get_package_suggestions(self) -> List[str]:
        """Get package management command suggestions."""
        package_managers = self.current_profile.get('package_managers', [])
        suggestions = []
        
        if 'apt' in package_managers:
            suggestions.extend([
                'sudo apt update && sudo apt upgrade',
                'apt search <package>',
                'sudo apt install <package>',
                'sudo apt remove <package>',
                'apt list --installed'
            ])
        elif 'yum' in package_managers:
            suggestions.extend([
                'sudo yum update',
                'yum search <package>',
                'sudo yum install <package>',
                'sudo yum remove <package>',
                'yum list installed'
            ])
        elif 'apk' in package_managers:
            suggestions.extend([
                'sudo apk update && sudo apk upgrade',
                'apk search <package>',
                'sudo apk add <package>',
                'sudo apk del <package>',
                'apk info'
            ])
        
        return suggestions

    def _get_service_suggestions(self) -> List[str]:
        """Get service management command suggestions."""
        service_manager = self.current_profile.get('service_manager', 'unknown')
        
        if service_manager == 'systemd':
            return [
                'systemctl status <service>',
                'sudo systemctl start <service>',
                'sudo systemctl stop <service>',
                'sudo systemctl restart <service>',
                'sudo systemctl enable <service>',
                'systemctl list-units --type=service'
            ]
        elif service_manager == 'sysvinit':
            return [
                'service <service> status',
                'sudo service <service> start',
                'sudo service <service> stop',
                'sudo service <service> restart',
                'chkconfig --list'
            ]
        
        return ['ps aux | grep <service>', 'killall <service>']

    def _get_network_suggestions(self) -> List[str]:
        """Get network-related command suggestions."""
        return [
            'ip addr show',
            'netstat -tulpn',
            'ss -tulpn',
            'ping -c 4 <host>',
            'curl -I <url>',
            'dig <domain>'
        ]

    def _get_monitoring_suggestions(self) -> List[str]:
        """Get system monitoring command suggestions."""
        suggestions = ['top', 'ps aux', 'df -h', 'free -h', 'uptime']
        
        # Add htop if available
        software = self.current_profile.get('installed_software', {})
        if 'htop' in software.get('system_tools', []):
            suggestions.insert(0, 'htop')
        
        return suggestions