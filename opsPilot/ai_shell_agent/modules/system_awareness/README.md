# System Awareness Module

The System Awareness module brings intelligent server profiling and context-aware command generation to OpsPilot. Instead of generating generic commands, the AI now understands your specific server configuration and generates targeted, compatible commands.

## 🎯 **Key Features**

### **AI-Powered Server Discovery**
- Automatically profiles servers using intelligent discovery commands
- AI analyzes command outputs to understand system configuration
- Minimal hardcoding - AI handles most analysis and adaptation

### **Context-Aware Command Generation**
- Commands tailored to specific OS, package managers, and available tools
- Enhanced AI prompts with server context
- Reduced command failures due to incompatible suggestions

### **Smart Server Profiling**
- Discovers OS type, version, and architecture
- Identifies package managers (apt, yum, dnf, apk, etc.)
- Detects init systems (systemd, init.d, OpenRC)
- Maps available services and capabilities
- Analyzes user permissions and sudo access

## 🏗️ **Architecture**

```
system_awareness/
├── __init__.py              # Module exports
├── ai_analyzer.py           # AI-powered system analysis
├── server_profiler.py       # Server discovery and profiling
├── context_manager.py       # Context management and integration
└── README.md               # This documentation
```

### **Core Components**

#### **SystemAnalyzer** (`ai_analyzer.py`)
- Uses AI to analyze raw command outputs
- Generates intelligent discovery commands
- Validates command compatibility
- Provides structured system insights

#### **ServerProfiler** (`server_profiler.py`)
- Executes discovery commands on target servers
- Caches profiles for performance
- Tracks discovery history and success rates
- Provides command validation

#### **SystemContextManager** (`context_manager.py`)
- Manages server profiles and context
- Enhances AI prompts with server information
- Provides context-aware functionality
- Handles profile storage and retrieval

## 🚀 **Usage**

### **Automatic Integration**
The system awareness is automatically activated when connecting to servers:

```python
# In your application
from ai_shell_agent.modules.system_awareness import SystemContextManager

system_context = SystemContextManager()

# Profile server on connection
profile = system_context.initialize_context(ssh_client)

# Use in command generation
result = ask_ai_for_command(user_input, memory, system_context=system_context)

# Use in troubleshooting
result = ask_ai_for_troubleshoot(error_text, context, system_context=system_context)
```

### **Web Interface Integration**
- Server profiling happens automatically on SSH connection
- System awareness status shown in UI
- Enhanced command suggestions based on server capabilities

### **CLI Integration**
- Automatic server profiling on startup
- System summary displayed after profiling
- Context-aware command generation throughout session

## 📊 **Server Profile Structure**

```json
{
  "os": {
    "name": "Ubuntu",
    "version": "20.04",
    "architecture": "x86_64"
  },
  "package_manager": {
    "primary": "apt",
    "available": ["apt", "snap"]
  },
  "init_system": "systemd",
  "services": {
    "active": ["nginx", "mysql", "docker"],
    "available": ["apache2", "postgresql"]
  },
  "capabilities": {
    "containerization": ["docker"],
    "web_servers": ["nginx"],
    "databases": ["mysql"]
  },
  "permissions": {
    "has_sudo": true,
    "user_groups": ["sudo", "docker"]
  },
  "confidence_score": 0.95,
  "profiling_metadata": {
    "timestamp": 1699123456,
    "discovery_commands_count": 12,
    "successful_commands": 11
  }
}
```

## 🔧 **API Endpoints**

### **POST /profile**
Profile a server and initialize system context:
```json
{
  "host": "10.0.0.1",
  "username": "ubuntu",
  "port": 22,
  "force_refresh": false
}
```

### **GET /profile/summary**
Get current server profile summary:
```json
{
  "summary": "🖥️ System: Ubuntu 20.04\n📦 Package Manager: apt...",
  "has_profile": true,
  "confidence": 0.95
}
```

### **GET /profile/suggestions/{category}**
Get server-specific command suggestions:
```json
{
  "category": "install",
  "suggestions": ["apt update", "apt install <package>"],
  "server_aware": true
}
```

## 🧠 **AI Integration**

### **Enhanced Prompts**
The system automatically enhances AI prompts with server context:

```
IMPORTANT - SERVER CONTEXT:
You are working with a Ubuntu 20.04 server.

Server Details:
- Operating System: Ubuntu 20.04
- Package Manager: apt
- Init System: systemd
- Sudo Access: true

Available Capabilities:
{
  "containerization": ["docker"],
  "web_servers": ["nginx"]
}

CRITICAL: Generate commands that are specifically compatible with this server configuration.
```

### **Command Validation**
Pre-execution validation ensures commands are compatible:
- Checks package manager availability
- Validates service manager compatibility
- Suggests alternatives for incompatible commands

## 🔄 **Workflow Enhancement**

### **Command Generation Flow**
1. **Server Profiling** → Understand system capabilities
2. **Context Enhancement** → Add server info to AI prompt
3. **Command Generation** → AI generates server-specific commands
4. **Validation** → Pre-execution compatibility check
5. **Execution** → Run validated commands
6. **Learning** → Update understanding based on results

### **Troubleshooting Flow**
1. **Error Analysis** → Combine error with server profile
2. **Targeted Diagnostics** → Use appropriate diagnostic tools
3. **Server-Specific Fixes** → Generate OS-appropriate solutions
4. **Verification** → Use server-compatible verification methods

## 📈 **Benefits**

### **Improved Accuracy**
- Commands tailored to specific server configurations
- Reduced failures due to incompatible suggestions
- Better understanding of available tools and services

### **Enhanced User Experience**
- Faster command execution with fewer errors
- More relevant troubleshooting suggestions
- Intelligent adaptation to different server types

### **AI-Driven Intelligence**
- Minimal hardcoding - AI handles most analysis
- Adaptive learning from command execution results
- Intelligent fallbacks for unsupported scenarios

## 🔒 **Security & Performance**

### **Security**
- Profile data stored temporarily in memory
- No sensitive information persisted
- SSH connections handled securely

### **Performance**
- Profile caching for repeated connections
- Intelligent command prioritization
- Minimal discovery overhead

### **Reliability**
- Graceful fallback to generic mode if profiling fails
- Error handling for discovery command failures
- Confidence scoring for profile reliability

## 🚀 **Future Enhancements**

- **Adaptive Learning**: Learn from command success/failure patterns
- **Profile Persistence**: Optional profile storage for frequent servers
- **Advanced Validation**: Real-time command compatibility checking
- **Multi-Server Context**: Handle multiple server profiles simultaneously
- **Custom Discovery**: User-defined discovery commands for specialized environments

The System Awareness module transforms OpsPilot from a generic command generator into an intelligent, server-aware DevOps assistant that understands and adapts to your specific infrastructure.
