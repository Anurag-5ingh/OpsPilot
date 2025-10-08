"""
System Context Manager
Manages server profiles and provides context-aware functionality
"""
import json
import asyncio
from typing import Dict, Optional, List
from .server_profiler import ServerProfiler
from .ai_analyzer import SystemAnalyzer


class SystemContextManager:
    """Manages system context and provides intelligent server-aware functionality"""
    
    def __init__(self):
        """Initialize the context manager"""
        self.profiles = {}  # host_key -> profile
        self.current_profiler = None
        self.analyzer = SystemAnalyzer()
    
    def initialize_context(self, ssh_client, force_refresh: bool = False) -> Dict:
        """
        Initialize system context for a new SSH connection
        
        Args:
            ssh_client: SSH client for the server
            force_refresh: Force re-profiling
            
        Returns:
            Server profile
        """
        # Create profiler for this connection
        self.current_profiler = ServerProfiler(ssh_client)
        
        # Profile the server
        profile = self.current_profiler.profile_server(force_refresh=force_refresh)
        
        # Store in context
        cache_key = self.current_profiler._get_cache_key()
        self.profiles[cache_key] = profile
        
        return profile
    
    def get_current_profile(self) -> Optional[Dict]:
        """Get the current server profile"""
        if self.current_profiler:
            return self.current_profiler.get_cached_profile()
        return None
    
    def get_context_for_command_generation(self, user_request: str) -> Dict:
        """
        Get enhanced context for AI command generation
        
        Args:
            user_request: User's natural language request
            
        Returns:
            Context dictionary for AI prompt enhancement
        """
        profile = self.get_current_profile()
        if not profile:
            return {"has_context": False, "message": "No server profile available"}
        
        # Build context for command generation
        context = {
            "has_context": True,
            "server_info": {
                "os": f"{profile['os']['name']} {profile['os']['version']}",
                "package_manager": profile['package_manager']['primary'],
                "init_system": profile['init_system'],
                "available_tools": profile.get('capabilities', {}),
                "sudo_access": profile.get('permissions', {}).get('has_sudo', False)
            },
            "confidence": profile.get('confidence_score', 0.5),
            "user_request": user_request,
            "context_type": "command_generation"
        }
        
        return context
    
    def get_context_for_troubleshooting(self, error_text: str, additional_context: Dict = None) -> Dict:
        """
        Get enhanced context for AI troubleshooting
        
        Args:
            error_text: Error message to troubleshoot
            additional_context: Additional context (command that failed, etc.)
            
        Returns:
            Context dictionary for troubleshooting AI
        """
        profile = self.get_current_profile()
        if not profile:
            return {"has_context": False, "message": "No server profile available"}
        
        context = {
            "has_context": True,
            "server_info": {
                "os": f"{profile['os']['name']} {profile['os']['version']}",
                "package_manager": profile['package_manager']['primary'],
                "init_system": profile['init_system'],
                "services": profile.get('services', {}),
                "capabilities": profile.get('capabilities', {}),
                "network": profile.get('network', {}),
                "paths": profile.get('paths', {})
            },
            "error_context": {
                "error_text": error_text,
                "additional_info": additional_context or {}
            },
            "confidence": profile.get('confidence_score', 0.5),
            "context_type": "troubleshooting"
        }
        
        return context
    
    def validate_command(self, command: str) -> Dict:
        """
        Validate command compatibility with current server
        
        Args:
            command: Command to validate
            
        Returns:
            Validation result with suggestions
        """
        if not self.current_profiler:
            return {
                "valid": True,
                "confidence": 0.5,
                "message": "No profiler available - assuming command is valid"
            }
        
        return self.current_profiler.validate_command_compatibility(command)
    
    def enhance_ai_prompt(self, base_prompt: str, context_type: str, **kwargs) -> str:
        """
        Enhance AI prompt with server context
        
        Args:
            base_prompt: Base AI prompt
            context_type: Type of context (command_generation, troubleshooting)
            **kwargs: Additional context parameters
            
        Returns:
            Enhanced prompt with server context
        """
        profile = self.get_current_profile()
        if not profile:
            return base_prompt
        
        if context_type == "command_generation":
            context = self.get_context_for_command_generation(kwargs.get('user_request', ''))
        elif context_type == "troubleshooting":
            context = self.get_context_for_troubleshooting(
                kwargs.get('error_text', ''),
                kwargs.get('additional_context', {})
            )
        else:
            return base_prompt
        
        # Build enhanced prompt
        enhanced_prompt = f"""{base_prompt}

IMPORTANT - SERVER CONTEXT:
You are working with a {context['server_info']['os']} server.

Server Details:
- Operating System: {context['server_info']['os']}
- Package Manager: {context['server_info']['package_manager']}
- Init System: {context['server_info']['init_system']}
- Sudo Access: {context['server_info'].get('sudo_access', 'Unknown')}

Available Capabilities:
{json.dumps(context['server_info'].get('available_tools', {}), indent=2)}

CRITICAL: Generate commands that are specifically compatible with this server configuration.
Consider the package manager, init system, and available tools when generating responses.
Profile Confidence: {context['confidence']:.2f}

"""
        
        return enhanced_prompt
    
    def get_system_summary(self) -> str:
        """Get a human-readable summary of the current system"""
        profile = self.get_current_profile()
        if not profile:
            return "No system profile available"
        
        summary_parts = [
            f"🖥️  System: {profile['os']['name']} {profile['os']['version']}",
            f"📦 Package Manager: {profile['package_manager']['primary']}",
            f"⚙️  Init System: {profile['init_system']}",
        ]
        
        if profile.get('services', {}).get('active'):
            active_services = profile['services']['active'][:5]  # Show first 5
            summary_parts.append(f"🔧 Active Services: {', '.join(active_services)}")
        
        if profile.get('capabilities'):
            caps = []
            for category, tools in profile['capabilities'].items():
                if tools:
                    caps.append(f"{category}: {len(tools)} tools")
            if caps:
                summary_parts.append(f"🛠️  Capabilities: {', '.join(caps)}")
        
        confidence = profile.get('confidence_score', 0)
        confidence_emoji = "🟢" if confidence > 0.8 else "🟡" if confidence > 0.5 else "🔴"
        summary_parts.append(f"{confidence_emoji} Profile Confidence: {confidence:.1%}")
        
        return "\n".join(summary_parts)
    
    def refresh_profile(self) -> bool:
        """
        Refresh the current server profile
        
        Returns:
            True if refresh was initiated successfully
        """
        if not self.current_profiler:
            return False
        
        # This would typically be called asynchronously
        # For now, just clear cache to force refresh on next access
        self.current_profiler.clear_cache()
        return True
    
    def export_profile(self, format: str = "json") -> str:
        """
        Export current profile in specified format
        
        Args:
            format: Export format (json, summary)
            
        Returns:
            Formatted profile data
        """
        profile = self.get_current_profile()
        if not profile:
            return "No profile available"
        
        if format == "json":
            return json.dumps(profile, indent=2)
        elif format == "summary":
            return self.get_system_summary()
        else:
            return str(profile)
    
    def get_command_suggestions(self, task_category: str) -> List[str]:
        """
        Get server-specific command suggestions for common tasks
        
        Args:
            task_category: Category of task (install, service, monitor, etc.)
            
        Returns:
            List of suggested commands for this server
        """
        profile = self.get_current_profile()
        if not profile:
            return []
        
        suggestions = []
        pkg_mgr = profile['package_manager']['primary']
        init_sys = profile['init_system']
        
        if task_category == "install":
            if pkg_mgr == "apt":
                suggestions = ["apt update", "apt install <package>", "apt search <term>"]
            elif pkg_mgr == "yum":
                suggestions = ["yum update", "yum install <package>", "yum search <term>"]
            elif pkg_mgr == "dnf":
                suggestions = ["dnf update", "dnf install <package>", "dnf search <term>"]
        
        elif task_category == "service":
            if init_sys == "systemd":
                suggestions = ["systemctl status <service>", "systemctl start <service>", "systemctl enable <service>"]
            else:
                suggestions = ["service <service> status", "service <service> start"]
        
        elif task_category == "monitor":
            suggestions = ["ps aux", "top", "htop", "df -h", "free -m"]
            if init_sys == "systemd":
                suggestions.extend(["journalctl -f", "systemctl list-units"])
        
        return suggestions
