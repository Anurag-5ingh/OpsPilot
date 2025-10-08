"""
AI-Powered System Analyzer
Uses AI to analyze server information and provide intelligent insights
"""
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# GPT-4o-mini client setup (reuse existing configuration)
try:
    client = OpenAI(
        base_url="https://aoai-farm.bosch-temp.com/api/openai/deployments/askbosch-prod-farm-openai-gpt-4o-mini-2024-07-18",
        api_key="dummy",
        default_headers={
            "genaiplatform-farm-subscription-key": "73620a9fe1d04540b9aabe89a2657a61",
        }
    )
except TypeError:
    import httpx
    client = OpenAI(
        base_url="https://aoai-farm.bosch-temp.com/api/openai/deployments/askbosch-prod-farm-openai-gpt-4o-mini-2024-07-18",
        api_key="dummy",
        default_headers={
            "genaiplatform-farm-subscription-key": "73620a9fe1d04540b9aabe89a2657a61",
        },
        http_client=httpx.Client()
    )


class SystemAnalyzer:
    """AI-powered system analysis for server profiling and context understanding"""
    
    def __init__(self):
        self.client = client
    
    def analyze_system_info(self, command_outputs: dict) -> dict:
        """
        Use AI to analyze raw system command outputs and extract structured information
        
        Args:
            command_outputs: Dict of command outputs from server discovery
            
        Returns:
            Structured system profile analyzed by AI
        """
        system_prompt = self._get_system_analysis_prompt()
        
        # Prepare the raw data for AI analysis
        analysis_request = {
            "task": "analyze_server_system",
            "raw_outputs": command_outputs
        }
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(analysis_request, indent=2)}
        ]
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                extra_query={"api-version": "2024-08-01-preview"},
                temperature=0.1,  # Low temperature for consistent analysis
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content.strip()
            analysis_result = json.loads(content)
            
            return {
                "success": True,
                "system_profile": analysis_result,
                "raw_analysis": content
            }
            
        except Exception as e:
            print(f"AI system analysis failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "system_profile": self._fallback_analysis(command_outputs)
            }
    
    def analyze_command_compatibility(self, command: str, system_profile: dict) -> dict:
        """
        Analyze if a command is compatible with the current system
        
        Args:
            command: The command to analyze
            system_profile: Current system profile
            
        Returns:
            Compatibility analysis and suggestions
        """
        compatibility_prompt = self._get_compatibility_analysis_prompt()
        
        analysis_request = {
            "command": command,
            "system_profile": system_profile
        }
        
        messages = [
            {"role": "system", "content": compatibility_prompt},
            {"role": "user", "content": json.dumps(analysis_request, indent=2)}
        ]
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                extra_query={"api-version": "2024-08-01-preview"},
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content.strip()
            return {
                "success": True,
                "analysis": json.loads(content)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "analysis": {"compatible": True, "confidence": 0.5, "alternatives": []}
            }
    
    def generate_discovery_commands(self, partial_info: dict = None) -> list:
        """
        Use AI to generate intelligent discovery commands based on partial system info
        
        Args:
            partial_info: Any existing system information to build upon
            
        Returns:
            List of discovery commands tailored to the system
        """
        discovery_prompt = self._get_discovery_prompt()
        
        request_data = {
            "task": "generate_discovery_commands",
            "existing_info": partial_info or {},
            "goal": "comprehensive_system_profiling"
        }
        
        messages = [
            {"role": "system", "content": discovery_prompt},
            {"role": "user", "content": json.dumps(request_data, indent=2)}
        ]
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                extra_query={"api-version": "2024-08-01-preview"},
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content.strip()
            result = json.loads(content)
            return result.get("commands", self._get_fallback_discovery_commands())
            
        except Exception as e:
            print(f"AI discovery command generation failed: {e}")
            return self._get_fallback_discovery_commands()
    
    def _get_system_analysis_prompt(self) -> str:
        """System analysis prompt for AI"""
        return """You are a system administrator expert analyzing server information.

Your task is to analyze raw command outputs and extract structured system information.

Analyze the provided command outputs and return a JSON object with this structure:
{
  "os": {
    "name": "Ubuntu/CentOS/Alpine/etc",
    "version": "20.04/8/etc",
    "architecture": "x86_64/arm64/etc"
  },
  "package_manager": {
    "primary": "apt/yum/dnf/apk/etc",
    "available": ["apt", "snap", "etc"]
  },
  "init_system": "systemd/init.d/openrc/etc",
  "services": {
    "active": ["nginx", "mysql", "etc"],
    "available": ["docker", "apache2", "etc"]
  },
  "capabilities": {
    "containerization": ["docker", "podman", "etc"],
    "web_servers": ["nginx", "apache2", "etc"],
    "databases": ["mysql", "postgresql", "etc"],
    "monitoring": ["systemctl", "service", "etc"]
  },
  "permissions": {
    "has_sudo": true/false,
    "user_groups": ["sudo", "docker", "etc"]
  },
  "network": {
    "interfaces": ["eth0", "lo", "etc"],
    "firewall": "ufw/iptables/firewalld/none"
  },
  "paths": {
    "config_dirs": ["/etc", "/usr/local/etc"],
    "log_dirs": ["/var/log", "/var/log/nginx"],
    "service_dirs": ["/etc/systemd/system", "/etc/init.d"]
  },
  "confidence_score": 0.95,
  "analysis_notes": "Additional insights about the system"
}

Be intelligent in your analysis. If commands fail or return errors, infer what you can from the failures.
Focus on practical information that would help generate better commands."""
    
    def _get_compatibility_analysis_prompt(self) -> str:
        """Command compatibility analysis prompt"""
        return """You are analyzing command compatibility with a specific server system.

Given a command and system profile, determine:
1. Will this command work on this system?
2. What's the confidence level?
3. What are better alternatives if needed?

Return JSON:
{
  "compatible": true/false,
  "confidence": 0.0-1.0,
  "issues": ["issue1", "issue2"],
  "alternatives": [
    {
      "command": "alternative command",
      "reason": "why this is better",
      "confidence": 0.0-1.0
    }
  ],
  "modifications": [
    {
      "original": "part of original command",
      "suggested": "suggested replacement",
      "reason": "why change is needed"
    }
  ],
  "reasoning": "detailed explanation"
}

Consider:
- Package manager compatibility (apt vs yum vs apk)
- Service manager compatibility (systemd vs init.d)
- Available software and versions
- Permission requirements
- Path differences"""
    
    def _get_discovery_prompt(self) -> str:
        """Discovery command generation prompt"""
        return """You are generating intelligent system discovery commands.

Generate commands that will reveal comprehensive system information with minimal overhead.
Prioritize commands that:
1. Work across different Linux distributions
2. Provide maximum information with minimal commands
3. Handle failures gracefully
4. Are safe to run (read-only when possible)

Return JSON:
{
  "commands": [
    {
      "command": "actual shell command",
      "purpose": "what this discovers",
      "category": "os/services/network/etc",
      "priority": 1-10,
      "fallback_on_error": true/false
    }
  ],
  "execution_strategy": "sequential/parallel",
  "estimated_time": "seconds",
  "safety_level": "safe/moderate/careful"
}

Focus on essential discovery that enables better command generation."""
    
    def _get_fallback_discovery_commands(self) -> list:
        """Minimal hardcoded fallback commands"""
        return [
            {
                "command": "uname -a",
                "purpose": "Basic system info",
                "category": "os",
                "priority": 10
            },
            {
                "command": "cat /etc/os-release 2>/dev/null || echo 'no-os-release'",
                "purpose": "OS identification",
                "category": "os", 
                "priority": 10
            },
            {
                "command": "which systemctl apt yum dnf apk docker 2>/dev/null || echo 'tools-check'",
                "purpose": "Available tools",
                "category": "tools",
                "priority": 9
            }
        ]
    
    def _fallback_analysis(self, command_outputs: dict) -> dict:
        """Basic fallback analysis when AI fails"""
        return {
            "os": {"name": "Unknown", "version": "Unknown"},
            "package_manager": {"primary": "unknown"},
            "init_system": "unknown",
            "services": {"active": [], "available": []},
            "capabilities": {},
            "permissions": {"has_sudo": False},
            "confidence_score": 0.1,
            "analysis_notes": "Fallback analysis - AI analysis failed"
        }
