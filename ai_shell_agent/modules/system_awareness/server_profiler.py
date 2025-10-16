"""
Server Profiler

Discovers and profiles remote servers to understand their capabilities,
operating system, installed software, and configuration.
"""

import json
import time
from typing import Dict, List, Optional, Tuple


class ServerProfiler:
    """
    Profiles remote servers via SSH to gather system information
    for context-aware command generation and troubleshooting.
    """

    def __init__(self):
        """Initialize the server profiler."""
        self.discovery_commands = {
            # Operating System Detection
            'os_info': [
                'uname -a',
                'cat /etc/os-release 2>/dev/null || cat /etc/redhat-release 2>/dev/null || cat /etc/debian_version 2>/dev/null',
                'lsb_release -a 2>/dev/null',
            ],
            
            # Package Manager Detection
            'package_managers': [
                'which apt apt-get 2>/dev/null',
                'which yum dnf 2>/dev/null', 
                'which apk 2>/dev/null',
                'which zypper 2>/dev/null',
                'which pacman 2>/dev/null',
                'which brew 2>/dev/null',
            ],
            
            # Service Manager Detection
            'service_managers': [
                'which systemctl 2>/dev/null && echo "systemd"',
                'which service 2>/dev/null && echo "sysvinit"', 
                'which rc-service 2>/dev/null && echo "openrc"',
                'ps 1 | grep -q systemd && echo "systemd" || echo "other"',
            ],
            
            # System Resources
            'system_resources': [
                'free -h 2>/dev/null',
                'df -h 2>/dev/null', 
                'nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null',
                'uptime',
            ],
            
            # Network Configuration
            'network_info': [
                'ip addr show 2>/dev/null || ifconfig 2>/dev/null',
                'hostname -I 2>/dev/null || hostname',
                'cat /etc/resolv.conf 2>/dev/null | grep nameserver',
            ],
            
            # Common Software Detection
            'installed_software': [
                'which docker 2>/dev/null',
                'which nginx apache2 httpd 2>/dev/null',
                'which mysql mysqld postgresql postgres 2>/dev/null',
                'which python python3 node npm java 2>/dev/null',
                'which git curl wget 2>/dev/null',
            ],
            
            # Security and Authentication
            'security_info': [
                'which sudo 2>/dev/null',
                'id',
                'ls -la /etc/sudoers.d/ 2>/dev/null | wc -l',
                'which firewall-cmd ufw iptables 2>/dev/null',
            ]
        }

    def profile_server(self, ssh_client, force_refresh: bool = False) -> Dict:
        """
        Profile a server comprehensively via SSH connection.
        
        Args:
            ssh_client: Active SSH client connection
            force_refresh: Whether to ignore cached results
            
        Returns:
            Dict: Comprehensive server profile with OS, software, and capabilities
        """
        profile = {
            'timestamp': time.time(),
            'hostname': self._get_hostname(ssh_client),
            'os_info': {},
            'package_managers': [],
            'service_manager': 'unknown',
            'system_resources': {},
            'network_info': {},
            'installed_software': {},
            'security_info': {},
            'capabilities': [],
            'confidence_score': 0.0
        }
        
        try:
            # Gather all system information
            profile['os_info'] = self._detect_os_info(ssh_client)
            profile['package_managers'] = self._detect_package_managers(ssh_client)
            profile['service_manager'] = self._detect_service_manager(ssh_client)
            profile['system_resources'] = self._get_system_resources(ssh_client)
            profile['network_info'] = self._get_network_info(ssh_client)
            profile['installed_software'] = self._detect_installed_software(ssh_client)
            profile['security_info'] = self._get_security_info(ssh_client)
            
            # Determine server capabilities based on discovered information
            profile['capabilities'] = self._determine_capabilities(profile)
            
            # Calculate confidence score based on successful detections
            profile['confidence_score'] = self._calculate_confidence_score(profile)
            
        except Exception as e:
            profile['error'] = f"Profiling failed: {str(e)}"
            profile['confidence_score'] = 0.0
            
        return profile

    def _execute_command_safe(self, ssh_client, command: str) -> Tuple[str, str]:
        """
        Execute command safely with timeout and error handling.
        
        Args:
            ssh_client: SSH client connection
            command: Command to execute
            
        Returns:
            Tuple of (stdout, stderr)
        """
        try:
            stdin, stdout, stderr = ssh_client.exec_command(command, timeout=10)
            stdout_data = stdout.read().decode('utf-8', errors='ignore').strip()
            stderr_data = stderr.read().decode('utf-8', errors='ignore').strip()
            return stdout_data, stderr_data
        except Exception as e:
            return "", str(e)

    def _get_hostname(self, ssh_client) -> str:
        """Get server hostname."""
        stdout, _ = self._execute_command_safe(ssh_client, 'hostname')
        return stdout.strip() if stdout else 'unknown'

    def _detect_os_info(self, ssh_client) -> Dict:
        """Detect operating system information."""
        os_info = {
            'distribution': 'unknown',
            'version': 'unknown',
            'kernel': 'unknown',
            'architecture': 'unknown'
        }
        
        # Get kernel and architecture info
        stdout, _ = self._execute_command_safe(ssh_client, 'uname -a')
        if stdout:
            parts = stdout.split()
            if len(parts) >= 3:
                os_info['kernel'] = f"{parts[0]} {parts[2]}"
            if len(parts) >= 12:
                os_info['architecture'] = parts[-2]
        
        # Get distribution info from /etc/os-release
        stdout, _ = self._execute_command_safe(ssh_client, 'cat /etc/os-release 2>/dev/null')
        if stdout:
            for line in stdout.split('\n'):
                if line.startswith('ID='):
                    os_info['distribution'] = line.split('=')[1].strip('"')
                elif line.startswith('VERSION_ID='):
                    os_info['version'] = line.split('=')[1].strip('"')
                elif line.startswith('PRETTY_NAME='):
                    os_info['pretty_name'] = line.split('=')[1].strip('"')
        
        return os_info

    def _detect_package_managers(self, ssh_client) -> List[str]:
        """Detect available package managers."""
        package_managers = []
        
        managers = {
            'apt': 'apt --version 2>/dev/null',
            'yum': 'yum --version 2>/dev/null',
            'dnf': 'dnf --version 2>/dev/null', 
            'apk': 'apk --version 2>/dev/null',
            'zypper': 'zypper --version 2>/dev/null',
            'pacman': 'pacman --version 2>/dev/null',
            'brew': 'brew --version 2>/dev/null'
        }
        
        for manager, command in managers.items():
            stdout, _ = self._execute_command_safe(ssh_client, command)
            if stdout and 'not found' not in stdout.lower():
                package_managers.append(manager)
        
        return package_managers

    def _detect_service_manager(self, ssh_client) -> str:
        """Detect the service management system."""
        # Check for systemd
        stdout, _ = self._execute_command_safe(ssh_client, 'systemctl --version 2>/dev/null')
        if stdout and 'systemd' in stdout.lower():
            return 'systemd'
        
        # Check for SysV init
        stdout, _ = self._execute_command_safe(ssh_client, 'which service 2>/dev/null')
        if stdout:
            return 'sysvinit'
        
        # Check for OpenRC
        stdout, _ = self._execute_command_safe(ssh_client, 'which rc-service 2>/dev/null')
        if stdout:
            return 'openrc'
        
        return 'unknown'

    def _get_system_resources(self, ssh_client) -> Dict:
        """Get system resource information."""
        resources = {}
        
        # Memory info
        stdout, _ = self._execute_command_safe(ssh_client, 'free -h 2>/dev/null')
        if stdout:
            resources['memory'] = stdout
        
        # Disk info
        stdout, _ = self._execute_command_safe(ssh_client, 'df -h 2>/dev/null')
        if stdout:
            resources['disk'] = stdout
            
        # CPU info
        stdout, _ = self._execute_command_safe(ssh_client, 'nproc 2>/dev/null')
        if stdout:
            resources['cpu_cores'] = stdout.strip()
        
        # Load average
        stdout, _ = self._execute_command_safe(ssh_client, 'uptime')
        if stdout:
            resources['uptime'] = stdout
            
        return resources

    def _get_network_info(self, ssh_client) -> Dict:
        """Get network configuration information."""
        network = {}
        
        # IP addresses
        stdout, _ = self._execute_command_safe(ssh_client, 'hostname -I 2>/dev/null')
        if stdout:
            network['ip_addresses'] = stdout.strip().split()
        
        # Hostname
        stdout, _ = self._execute_command_safe(ssh_client, 'hostname 2>/dev/null')
        if stdout:
            network['hostname'] = stdout.strip()
        
        return network

    def _detect_installed_software(self, ssh_client) -> Dict:
        """Detect commonly used software and tools."""
        software = {
            'containers': [],
            'web_servers': [],
            'databases': [],
            'development': [],
            'system_tools': []
        }
        
        # Container technologies
        for tool in ['docker', 'podman', 'lxc']:
            stdout, _ = self._execute_command_safe(ssh_client, f'which {tool} 2>/dev/null')
            if stdout:
                software['containers'].append(tool)
        
        # Web servers
        for server in ['nginx', 'apache2', 'httpd']:
            stdout, _ = self._execute_command_safe(ssh_client, f'which {server} 2>/dev/null')
            if stdout:
                software['web_servers'].append(server)
        
        # Databases
        for db in ['mysql', 'mysqld', 'postgresql', 'postgres', 'redis-server', 'mongod']:
            stdout, _ = self._execute_command_safe(ssh_client, f'which {db} 2>/dev/null')
            if stdout:
                software['databases'].append(db)
        
        # Development tools
        for tool in ['python', 'python3', 'node', 'npm', 'java', 'go', 'php']:
            stdout, _ = self._execute_command_safe(ssh_client, f'which {tool} 2>/dev/null')
            if stdout:
                software['development'].append(tool)
                
        # System tools
        for tool in ['git', 'curl', 'wget', 'vim', 'nano', 'htop']:
            stdout, _ = self._execute_command_safe(ssh_client, f'which {tool} 2>/dev/null')
            if stdout:
                software['system_tools'].append(tool)
        
        return software

    def _get_security_info(self, ssh_client) -> Dict:
        """Get security and permission information."""
        security = {}
        
        # User info
        stdout, _ = self._execute_command_safe(ssh_client, 'id')
        if stdout:
            security['user_info'] = stdout
        
        # Sudo availability
        stdout, _ = self._execute_command_safe(ssh_client, 'which sudo 2>/dev/null')
        security['has_sudo'] = bool(stdout)
        
        # Firewall detection
        for fw in ['firewall-cmd', 'ufw', 'iptables']:
            stdout, _ = self._execute_command_safe(ssh_client, f'which {fw} 2>/dev/null')
            if stdout:
                security['firewall'] = fw
                break
        
        return security

    def _determine_capabilities(self, profile: Dict) -> List[str]:
        """Determine server capabilities based on profile."""
        capabilities = []
        
        # OS-based capabilities
        os_dist = profile['os_info'].get('distribution', '').lower()
        if 'ubuntu' in os_dist or 'debian' in os_dist:
            capabilities.extend(['apt-package-management', 'systemd-services'])
        elif 'centos' in os_dist or 'rhel' in os_dist or 'fedora' in os_dist:
            capabilities.extend(['yum-package-management', 'systemd-services'])
        elif 'alpine' in os_dist:
            capabilities.extend(['apk-package-management', 'openrc-services'])
        
        # Software-based capabilities
        if profile['installed_software'].get('containers'):
            capabilities.append('container-management')
        if profile['installed_software'].get('web_servers'):
            capabilities.append('web-server-management')
        if profile['installed_software'].get('databases'):
            capabilities.append('database-management')
        if profile['installed_software'].get('development'):
            capabilities.append('development-environment')
        
        # Service management
        if profile['service_manager'] == 'systemd':
            capabilities.append('systemd-service-control')
        elif profile['service_manager'] == 'sysvinit':
            capabilities.append('sysvinit-service-control')
        
        return capabilities

    def _calculate_confidence_score(self, profile: Dict) -> float:
        """Calculate confidence score based on successful detections."""
        total_categories = 7  # os, package_managers, service_manager, etc.
        successful_detections = 0
        
        if profile['os_info'].get('distribution') != 'unknown':
            successful_detections += 1
        if profile['package_managers']:
            successful_detections += 1
        if profile['service_manager'] != 'unknown':
            successful_detections += 1
        if profile['system_resources']:
            successful_detections += 1
        if profile['network_info']:
            successful_detections += 1
        if any(profile['installed_software'].values()):
            successful_detections += 1
        if profile['security_info']:
            successful_detections += 1
            
        return successful_detections / total_categories