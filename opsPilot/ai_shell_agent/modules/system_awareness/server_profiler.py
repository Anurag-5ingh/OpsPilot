"""
Server Profiler
Discovers and profiles server capabilities using AI-generated discovery commands
"""
import json
import time
from typing import Dict, List, Optional
from .ai_analyzer import SystemAnalyzer


class ServerProfiler:
    """Intelligent server profiling using AI-driven discovery"""
    
    def __init__(self, ssh_client):
        """
        Initialize profiler with SSH client
        
        Args:
            ssh_client: Paramiko SSH client for command execution
        """
        self.ssh_client = ssh_client
        self.analyzer = SystemAnalyzer()
        self.profile_cache = {}
        self.discovery_history = []
    
    def profile_server(self, force_refresh: bool = False) -> Dict:
        """
        Profile the server using AI-driven discovery
        
        Args:
            force_refresh: Force re-profiling even if cached profile exists
            
        Returns:
            Comprehensive server profile
        """
        # Generate cache key
        cache_key = self._get_cache_key()
        
        # Return cached profile if available and not forcing refresh
        if not force_refresh and cache_key in self.profile_cache:
            cached_profile = self.profile_cache[cache_key]
            if self._is_profile_fresh(cached_profile):
                return cached_profile
        
        print("🔍 Discovering server capabilities...")
        
        # Phase 1: Generate intelligent discovery commands
        discovery_commands = self.analyzer.generate_discovery_commands()
        
        # Phase 2: Execute discovery commands
        raw_outputs = self._execute_discovery_commands(discovery_commands)
        
        # Phase 3: AI analysis of outputs
        analysis_result = self.analyzer.analyze_system_info(raw_outputs)
        
        if analysis_result["success"]:
            system_profile = analysis_result["system_profile"]
        else:
            print(f"⚠️ AI analysis failed: {analysis_result.get('error')}")
            system_profile = analysis_result["system_profile"]  # fallback
        
        # Phase 4: Enhance profile with metadata
        enhanced_profile = self._enhance_profile(system_profile, raw_outputs)
        
        # Cache the profile
        self.profile_cache[cache_key] = enhanced_profile
        
        print(f"✅ Server profiled: {enhanced_profile['os']['name']} {enhanced_profile['os']['version']}")
        return enhanced_profile
    
    def _execute_discovery_commands(self, discovery_commands: List[Dict]) -> Dict:
        """Execute discovery commands and collect outputs"""
        # Import here to avoid circular dependency
        from ai_shell_agent.modules.ssh.client import run_shell
        
        raw_outputs = {}
        
        # Sort commands by priority
        sorted_commands = sorted(discovery_commands, key=lambda x: x.get('priority', 5), reverse=True)
        
        for cmd_info in sorted_commands:
            command = cmd_info['command']
            category = cmd_info.get('category', 'general')
            
            try:
                print(f"  Running: {command}")
                output, error = run_shell(command, ssh_client=self.ssh_client)
                
                raw_outputs[f"{category}_{len(raw_outputs)}"] = {
                    "command": command,
                    "output": output,
                    "error": error,
                    "success": not error,
                    "category": category,
                    "purpose": cmd_info.get('purpose', 'Discovery')
                }
                
                # Record in history
                self.discovery_history.append({
                    "command": command,
                    "timestamp": time.time(),
                    "success": not error
                })
                
            except Exception as e:
                print(f"  ❌ Command failed: {command} - {e}")
                raw_outputs[f"{category}_{len(raw_outputs)}"] = {
                    "command": command,
                    "output": "",
                    "error": str(e),
                    "success": False,
                    "category": category
                }
        
        return raw_outputs
    
    def _enhance_profile(self, system_profile: Dict, raw_outputs: Dict) -> Dict:
        """Enhance the AI-generated profile with additional metadata"""
        enhanced_profile = system_profile.copy()
        
        # Add profiling metadata
        enhanced_profile["profiling_metadata"] = {
            "timestamp": time.time(),
            "discovery_commands_count": len(raw_outputs),
            "successful_commands": sum(1 for output in raw_outputs.values() if output["success"]),
            "profiling_version": "1.0",
            "cache_key": self._get_cache_key()
        }
        
        # Add raw discovery data for debugging
        enhanced_profile["raw_discovery"] = raw_outputs
        
        # Calculate overall confidence
        if "confidence_score" not in enhanced_profile:
            enhanced_profile["confidence_score"] = self._calculate_confidence(raw_outputs)
        
        return enhanced_profile
    
    def _calculate_confidence(self, raw_outputs: Dict) -> float:
        """Calculate confidence score based on discovery success"""
        if not raw_outputs:
            return 0.0
        
        successful_commands = sum(1 for output in raw_outputs.values() if output["success"])
        total_commands = len(raw_outputs)
        
        base_confidence = successful_commands / total_commands
        
        # Boost confidence if we got key information
        key_info_bonus = 0.0
        for output in raw_outputs.values():
            if output["success"] and any(keyword in output["command"].lower() 
                                       for keyword in ["uname", "os-release", "systemctl", "which"]):
                key_info_bonus += 0.1
        
        return min(1.0, base_confidence + key_info_bonus)
    
    def _get_cache_key(self) -> str:
        """Generate cache key for the current SSH connection"""
        # Use SSH connection details as cache key
        try:
            transport = self.ssh_client.get_transport()
            if transport:
                host = transport.getpeername()[0]
                return f"{host}_{transport.remote_version}"
            return "unknown_host"
        except:
            return "unknown_connection"
    
    def _is_profile_fresh(self, profile: Dict, max_age_hours: int = 24) -> bool:
        """Check if cached profile is still fresh"""
        if "profiling_metadata" not in profile:
            return False
        
        timestamp = profile["profiling_metadata"].get("timestamp", 0)
        age_hours = (time.time() - timestamp) / 3600
        
        return age_hours < max_age_hours
    
    def get_cached_profile(self) -> Optional[Dict]:
        """Get cached profile if available"""
        cache_key = self._get_cache_key()
        return self.profile_cache.get(cache_key)
    
    def clear_cache(self):
        """Clear profile cache"""
        self.profile_cache.clear()
        print("🗑️ Profile cache cleared")
    
    def get_discovery_history(self) -> List[Dict]:
        """Get history of discovery commands"""
        return self.discovery_history.copy()
    
    def validate_command_compatibility(self, command: str) -> Dict:
        """
        Validate if a command is compatible with the current server
        
        Args:
            command: Command to validate
            
        Returns:
            Compatibility analysis
        """
        profile = self.get_cached_profile()
        if not profile:
            return {
                "compatible": True,  # Assume compatible if no profile
                "confidence": 0.5,
                "reason": "No server profile available"
            }
        
        return self.analyzer.analyze_command_compatibility(command, profile)
