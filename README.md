# OpsPilot - Enterprise AI DevOps Platform

**OpsPilot** has evolved into a comprehensive, enterprise-grade AI DevOps platform that combines intelligent automation, proactive monitoring, predictive analytics, and robust recovery mechanisms. With advanced machine learning capabilities and multi-server orchestration, OpsPilot transforms complex DevOps operations into intelligent, secure, and reliable workflows.

## 🚀 **Platform Overview**

OpsPilot provides **seven major enhancement modules** that work together to deliver unprecedented intelligence and automation for DevOps operations:

1. **🧠 Context-Aware Command Learning** - Adaptive learning from user patterns
2. **📊 Real-time System Monitoring** - Proactive health tracking with ML anomaly detection
3. **🔮 Predictive Failure Prevention** - ML-powered failure prediction and prevention
4. **🌐 Multi-server Command Coordination** - Intelligent orchestration across multiple servers
5. **🔄 Enhanced Command Rollback System** - Comprehensive recovery with system snapshots
6. **🛡️ Security Compliance Checker** - ML-enhanced policy validation
7. **📚 Smart Documentation Generator** - Automated documentation from command patterns

## 🧠 **Intelligence & Learning Features**

### 🎯 **Advanced Machine Learning**
- **Multi-Model Ensemble**: Random Forest, Gradient Boosting, and Logistic Regression for superior accuracy
- **Adaptive Risk Scoring**: Continuously evolving risk assessment based on execution outcomes
- **Pattern Recognition**: Identifies user behavior patterns and system trends automatically
- **Contextual Learning**: Learns from environment, timing, and user preferences
- **Predictive Analytics**: Anticipates failures before they occur with high accuracy

### 🔍 **Context-Aware Intelligence**
- **User Behavior Modeling**: Analyzes command patterns, frequencies, and success rates
- **Temporal Pattern Recognition**: Learns time-based usage patterns and preferences
- **System Context Analysis**: Understands environment, load, and operational context
- **Command Sequence Learning**: Recognizes common command sequences and workflows
- **Auto-completion & Suggestions**: Intelligent command suggestions based on learned patterns

### 🛡️ **Security & Compliance Intelligence**
- **Multi-Framework Compliance**: SOX, PCI DSS, HIPAA, CIS, NIST policy validation
- **ML-Enhanced Security**: Learns from security violations and improves detection
- **Contextual Policy Enforcement**: Adapts security rules based on user role and environment
- **Risk Assessment**: Comprehensive risk analysis for individual commands and operations
- **Compliance Recommendations**: Suggests compliant alternatives for policy violations

## 🚀 **Core Enhancement Modules**

### 1. **🧠 Context-Aware Command Learning**
**Adaptive learning system that becomes smarter with every interaction**

- **Pattern Recognition**: Analyzes user command patterns, frequencies, and success rates
- **Behavioral Modeling**: Learns individual user preferences and working patterns
- **Contextual Recommendations**: Provides intelligent suggestions based on current context
- **Auto-completion**: Smart command completion based on historical usage
- **Success Prediction**: Estimates likelihood of command success in current context
- **Workflow Recognition**: Identifies common command sequences and suggests next steps

**Technical Implementation:**
- TF-IDF vectorization for command similarity analysis
- K-means clustering for pattern grouping
- SQLite database for pattern storage and retrieval
- Real-time feature extraction from execution context

### 2. **📊 Real-time System Monitoring**
**Proactive health tracking with ML-powered anomaly detection**

- **Comprehensive Metrics**: CPU, memory, disk, network, processes, and services
- **ML Anomaly Detection**: Isolation Forest algorithms for intelligent anomaly detection
- **Intelligent Alerting**: Context-aware alerts with actionable recommendations
- **Performance Trending**: Historical analysis and performance trend identification
- **Health Scoring**: Overall system health score with risk assessment
- **Auto-resolution**: Automatic alert resolution when conditions normalize

**Technical Implementation:**
- Multi-threaded metric collection with configurable intervals
- Isolation Forest models for each metric type
- Standard scaler for feature normalization
- Sliding window training data management
- Real-time alert generation with callback system

### 3. **🔮 Predictive Failure Prevention**
**ML-powered system that prevents failures before they occur**

- **Failure Prediction**: Anticipates disk space, memory, CPU, and service failures
- **Early Warning System**: Alerts before critical thresholds are reached
- **Preventive Actions**: Automated execution of safe preventive measures
- **Feature Engineering**: Advanced feature extraction from system metrics
- **Ensemble Models**: Random Forest, Gradient Boosting, and Logistic Regression
- **Risk Scoring**: Confidence-based prediction scoring system

**Technical Implementation:**
- Multi-model ensemble with weighted voting
- Feature selection using SelectKBest and f_classif
- Cross-validation for model performance assessment
- ROC AUC scoring for binary classification accuracy
- Automated model retraining with performance monitoring

### 4. **🌐 Multi-server Command Coordination**
**Enterprise-grade orchestration for complex multi-server operations**

- **Execution Strategies**: Sequential, Parallel, Rolling, Canary, and Blue-Green deployments
- **Dependency Management**: Intelligent resolution with topological sorting
- **Risk Assessment**: ML-enhanced risk analysis for multi-server operations
- **Failure Recovery**: Comprehensive rollback with configurable strategies
- **Progress Tracking**: Real-time monitoring of orchestration progress
- **SSH Pool Management**: Efficient connection pooling and reuse

**Technical Implementation:**
- Topological sorting for dependency resolution
- ThreadPoolExecutor for concurrent command execution
- SSH connection pooling with health checking
- Comprehensive execution result tracking and analysis
- Configurable rollback strategies with auto-execution

### 5. **🔄 Enhanced Command Rollback System**
**Comprehensive recovery mechanisms with system snapshots**

- **System Snapshots**: File system, configuration, services, and environment snapshots
- **Granular Rollback**: Step-by-step rollback with multiple recovery methods
- **Recovery Points**: Comprehensive system state capture and restoration
- **Automatic Rollback**: Intelligent rollback command generation
- **Compression & Deduplication**: Efficient storage with smart deduplication
- **Validation**: Post-rollback validation and verification

**Technical Implementation:**
- Multiple snapshot types with specialized handlers
- Gzip compression for efficient storage
- SHA256 hashing for content deduplication
- SQLite database for operation tracking
- Automatic rollback command generation based on operation type

### 6. **🛡️ Security Compliance Checker**
**ML-enhanced policy validation for enterprise security**

- **Multi-Framework Support**: SOX, PCI DSS, HIPAA, CIS, NIST compliance validation
- **Contextual Analysis**: Considers user role, environment, and system state
- **ML Learning**: Learns from user approvals and violation patterns
- **Alternative Suggestions**: Provides compliant command alternatives
- **Risk Scoring**: Comprehensive risk assessment for policy violations
- **Audit Trails**: Complete compliance audit logging

**Technical Implementation:**
- Regex and pattern-based policy matching
- Context-aware rule evaluation
- Machine learning from historical compliance decisions
- Configurable policy frameworks and custom rules
- Integration with existing security tools and workflows

### 7. **📚 Smart Documentation Generator**
**Automated documentation from command patterns and workflows**

- **Pattern Analysis**: Analyzes frequently executed command sequences
- **Automatic Runbooks**: Generates step-by-step operational procedures
- **Troubleshooting Guides**: Creates guides based on error patterns
- **Multiple Formats**: Supports Markdown, JSON, HTML, and plain text
- **Risk Assessment**: Documents risk levels and safety considerations
- **Template System**: Customizable documentation templates

**Technical Implementation:**
- Command sequence analysis and pattern recognition
- Template-based documentation generation
- Multiple output format support
- Integration with command execution history
- Automated documentation updates based on usage patterns

## Quickstart (Windows PowerShell)

1) Create a virtual environment and install dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2) Run the web server

```powershell
python app.py
```

- App runs at http://localhost:8080
- UI is available at http://localhost:8080/opspilot

3) Run the interactive CLI (optional)

```powershell
python main.py
```

## Configuration

Environment variables (optional):
- APP_SECRET: Flask secret key (default: dev_secret_change_me)
- REMOTE_HOST: Default host for non-interactive command execution
- REMOTE_USER: Default user for non-interactive command execution
- REMOTE_PORT: Default port (22 if unset)

Example (PowerShell):
```powershell
$env:APP_SECRET = "dev_secret_change_me"
$env:REMOTE_HOST = "10.0.0.1"
$env:REMOTE_USER = "ubuntu"
$env:REMOTE_PORT = "22"
```

## 📁 **Enhanced Project Structure**

```
OpsPilot/
├── ai_shell_agent/                    # Core Backend Platform
│   ├── modules/                       # Advanced Enhancement Modules
│   │   ├── command_generation/        # Smart Command Generation
│   │   │   ├── ai_handler.py              # AI command generation
│   │   │   ├── risk_analyzer.py           # Rule-based risk analysis
│   │   │   ├── fallback_analyzer.py       # Command failure analysis
│   │   │   ├── ml_risk_scorer.py          # ML-enhanced risk scoring
│   │   │   ├── ml_database_manager.py     # Training data management
│   │   │   └── data_collector.py          # Automatic data collection
│   │   ├── learning/                  # 🧠 Context-Aware Learning
│   │   │   └── context_aware_learner.py   # Adaptive command learning
│   │   ├── monitoring/                # 📊 Real-time Monitoring
│   │   │   └── real_time_monitor.py       # ML-powered system monitoring
│   │   ├── prediction/                # 🔮 Failure Prevention
│   │   │   └── failure_predictor.py       # ML failure prediction
│   │   ├── orchestration/             # 🌐 Multi-server Coordination
│   │   │   └── multi_server_coordinator.py # Enterprise orchestration
│   │   ├── rollback/                  # 🔄 Enhanced Rollback
│   │   │   └── rollback_manager.py        # Comprehensive recovery
│   │   ├── security/                  # 🛡️ Security & Compliance
│   │   │   └── compliance_checker.py      # ML policy validation
│   │   ├── documentation/             # 📚 Smart Documentation
│   │   │   └── smart_doc_generator.py     # Automated documentation
│   │   ├── troubleshooting/           # Intelligent Troubleshooting
│   │   │   └── troubleshoot_engine.py     # Multi-step error analysis
│   │   ├── system_awareness/          # System Profiling
│   │   │   └── system_profiler.py         # OS/system detection
│   │   ├── ssh/                       # SSH Management
│   │   │   └── ssh_manager.py             # Connection management
│   │   └── shared/                    # Shared Utilities
│   │       └── conversation_memory.py     # Context management
│   ├── api/                          # REST API Layer
│   │   ├── endpoints/                 # API Endpoints
│   │   │   ├── command_generation.py      # Command API endpoints
│   │   │   ├── monitoring.py              # Monitoring API endpoints
│   │   │   ├── orchestration.py           # Orchestration API endpoints
│   │   │   └── troubleshooting.py         # Troubleshooting API endpoints
│   │   └── middleware/                # API Middleware
│   │       ├── auth.py                   # Authentication
│   │       └── rate_limiter.py           # Rate limiting
│   ├── utils/                        # Core Utilities
│   │   └── logging_utils.py           # Logging configuration
│   └── main_runner.py                # CLI Entry Point
├── frontend/                          # Enhanced Frontend
│   ├── js/                            # JavaScript Modules
│   │   ├── main.js                    # Application entry point
│   │   ├── utils.js                   # Shared utilities
│   │   ├── command-mode.js            # Command generation UI
│   │   ├── troubleshoot-mode.js       # Troubleshooting UI
│   │   └── terminal.js                # SSH terminal
│   ├── css/                           # Stylesheets
│   │   └── main.css                   # Main stylesheet
│   ├── assets/                        # Static Assets
│   │   └── icons/                     # UI icons
│   └── index.html                     # Main HTML
├── data/                              # Data Storage (Auto-created)
│   ├── ml_risk_database.db            # ML training data
│   ├── command_learning.db            # Command learning data
│   ├── monitoring_metrics.db          # Monitoring data
│   ├── failure_prediction.db          # Prediction data
│   └── rollback_operations.db         # Rollback data
├── models/                            # ML Models (Auto-created)
│   ├── risk_scorer_models/            # Risk scoring models
│   ├── command_learning_models/       # Learning models
│   ├── monitoring_models/             # Anomaly detection models
│   ├── prediction_models/             # Failure prediction models
│   └── compliance_models/             # Compliance models
├── storage/                           # File Storage (Auto-created)
│   ├── rollback_storage/              # System snapshots
│   ├── documentation/                 # Generated docs
│   └── logs/                          # System logs
├── config/                            # Configuration Files
│   ├── compliance_policies.json       # Security policies
│   ├── monitoring_config.json         # Monitoring configuration
│   └── orchestration_config.json     # Orchestration settings
├── tests/                             # Comprehensive Test Suite
│   ├── unit/                          # Unit tests
│   ├── integration/                   # Integration tests
│   └── performance/                   # Performance tests
├── docs/                              # Documentation
│   ├── API_REFERENCE.md               # Complete API documentation
│   ├── ARCHITECTURE.md                # System architecture
│   ├── ML_SYSTEM.md                   # ML system details
│   └── DEPLOYMENT.md                  # Deployment guide
├── app.py                             # Flask Application
├── main.py                            # CLI Entrypoint
├── requirements.txt                   # Python Dependencies
├── docker-compose.yml                # Container orchestration
├── Dockerfile                        # Container definition
└── README.md                          # This file
```

## 📡 **Comprehensive API Reference**

### 🧠 Context-Aware Learning APIs
- **POST /api/v1/learning/suggestions** - Get intelligent command suggestions
  - Body: `{ "partial_command": "docker", "context": {...}, "user_id": "user123" }`
  - Returns: `{ "suggestions": [{"command": "docker ps", "confidence": 0.9, "reason": "..."}], ... }`

- **POST /api/v1/learning/record-execution** - Record command execution for learning
  - Body: `{ "command": "ls -la", "outcome": "success", "context": {...} }`
  - Returns: `{ "success": true, "learning_updated": true }`

- **GET /api/v1/learning/patterns/{user_id}** - Analyze user's command patterns
  - Returns: `{ "patterns": {...}, "most_used_commands": [...], "temporal_patterns": {...} }`

- **GET /api/v1/learning/auto-complete** - Get auto-completion suggestions
  - Query: `?partial_command=dock&user_id=user123`
  - Returns: `{ "completions": ["docker", "docker-compose", ...] }`

### 📊 Real-time Monitoring APIs
- **POST /api/v1/monitoring/start** - Start system monitoring
  - Body: `{ "config": { "collection_interval": 30, "anomaly_detection": true } }`
  - Returns: `{ "monitoring_id": "mon_123", "status": "running" }`

- **GET /api/v1/monitoring/metrics/current** - Get current system metrics
  - Returns: `{ "metrics": [...], "timestamp": "...", "health_score": 95 }`

- **GET /api/v1/monitoring/alerts/active** - Get active system alerts
  - Returns: `{ "alerts": [...], "total_count": 3, "critical_count": 1 }`

- **POST /api/v1/monitoring/thresholds** - Set custom alert thresholds
  - Body: `{ "metric_pattern": "cpu.usage_percent", "warning": 80, "critical": 95 }`
  - Returns: `{ "success": true, "threshold_updated": true }`

- **GET /api/v1/monitoring/history/{metric_name}** - Get metric history
  - Query: `?hours_back=24`
  - Returns: `{ "history": [...], "trend_analysis": {...} }`

### 🔮 Predictive Failure Prevention APIs
- **POST /api/v1/prediction/analyze-snapshot** - Analyze system snapshot for failure prediction
  - Body: `{ "system_snapshot": {...}, "prediction_types": ["disk_space", "memory"] }`
  - Returns: `{ "predictions": [...], "risk_score": 0.7, "recommended_actions": [...] }`

- **GET /api/v1/prediction/active-predictions** - Get active failure predictions
  - Returns: `{ "predictions": [...], "critical_count": 2, "total_count": 5 }`

- **POST /api/v1/prediction/train-models** - Train failure prediction models
  - Body: `{ "days_back": 30, "failure_types": ["disk_space", "memory_exhaustion"] }`
  - Returns: `{ "training_results": {...}, "model_performance": {...} }`

- **GET /api/v1/prediction/statistics** - Get prediction accuracy statistics
  - Returns: `{ "accuracy_by_type": {...}, "total_predictions": 150, "prevention_success_rate": 0.85 }`

### 🌐 Multi-server Orchestration APIs
- **POST /api/v1/orchestration/plans** - Create orchestration plan
  - Body: `{ "name": "deploy-v2", "servers": [...], "commands": [...], "execution_config": {...} }`
  - Returns: `{ "plan_id": "plan_123", "risk_assessment": {...}, "execution_phases": [...] }`

- **POST /api/v1/orchestration/plans/{plan_id}/execute** - Execute orchestration plan
  - Body: `{ "confirm": true, "include_details": false }`
  - Returns: `{ "execution_id": "exec_123", "status": "running", "phase_count": 3 }`

- **GET /api/v1/orchestration/plans/{plan_id}/risk-assessment** - Get plan risk assessment
  - Body: `{ "system_context": {...} }`
  - Returns: `{ "overall_risk_score": 0.4, "command_risks": {...}, "mitigation_suggestions": [...] }`

- **POST /api/v1/orchestration/plans/{plan_id}/simulate** - Simulate plan execution
  - Returns: `{ "simulation_results": {...}, "estimated_duration": 300, "warnings": [...] }`

- **GET /api/v1/orchestration/execution-history** - Get execution history
  - Query: `?limit=20`
  - Returns: `{ "history": [...], "success_rate": 0.92 }`

- **GET /api/v1/orchestration/strategies** - Get available execution strategies
  - Returns: `{ "strategies": {...}, "dependency_types": {...} }`

### 🔄 Enhanced Rollback APIs
- **POST /api/v1/rollback/operations/{operation_id}/start** - Start tracking operation
  - Body: `{ "description": "Database migration", "context": {...} }`
  - Returns: `{ "success": true, "recovery_point_id": "rp_123" }`

- **POST /api/v1/rollback/operations/{operation_id}/add-step** - Add operation step
  - Body: `{ "command": "...", "operation_type": "database_operation", "rollback_command": "..." }`
  - Returns: `{ "step_id": "step_123", "pre_snapshot_id": "snap_456" }`

- **POST /api/v1/rollback/operations/{operation_id}/rollback** - Rollback operation
  - Body: `{ "recovery_mode": "automatic", "target_step": "step_5", "dry_run": false }`
  - Returns: `{ "rollback_id": "rb_123", "steps_to_rollback": 3, "estimated_duration": 120 }`

- **POST /api/v1/rollback/recovery-points** - Create recovery point
  - Body: `{ "description": "Pre-deployment checkpoint", "operation_context": {...} }`
  - Returns: `{ "recovery_point_id": "rp_789", "snapshots": [...] }`

- **POST /api/v1/rollback/recovery-points/{rp_id}/restore** - Restore to recovery point
  - Body: `{ "dry_run": false }`
  - Returns: `{ "success": true, "restored_snapshots": 4, "validation_results": [...] }`

- **GET /api/v1/rollback/operations/{operation_id}/status** - Get operation status
  - Returns: `{ "total_steps": 5, "executed_steps": 3, "rollback_ready": true, "steps": [...] }`

### 🛡️ Security & Compliance APIs
- **POST /api/v1/security/check-compliance** - Check command compliance
  - Body: `{ "command": "rm -rf /", "context": {...}, "user_context": {...} }`
  - Returns: `{ "compliant": false, "violations": [...], "alternative_commands": [...] }`

- **GET /api/v1/security/policies/{framework}** - Get compliance policies
  - Returns: `{ "policies": [...], "framework": "SOX", "total_rules": 45 }`

- **POST /api/v1/security/policies/validate** - Validate custom policy
  - Body: `{ "policy": {...}, "test_commands": [...] }`
  - Returns: `{ "valid": true, "test_results": [...] }`

### 📚 Smart Documentation APIs
- **POST /api/v1/documentation/generate** - Generate documentation
  - Body: `{ "command_sequences": [...], "format": "markdown", "include_risks": true }`
  - Returns: `{ "documentation": "...", "generated_sections": [...] }`

- **GET /api/v1/documentation/runbooks** - List generated runbooks
  - Returns: `{ "runbooks": [...], "total_count": 12 }`

- **POST /api/v1/documentation/troubleshooting-guide** - Generate troubleshooting guide
  - Body: `{ "error_patterns": [...], "historical_data": {...} }`
  - Returns: `{ "guide": "...", "solution_patterns": [...] }`

### Legacy Core APIs (Enhanced)
- **POST /ask** - Enhanced command generation with all modules
  - Body: `{ "prompt": "deploy to production", "context": {...} }`
  - Returns: `{ "ai_command": "...", "risk_analysis": {...}, "compliance_check": {...}, "suggestions": [...] }`

- **POST /run** - Execute with comprehensive monitoring and rollback
  - Body: `{ "host": "server1", "username": "admin", "command": "...", "create_rollback_point": true }`
  - Returns: `{ "output": "...", "monitoring_data": {...}, "rollback_info": {...} }`

- **POST /troubleshoot** - Enhanced troubleshooting with ML prediction
  - Body: `{ "error_text": "...", "system_context": {...} }`
  - Returns: `{ "analysis": "...", "failure_predictions": [...], "preventive_actions": [...] }`

### WebSocket Events (Enhanced Terminal)
- `start_ssh` - Start monitored SSH session
- `terminal_input` - Send keystrokes with learning
- `terminal_output` - Receive output with analysis
- `system_alert` - Real-time system alerts
- `prediction_alert` - Failure prediction alerts
- `compliance_warning` - Security compliance warnings
- `resize` - Update terminal size
- `disconnect` - Close session with cleanup

## 🏢 **Enterprise Architecture**

### 📝 **System Architecture Overview**

OpsPilot follows a **modular, microservice-inspired architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────┐
│              Frontend (Web UI)                 │
│  React-like Components + WebSocket Terminal    │
└────────────────┬─────────────────────────────┘
                 │
┌────────────────┴─────────────────────────────┐
│              REST API Layer                   │
│     Flask + SocketIO + Authentication        │
└────────────────┬─────────────────────────────┘
                 │
┌────────────────┴─────────────────────────────┐
│        Enhancement Modules (7 Core)          │
├───────────────┬───────────────┬───────────────┤
│ Learning      │ Monitoring    │ Prediction  │
├───────────────┼───────────────┼───────────────┤
│ Orchestration │ Rollback      │ Security    │
└───────────────┴───────────────┴───────────────┘
                 │
┌────────────────┴─────────────────────────────┐
│               Data Layer                     │
│   SQLite DBs + ML Models + File Storage     │
└─────────────────────────────────────────────┘
```

### 🧠 **Enhancement Modules Architecture**

#### **Context-Aware Learning** (`ai_shell_agent/modules/learning/`)
- **Pattern Analysis Engine**: TF-IDF vectorization + K-means clustering
- **Behavioral Modeling**: Statistical analysis of user command patterns
- **Contextual Recommendation**: Real-time feature extraction and matching
- **Learning Database**: SQLite with optimized indexing for pattern queries
- **Auto-completion Engine**: Efficient prefix matching with confidence scoring

#### **Real-time Monitoring** (`ai_shell_agent/modules/monitoring/`)
- **Metric Collection**: Multi-threaded psutil-based system monitoring
- **Anomaly Detection**: Isolation Forest models per metric type
- **Alert Engine**: Intelligent threshold-based + ML-based alerting
- **Data Pipeline**: Streaming data processing with sliding windows
- **Health Scoring**: Weighted composite health score calculation

#### **Predictive Prevention** (`ai_shell_agent/modules/prediction/`)
- **Feature Engineering**: Advanced temporal and statistical feature extraction
- **Ensemble Models**: Random Forest + Gradient Boosting + Logistic Regression
- **Prediction Engine**: Multi-model voting with confidence weighting
- **Prevention Actions**: Automated safe action execution framework
- **Performance Tracking**: Cross-validation and ROC AUC monitoring

#### **Multi-server Orchestration** (`ai_shell_agent/modules/orchestration/`)
- **Dependency Resolution**: Topological sorting with cycle detection
- **Execution Strategies**: Pluggable execution pattern implementations
- **Risk Assessment**: ML-enhanced multi-server risk analysis
- **Connection Pooling**: Efficient SSH connection management and reuse
- **Progress Tracking**: Real-time execution monitoring with callbacks

#### **Enhanced Rollback** (`ai_shell_agent/modules/rollback/`)
- **Snapshot Engine**: Multi-type snapshots with compression and deduplication
- **Recovery Points**: Comprehensive system state capture and restoration
- **Operation Tracking**: Detailed step-by-step execution history
- **Auto-rollback Generation**: Intelligent rollback command synthesis
- **Validation Framework**: Post-rollback verification and health checks

#### **Security & Compliance** (`ai_shell_agent/modules/security/`)
- **Policy Engine**: Multi-framework compliance rule evaluation
- **Contextual Analysis**: Environment and role-aware policy enforcement
- **ML Learning**: Adaptive policy enforcement based on historical decisions
- **Alternative Generation**: Compliant command alternative suggestions
- **Audit System**: Comprehensive compliance logging and reporting

#### **Smart Documentation** (`ai_shell_agent/modules/documentation/`)
- **Pattern Recognition**: Command sequence analysis and clustering
- **Template System**: Configurable documentation template engine
- **Multi-format Output**: Markdown, JSON, HTML, and plain text generation
- **Risk Integration**: Automated risk assessment documentation
- **Version Control**: Documentation versioning and change tracking

### 🗺️ **Data Flow Architecture**

```
User Request → API Gateway → Module Router → Enhancement Modules
     │                                               │
     v                                               v
WebSocket → Terminal Handler → SSH Executor → Data Collector
     │                                               │
     v                                               v
ML Pipeline → Risk Assessment → Compliance Check → Response
```

### 🔌 **Integration Architecture**

- **Event-Driven**: Callback-based integration between modules
- **Plugin System**: Modular architecture allows independent module usage
- **Data Sharing**: Shared context and learning across all modules
- **API First**: RESTful APIs for all module functionality
- **Async Processing**: Non-blocking operations with threading and async/await

### 📦 **Legacy Core Modules** (Backward Compatible)

#### **Smart Command Generation** (`ai_shell_agent/modules/command_generation/`)
- **AI Command Generation**: GPT-4o-mini with temperature 0.3 for consistent commands
- **ML Risk Scoring**: Machine learning model learns from execution outcomes
- **Risk Analysis**: Multi-layered risk assessment with rule-based + ML predictions
- **Failure Analysis**: Intelligent analysis of failed commands with alternatives
- **Auto Data Collection**: Seamless integration for continuous learning

#### **Intelligent Troubleshooting** (`ai_shell_agent/modules/troubleshooting/`)
- **Error Pattern Recognition**: AI analyzes error patterns with historical context
- **Multi-step Remediation**: Diagnostics → Fixes → Verification workflow
- **System-Aware Solutions**: Tailored fixes based on server profiling
- **Risk-Assessed Actions**: ML-enhanced risk evaluation for fix commands
- **Alternative Suggestions**: Multiple solution paths with success probability

#### **System Awareness** (`ai_shell_agent/modules/system_awareness/`)
- **Server Profiling**: Auto-detects OS, package managers, service managers
- **Context Management**: Maintains system state and capabilities
- **Command Optimization**: Tailors commands to specific system configurations
- **Performance Monitoring**: Tracks system resources for intelligent decisions

#### **SSH Management** (`ai_shell_agent/modules/ssh/`)
- SSH client creation and management with automatic data collection
- Command execution over SSH with timing and outcome tracking
- Session management endpoints

#### **Shared Utilities** (`ai_shell_agent/modules/shared/`)
- Conversation memory (max 20 entries) with learning integration
- Utility functions (path normalization, data validation, etc.)

### 🗺️ **Frontend Architecture**

- **main.js** - Application entry point and event listeners
- **utils.js** - Shared state and utilities
- **terminal.js** - SSH terminal functionality  
- **command-mode.js** - Command generation UI
- **troubleshoot-mode.js** - Troubleshooting UI

## 🔧 **Enterprise Technology Stack**

### 🚀 **Backend Technologies**

#### **Core Framework**
- **Python 3.10+** with asyncio for high-performance asynchronous operations
- **Flask** for REST API endpoints with modular blueprint architecture
- **Flask-SocketIO** for real-time WebSocket communication and live updates
- **Celery** (future) for distributed task processing

#### **AI & Machine Learning**
- **OpenAI GPT-4o-mini** for AI command generation (temperature 0.3)
- **scikit-learn** for comprehensive ML model pipeline
  - Random Forest, Gradient Boosting, Logistic Regression
  - Isolation Forest for anomaly detection
  - TF-IDF vectorization and K-means clustering
- **numpy** & **pandas** for advanced data processing
- **joblib** for model persistence and optimization

#### **Data & Storage**
- **SQLite** with optimized indexing for development/small deployments
- **PostgreSQL** support for enterprise deployments
- **Redis** (future) for caching and session management
- **JSON** for configuration and lightweight data exchange

#### **System Integration**
- **Paramiko** for robust SSH client connections with connection pooling
- **psutil** for comprehensive system monitoring and resource tracking
- **threading** & **concurrent.futures** for multi-threaded operations
- **subprocess** for secure local command execution

#### **Security & Compliance**
- **cryptography** for encryption and secure data handling
- **hashlib** for secure hashing and validation
- **JWT** (future) for authentication and authorization

### 🎨 **Frontend Technologies**

#### **Core Technologies**
- **Modern JavaScript (ES2020+)** with async/await patterns
- **HTML5** semantic markup with ARIA accessibility compliance
- **CSS3** with custom properties, flexbox, and grid layouts
- **Progressive Web App (PWA)** capabilities

#### **Real-time Communication**
- **Socket.IO client** for bidirectional real-time communication
- **WebSocket** native support for low-latency connections
- **Fetch API** for modern HTTP request handling

#### **Terminal & UI**
- **Xterm.js** for professional terminal emulation
- **Chart.js** (future) for monitoring visualizations
- **CodeMirror** (future) for syntax highlighting

### 🛠️ **DevOps & Deployment**

- **Docker** containerization support
- **GitHub Actions** for CI/CD pipeline
- **pytest** for comprehensive testing framework
- **Black** & **isort** for code formatting
- **flake8** for code linting and quality assurance

## 🎯 Usage

### Web Interface

1. Navigate to `http://localhost:8080/opspilot`
2. Enter SSH credentials (host, username)
3. Choose mode:
   - **Command Mode**: Generate commands from natural language
   - **Troubleshoot Mode**: Analyze and fix errors

### Smart Command Mode
1. Type natural language request: "list all files"
2. AI generates command with ML-enhanced risk analysis: `ls -la`
3. Review risk warnings and safety recommendations
4. Confirm to execute (decision is automatically learned from)
5. System learns from execution outcome to improve future predictions

### Intelligent Troubleshoot Mode
1. Paste error message: "nginx: bind() failed"
2. AI analyzes with system context and creates smart remediation plan:
   - **Root Cause Analysis**: Pattern recognition from historical data
   - **Diagnostic Commands**: System-aware discovery commands
   - **Fix Commands**: ML risk-assessed repair actions
   - **Verification Commands**: Comprehensive validation steps
   - **Alternative Solutions**: Multiple approaches with success probability
3. Execute steps with intelligent confirmation and automatic learning

## 🔐 Security & Privacy

- **Smart Risk Assessment**: ML-enhanced security analysis of commands
- **Behavioral Learning**: Adapts to user patterns while maintaining security
- **Local Data Storage**: All ML training data stays on your system (SQLite)
- **SSH Security**: Key-based or password authentication with session management
- **Intelligent Confirmations**: Context-aware warnings for risky operations
- **Privacy Protection**: No command data sent to external services beyond OpenAI
- **API Key Security**: Protected OpenAI integration with rate limiting

## 🧠 ML Quick Start

### Automatic Learning
The ML system starts learning **immediately** - no setup required!

1. **Use Commands**: Every command generates training data
2. **Interact with Warnings**: User decisions improve risk assessment  
3. **System Learns**: ML model automatically adapts to your patterns

### First Training Session
After ~50 command executions:
```bash
curl -X POST http://localhost:8080/ml/train
```

### Check ML Status
```bash
curl http://localhost:8080/ml/status
```

### Export Training Data (Optional)
```python
from ai_shell_agent.modules.command_generation.ml_database_manager import MLDatabaseManager
db = MLDatabaseManager()
db.export_training_data("my_training_data.csv")
```

## 📝 Notes

- **AI Provider**: OpenAI GPT-4o-mini (Bosch internal endpoint)
- **ML Data**: Stored locally in SQLite (`data/ml_risk_database.db`)
- **Privacy**: All learning data stays on your system
- **Performance**: ML training is lightweight and fast
- **Scalability**: Handles thousands of commands efficiently
- To change AI provider, update `ai_shell_agent/modules/*/ai_handler.py`
- See `ML_DATA_FLOW.md` for detailed ML system documentation
