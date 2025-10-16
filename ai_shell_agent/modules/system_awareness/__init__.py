"""
System Awareness Module

Provides server profiling and context-aware command generation capabilities.
Analyzes target servers to understand OS, package managers, services, and installed software
for more accurate AI-generated commands and troubleshooting.
"""

from .context_manager import SystemContextManager
from .server_profiler import ServerProfiler

__all__ = ['SystemContextManager', 'ServerProfiler']