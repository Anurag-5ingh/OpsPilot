# OpsPilot - AI-Powered DevOps Assistant
# Main Flask application serving REST API and WebSocket terminal

# Skip eventlet on Windows as it has compatibility issues
# Use threading mode instead for better Windows compatibility

# Core imports
import os
import json
import time
from flask import Flask, request, jsonify, send_from_directory, render_template, redirect, url_for
from flask_socketio import SocketIO, emit
import paramiko
import threading

# Import OpsPilot modules
from ai_shell_agent.modules.command_generation import ask_ai_for_command, analyze_command_failure
from ai_shell_agent.modules.command_generation.ml_risk_scorer import MLRiskScorer
from ai_shell_agent.modules.security.compliance_checker import SecurityComplianceChecker, ComplianceFramework
from ai_shell_agent.modules.documentation.smart_doc_generator import SmartDocumentationGenerator, DocumentationType, DocumentationFormat
from ai_shell_agent.modules.troubleshooting import ask_ai_for_troubleshoot, TroubleshootWorkflow
from ai_shell_agent.modules.ssh import create_ssh_client, run_shell, ssh_bp
from ai_shell_agent.modules.shared import ConversationMemory
from ai_shell_agent.modules.system_awareness import SystemContextManager

# ===========================
# Application Configuration
# ===========================
app = Flask(__name__)

# Flask secret key for session management
# Can be overridden with APP_SECRET environment variable
app.config['SECRET_KEY'] = os.environ.get("APP_SECRET", "dev_secret_change_me")

# Initialize conversation memory to maintain context across interactions
# Limited to 20 entries for performance optimization
memory = ConversationMemory(max_entries=20)

# Initialize system context manager for server-aware command generation
system_context = SystemContextManager()

# Initialize ML Risk Scorer for continuous learning
ml_scorer = MLRiskScorer()

# Initialize Security Compliance Checker
compliance_checker = SecurityComplianceChecker()
# Enable common compliance frameworks by default
compliance_checker.enable_framework(ComplianceFramework.CIS)
compliance_checker.enable_framework(ComplianceFramework.NIST)
compliance_checker.enable_framework(ComplianceFramework.CUSTOM)

# Initialize Smart Documentation Generator
print("Initializing Smart Documentation Generator...")
doc_generator = SmartDocumentationGenerator()
print("Smart Documentation Generator initialized successfully")

# Register SSH blueprint for SSH connection management endpoints
print("Registering SSH blueprint...")
app.register_blueprint(ssh_bp)
print("SSH blueprint registered successfully")


# ===========================
# Frontend Serving Routes
# ===========================

@app.route("/")
def index():
    """Main route - redirect to OpsPilot interface"""
    return redirect(url_for("serve_index"))

@app.route("/opspilot")
def serve_index():
    """Serve the main OpsPilot web interface"""
    return send_from_directory("frontend", "index.html")

@app.route("/<path:path>")
def serve_static(path):
    """Serve static frontend files (CSS, JS, images)"""
    return send_from_directory("frontend", path)

# ===========================
# Command Generation API
# ===========================

@app.route("/ask", methods=["POST"])
def ask():
    """
    Generate a shell command from natural language input.
    
    Request body:
    {
        "prompt": "natural language request (e.g., 'list all files')"
    }
    
    Returns:
    {
        "ai_command": "generated shell command",
        "original_prompt": "original user input"
    }
    """
    data = request.get_json()
    user_input = data.get("prompt")

    # Validate input
    if not user_input:
        return jsonify({"error": "No prompt provided"}), 400

    # Generate a shell command from natural language using AI with system context
    result = ask_ai_for_command(user_input, memory=memory.get(), system_context=system_context)
    if not result:
        return jsonify({"error": "AI failed to respond"}), 500

    # Extract the generated command from AI response
    ai_response = result.get("ai_response", {})
    command = ai_response.get("final_command")

    if not command:
        return jsonify({"error": "No command generated"}), 400

    # Store the interaction in conversation memory for context
    memory.add(user_input, command)

    return jsonify({
        "ai_command": command,
        "original_prompt": user_input
    })

@app.route("/run", methods=["POST"])
def run_command():
    """
    Execute a shell command on the remote server via SSH.
    
    Request body:
    {
        "host": "remote server hostname/IP",
        "username": "SSH username",
        "password": "SSH password (optional if using keys)",
        "command": "shell command to execute",
        "port": 22 (optional, defaults to 22)
    }
    
    Returns:
    {
        "output": "command output",
        "error": "error output (if any)"
    }
    """
    data = request.get_json()
    host = data.get("host")
    username = data.get("username")
    password = data.get("password")
    command = data.get("command")
    port = data.get("port", 22)

    # Validate required parameters
    if not host or not username or not command:
        return jsonify({"error": "host, username, and command are required"}), 400

    # Create SSH client and execute command
    ssh_client = create_ssh_client(host, username, port, password)
    if ssh_client is None:
        return jsonify({"error": f"SSH connection failed for {username}@{host}"}), 500

    # Execute the command and return results
    output, error = run_shell(command, ssh_client=ssh_client)
    return jsonify({"output": output, "error": error})

@app.route("/analyze-failure", methods=["POST"])
def analyze_failure():
    """
    Analyze a failed command execution and suggest intelligent alternatives.
    
    This endpoint examines why a command failed, provides root cause analysis,
    and suggests system-aware alternative solutions with detailed reasoning.
    
    Request body:
    {
        "original_command": "htop",
        "error_output": "bash: htop: command not found",
        "host": "server hostname/IP (optional for context)",
        "username": "SSH username (optional for context)"
    }
    
    Returns:
    {
        "original_command": "htop",
        "failure_analysis": {
            "categories": ["command_not_found"],
            "root_cause": "The command 'htop' is not installed...",
            "confidence_score": 0.85
        },
        "alternative_solutions": [
            {
                "alternative_command": "sudo apt install htop",
                "reasoning": "Install htop package first",
                "success_probability": 0.8,
                "side_effects": ["Downloads and installs package"]
            }
        ],
        "system_specific_fixes": [...]
    }
    """
    data = request.get_json()
    original_command = data.get("original_command")
    error_output = data.get("error_output")
    host = data.get("host")  # Optional for system context
    username = data.get("username")  # Optional for system context
    
    # Validate required parameters
    if not original_command or not error_output:
        return jsonify({"error": "original_command and error_output are required"}), 400
    
    # Use system context if host info provided (optional enhancement)
    context_to_use = system_context
    if host and username:
        # Could enhance to get specific context for this host
        # For now, use the current system context
        pass
    
    try:
        # Analyze the command failure with intelligent alternatives
        analysis_result = analyze_command_failure(
            original_command, error_output, context_to_use
        )
        
        return jsonify(analysis_result)
        
    except Exception as e:
        return jsonify({
            "error": f"Failure analysis failed: {str(e)}",
            "original_command": original_command
        }), 500

# ===========================
# Troubleshooting API
# ===========================

@app.route("/troubleshoot", methods=["POST"])
def troubleshoot():
    """
    Analyze an error and provide multi-step troubleshooting plan.
    This feature generates diagnostic commands, fix commands, and verification steps.
    
    Request body:
    {
        "error_text": "error message or description",
        "host": "remote host",
        "username": "SSH username",
        "port": 22,
        "context": {
            "last_command": "optional - last command that failed",
            "last_output": "optional - output from last command",
            "last_error": "optional - error from last command"
        }
    }
    
    Returns:
    {
        "analysis": "AI analysis of the error",
        "diagnostic_commands": ["list", "of", "diagnostic", "commands"],
        "fix_commands": ["list", "of", "fix", "commands"],
        "verification_commands": ["list", "of", "verification", "commands"],
        "reasoning": "explanation of the troubleshooting approach",
        "risk_level": "low|medium|high",
        "requires_confirmation": boolean
    }
    """
    data = request.get_json()
    error_text = data.get("error_text")
    host = data.get("host")
    username = data.get("username")
    port = int(data.get("port", 22))
    context = data.get("context", {})
    
    # Validate required parameters
    if not error_text:
        return jsonify({"error": "error_text is required"}), 400
    
    if not host or not username:
        return jsonify({"error": "host and username are required"}), 400
    
    # Get troubleshooting plan from AI with system awareness
    result = ask_ai_for_troubleshoot(error_text, context=context, system_context=system_context)
    
    if not result or not result.get("success"):
        return jsonify({
            "error": "Failed to generate troubleshooting plan",
            "details": (result or {}).get("error", "Unknown error")
        }), 500
    
    # Extract troubleshooting plan components
    troubleshoot_plan = result.get("troubleshoot_response", {})
    
    return jsonify({
        "analysis": troubleshoot_plan.get("analysis"),
        "diagnostic_commands": troubleshoot_plan.get("diagnostic_commands", []),
        "fix_commands": troubleshoot_plan.get("fix_commands", []),
        "verification_commands": troubleshoot_plan.get("verification_commands", []),
        "reasoning": troubleshoot_plan.get("reasoning"),
        "risk_level": troubleshoot_plan.get("risk_level"),
        "requires_confirmation": troubleshoot_plan.get("requires_confirmation")
    })

@app.route("/troubleshoot/execute", methods=["POST"])
def troubleshoot_execute():
    """
    Execute troubleshooting commands (diagnostics, fixes, or verification).
    Uses the TroubleshootWorkflow engine to execute commands with appropriate safety measures.
    
    Request body:
    {
        "commands": ["cmd1", "cmd2", "cmd3"],
        "step_type": "diagnostic|fix|verification",
        "host": "remote host",
        "username": "SSH username",
        "password": "SSH password (optional)",
        "port": 22
    }
    
    Returns:
    {
        "results": [
            {
                "command": "executed command",
                "output": "command output",
                "error": "error output",
                "success": boolean,
                "execution_time": float
            }
        ],
        "all_success": boolean,
        "summary": "execution summary"
    }
    """
    data = request.get_json()
    commands = data.get("commands", [])
    step_type = data.get("step_type", "unknown")
    host = data.get("host")
    username = data.get("username")
    password = data.get("password")
    port = int(data.get("port", 22))
    
    # Validate required parameters
    if not commands:
        return jsonify({"error": "No commands provided"}), 400
    
    if not host or not username:
        return jsonify({"error": "host and username are required"}), 400
    
    # Create SSH client for command execution
    ssh_client = create_ssh_client(host, username, port, password)
    if ssh_client is None:
        return jsonify({"error": f"SSH connection failed for {username}@{host}"}), 500
    
    # Execute commands using the troubleshooting workflow engine
    workflow = TroubleshootWorkflow(ssh_client)
    
    # Choose execution method based on step type
    if step_type == "diagnostic":
        results = workflow.run_diagnostics(commands)
    elif step_type == "fix":
        results = workflow.run_fixes(commands)
    elif step_type == "verification":
        results = workflow.run_verification(commands)
    else:
        # Generic command execution
        results = workflow.execute_commands(commands, step_type)
    
    # Clean up SSH connection
    ssh_client.close()
    
    return jsonify(results)

# ===========================
# ML Risk Scorer API
# ===========================

@app.route("/ml/train", methods=["POST"])
def train_ml_model():
    """
    Train the ML risk scoring model on historical command execution data.
    
    This endpoint triggers training of the machine learning model that improves
    risk assessment accuracy based on user behavior patterns and command outcomes.
    
    Request body:
    {
        "force_retrain": false,
        "min_samples": 50
    }
    
    Returns:
    {
        "success": true,
        "training_result": {
            "metrics": {
                "accuracy": 0.85,
                "precision": 0.82,
                "recall": 0.88,
                "training_samples": 150
            }
        },
        "model_status": "trained"
    }
    """
    data = request.get_json() or {}
    force_retrain = data.get("force_retrain", False)
    min_samples = data.get("min_samples", 50)
    
    try:
        # Check if retraining is needed
        if not force_retrain and not ml_scorer.should_retrain():
            current_metrics = ml_scorer.get_model_performance()
            return jsonify({
                "success": True,
                "message": "Model is already up-to-date",
                "current_metrics": current_metrics,
                "model_status": "current"
            })
        
        # Train the model
        training_result = ml_scorer.train_model(min_samples=min_samples)
        
        if training_result['success']:
            return jsonify({
                "success": True,
                "training_result": training_result,
                "model_status": "trained"
            })
        else:
            return jsonify({
                "success": False,
                "error": training_result.get('error', 'Training failed'),
                "model_status": "failed"
            }), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"ML training failed: {str(e)}",
            "model_status": "error"
        }), 500

@app.route("/ml/feedback", methods=["POST"])
def record_command_feedback():
    """
    Record command execution outcome for continuous ML model improvement.
    
    This endpoint allows the system to learn from actual command outcomes,
    improving risk assessment accuracy over time.
    
    Request body:
    {
        "command": "sudo rm -rf /tmp/*",
        "initial_risk_analysis": {...},
        "user_confirmed": true,
        "execution_success": true,
        "actual_impact": "none|minor|moderate|severe",
        "system_context": {...},
        "user_feedback": "Command worked perfectly" (optional)
    }
    
    Returns:
    {
        "success": true,
        "message": "Feedback recorded successfully"
    }
    """
    data = request.get_json()
    
    required_fields = ['command', 'initial_risk_analysis', 'user_confirmed', 
                      'execution_success', 'actual_impact', 'system_context']
    
    # Validate required fields
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    try:
        # Record the execution outcome
        ml_scorer.record_execution_outcome(
            command=data['command'],
            initial_analysis=data['initial_risk_analysis'],
            user_confirmed=data['user_confirmed'],
            execution_success=data['execution_success'],
            actual_impact=data['actual_impact'],
            system_context=data['system_context'],
            user_feedback=data.get('user_feedback')
        )
        
        return jsonify({
            "success": True,
            "message": "Feedback recorded successfully"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to record feedback: {str(e)}"
        }), 500

@app.route("/ml/status", methods=["GET"])
def get_ml_model_status():
    """
    Get current ML model status and performance metrics.
    
    Returns:
    {
        "model_available": true,
        "performance_metrics": {
            "accuracy": 0.85,
            "precision": 0.82,
            "recall": 0.88,
            "training_date": "2024-01-15T10:30:00",
            "sample_size": 150
        },
        "should_retrain": false,
        "training_data_count": 200
    }
    """
    try:
        # Get current model performance
        metrics = ml_scorer.get_model_performance()
        
        # Check if model exists and is functional
        model_available = ml_scorer.model is not None
        
        # Check if retraining is recommended
        should_retrain = ml_scorer.should_retrain()
        
        # Get training data count
        recent_data = ml_scorer.db.get_training_data(days_back=180)
        training_data_count = len(recent_data)
        
        return jsonify({
            "model_available": model_available,
            "performance_metrics": metrics,
            "should_retrain": should_retrain,
            "training_data_count": training_data_count
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to get ML status: {str(e)}",
            "model_available": False
        }), 500

# ===========================
# Security Compliance API
# ===========================

@app.route("/security/check-compliance", methods=["POST"])
def check_command_compliance():
    """
    Check command compliance against security policies and frameworks.
    
    This endpoint validates commands against enabled compliance frameworks
    like SOX, PCI DSS, CIS, NIST, and custom organizational policies.
    
    Request body:
    {
        "command": "chmod 777 /var/www/html",
        "user_context": {
            "role": "admin",
            "user_id": "john.doe",
            "maintenance_window": false,
            "has_approval": false
        },
        "system_context": {
            "environment": "production",
            "host_info": {...}
        }
    }
    
    Returns:
    {
        "compliant": false,
        "compliance_score": 0.3,
        "violations": [
            {
                "rule_id": "cis_002",
                "framework": "cis",
                "severity": "medium",
                "title": "Secure Configuration Management",
                "description": "Setting overly permissive file permissions",
                "recommendation": "Follow principle of least privilege for file permissions",
                "remediation_commands": ["chmod 755 /var/www/html"]
            }
        ],
        "recommendations": [...],
        "approved_alternatives": [...]
    }
    """
    data = request.get_json()
    command = data.get("command")
    user_context = data.get("user_context", {})
    system_context = data.get("system_context", {})
    
    # Validate required parameters
    if not command:
        return jsonify({"error": "Command is required"}), 400
    
    try:
        # Check command compliance
        compliance_result = compliance_checker.check_command_compliance(
            command, system_context, user_context
        )
        
        return jsonify(compliance_result)
        
    except Exception as e:
        return jsonify({
            "error": f"Compliance check failed: {str(e)}",
            "command": command
        }), 500

@app.route("/security/frameworks", methods=["GET"])
def get_compliance_frameworks():
    """
    Get status of all compliance frameworks.
    
    Returns:
    {
        "enabled_frameworks": ["cis", "nist", "custom"],
        "available_frameworks": ["sox", "pci_dss", "hipaa", "soc2", "gdpr", "cis", "nist", "custom"],
        "total_policies": 12,
        "custom_policies": 0
    }
    """
    try:
        framework_status = compliance_checker.get_framework_status()
        return jsonify(framework_status)
    except Exception as e:
        return jsonify({"error": f"Failed to get framework status: {str(e)}"}), 500

@app.route("/security/frameworks/<framework>", methods=["POST", "DELETE"])
def manage_compliance_framework(framework):
    """
    Enable or disable compliance frameworks.
    
    POST: Enable framework
    DELETE: Disable framework
    
    Returns:
    {
        "success": true,
        "framework": "pci_dss",
        "action": "enabled|disabled"
    }
    """
    try:
        # Validate framework
        try:
            framework_enum = ComplianceFramework(framework)
        except ValueError:
            return jsonify({"error": f"Invalid framework: {framework}"}), 400
        
        if request.method == "POST":
            compliance_checker.enable_framework(framework_enum)
            action = "enabled"
        else:  # DELETE
            compliance_checker.disable_framework(framework_enum)
            action = "disabled"
        
        return jsonify({
            "success": True,
            "framework": framework,
            "action": action
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Framework management failed: {str(e)}",
            "framework": framework
        }), 500

@app.route("/security/record-decision", methods=["POST"])
def record_compliance_decision():
    """
    Record user decision on compliance violation for ML learning.
    
    Request body:
    {
        "violation_id": "cis_002",
        "user_approved": true,
        "user_context": {
            "role": "admin",
            "maintenance_window": true
        },
        "command": "chmod 777 /tmp"
    }
    
    Returns:
    {
        "success": true,
        "message": "Decision recorded for ML learning"
    }
    """
    data = request.get_json()
    violation_id = data.get("violation_id")
    user_approved = data.get("user_approved")
    user_context = data.get("user_context", {})
    command = data.get("command")
    
    # Validate required parameters
    if not violation_id or user_approved is None or not command:
        return jsonify({"error": "violation_id, user_approved, and command are required"}), 400
    
    try:
        compliance_checker.record_user_decision(
            violation_id, user_approved, user_context, command
        )
        
        return jsonify({
            "success": True,
            "message": "Decision recorded for ML learning"
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to record decision: {str(e)}",
            "violation_id": violation_id
        }), 500

# ===========================
# Smart Documentation API
# ===========================

@app.route("/documentation/generate-runbook", methods=["POST"])
def generate_runbook():
    """
    Generate runbook documentation from command execution patterns.
    
    Request body:
    {
        "title": "Database Backup Procedure" (optional),
        "days_back": 30,
        "min_frequency": 3
    }
    
    Returns:
    {
        "success": true,
        "available_patterns": [
            {
                "pattern": "mysqldump -> gzip -> scp",
                "frequency": 5,
                "avg_success_rate": 0.9
            }
        ],
        "generated_runbooks": [
            {
                "id": "runbook_20241016_142030",
                "title": "Procedure: mysqldump → gzip → scp",
                "confidence_score": 0.85
            }
        ]
    }
    """
    data = request.get_json() or {}
    title = data.get("title")
    days_back = data.get("days_back", 30)
    min_frequency = data.get("min_frequency", 3)
    
    try:
        # Identify command patterns
        patterns = doc_generator.pattern_analyzer.identify_command_sequences(days_back=days_back)
        
        if not patterns:
            return jsonify({
                "success": True,
                "available_patterns": [],
                "generated_runbooks": [],
                "message": "No frequent command patterns found"
            })
        
        # Filter patterns by frequency
        frequent_patterns = [p for p in patterns if p['frequency'] >= min_frequency]
        
        # Generate runbooks for frequent patterns
        generated_runbooks = []
        for pattern in frequent_patterns[:5]:  # Limit to top 5 patterns
            runbook = doc_generator.generate_runbook_from_pattern(pattern, title)
            generated_runbooks.append({
                "id": runbook.id,
                "title": runbook.title,
                "confidence_score": runbook.confidence_score
            })
        
        return jsonify({
            "success": True,
            "available_patterns": [
                {
                    "pattern": p["pattern"],
                    "frequency": p["frequency"],
                    "avg_success_rate": p["avg_success_rate"]
                } for p in frequent_patterns
            ],
            "generated_runbooks": generated_runbooks
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Runbook generation failed: {str(e)}"
        }), 500

@app.route("/documentation/generate-troubleshooting", methods=["POST"])
def generate_troubleshooting_guide():
    """
    Generate troubleshooting guide based on historical error patterns.
    
    Request body:
    {
        "error_pattern": "command_not_found",
        "title": "Command Not Found Troubleshooting" (optional)
    }
    
    Returns:
    {
        "success": true,
        "guide_id": "troubleshoot_command_not_found_20241016_142030",
        "title": "Troubleshooting: Command Not Found",
        "confidence_score": 0.75,
        "step_count": 8
    }
    """
    data = request.get_json()
    error_pattern = data.get("error_pattern")
    title = data.get("title")
    
    # Validate required parameters
    if not error_pattern:
        return jsonify({"error": "error_pattern is required"}), 400
    
    try:
        # Generate troubleshooting guide
        guide = doc_generator.generate_troubleshooting_guide(error_pattern, title)
        
        return jsonify({
            "success": True,
            "guide_id": guide.id,
            "title": guide.title,
            "confidence_score": guide.confidence_score,
            "step_count": len(guide.steps)
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Troubleshooting guide generation failed: {str(e)}",
            "error_pattern": error_pattern
        }), 500

@app.route("/documentation/generate-reference", methods=["POST"])
def generate_command_reference():
    """
    Generate command reference documentation based on usage patterns.
    
    Request body:
    {
        "command_pattern": "docker",
        "title": "Docker Command Reference" (optional)
    }
    
    Returns:
    {
        "success": true,
        "reference_id": "cmdref_docker_20241016_142030",
        "title": "docker Command Reference",
        "confidence_score": 0.82,
        "usage_examples": 5
    }
    """
    data = request.get_json()
    command_pattern = data.get("command_pattern")
    title = data.get("title")
    
    # Validate required parameters
    if not command_pattern:
        return jsonify({"error": "command_pattern is required"}), 400
    
    try:
        # Generate command reference
        reference = doc_generator.generate_command_reference(command_pattern, title)
        
        return jsonify({
            "success": True,
            "reference_id": reference.id,
            "title": reference.title,
            "confidence_score": reference.confidence_score,
            "usage_examples": len(reference.steps)
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Command reference generation failed: {str(e)}",
            "command_pattern": command_pattern
        }), 500

@app.route("/documentation/<doc_id>", methods=["GET"])
def get_documentation(doc_id):
    """
    Retrieve generated documentation by ID.
    
    Query parameters:
    - format: markdown|json|html|plain_text (default: markdown)
    
    Returns documentation in specified format.
    """
    format_param = request.args.get("format", "markdown")
    
    try:
        # Validate format
        try:
            doc_format = DocumentationFormat(format_param)
        except ValueError:
            return jsonify({"error": f"Invalid format: {format_param}"}), 400
        
        # Get documentation
        doc = doc_generator.get_generated_documentation(doc_id)
        if not doc:
            return jsonify({"error": f"Documentation not found: {doc_id}"}), 404
        
        # Format documentation
        formatted_doc = doc_generator.format_documentation(doc, doc_format)
        
        # Set appropriate content type
        if doc_format == DocumentationFormat.JSON:
            return jsonify(json.loads(formatted_doc))
        elif doc_format == DocumentationFormat.HTML:
            return formatted_doc, 200, {'Content-Type': 'text/html'}
        else:
            return formatted_doc, 200, {'Content-Type': 'text/plain'}
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to retrieve documentation: {str(e)}",
            "doc_id": doc_id
        }), 500

@app.route("/documentation/list", methods=["GET"])
def list_documentation():
    """
    List all generated documentation with metadata.
    
    Returns:
    {
        "success": true,
        "documentation": [
            {
                "id": "runbook_20241016_142030",
                "title": "Database Backup Procedure",
                "type": "runbook",
                "generated_at": "2024-10-16T14:20:30",
                "confidence_score": 0.85
            }
        ],
        "total_count": 1
    }
    """
    try:
        docs = doc_generator.list_generated_documentation()
        
        return jsonify({
            "success": True,
            "documentation": docs,
            "total_count": len(docs)
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to list documentation: {str(e)}"
        }), 500

# ===========================
# System Awareness API
# ===========================

@app.route("/profile", methods=["POST"])
def profile_server():
    """
    Profile a server to understand its capabilities and configuration.
    
    This endpoint analyzes the target server to detect:
    - Operating system and version
    - Available package managers (apt, yum, dnf, apk, etc.)
    - Service manager (systemd, sysvinit, openrc)
    - Installed software and tools
    - Security context (sudo availability, firewall)
    
    Request body:
    {
        "host": "server hostname/IP",
        "username": "SSH username",
        "password": "SSH password (optional)",
        "port": 22,
        "force_refresh": false
    }
    
    Returns:
    {
        "success": true,
        "profile": {
            "os_info": {"distribution": "ubuntu", "version": "20.04"},
            "package_managers": ["apt"],
            "service_manager": "systemd",
            "installed_software": {...},
            "capabilities": [...],
            "confidence_score": 0.85
        },
        "summary": "OS: Ubuntu 20.04 | Package Manager: apt | Service Manager: systemd"
    }
    """
    data = request.get_json()
    host = data.get("host")
    username = data.get("username")
    password = data.get("password")
    port = int(data.get("port", 22))
    force_refresh = data.get("force_refresh", False)
    
    # Validate required parameters
    if not host or not username:
        return jsonify({"error": "host and username are required"}), 400
    
    # Create SSH client for server profiling
    ssh_client = create_ssh_client(host, username, port, password)
    if ssh_client is None:
        return jsonify({"error": f"SSH connection failed for {username}@{host}"}), 500
    
    try:
        # Initialize system context with this connection
        profile = system_context.initialize_context(ssh_client, host, force_refresh)
        
        return jsonify({
            "success": True,
            "profile": profile,
            "summary": system_context.get_system_summary()
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Server profiling failed: {str(e)}"
        }), 500
    finally:
        ssh_client.close()

@app.route("/profile/summary", methods=["GET"])
def get_profile_summary():
    """
    Get a summary of the currently active server profile.
    
    Returns:
    {
        "summary": "OS: Ubuntu 20.04 | Package Manager: apt | Service Manager: systemd",
        "has_profile": true,
        "confidence": 0.85
    }
    """
    summary = system_context.get_system_summary()
    profile = system_context.get_current_profile()
    
    return jsonify({
        "summary": summary,
        "has_profile": profile is not None,
        "confidence": profile.get("confidence_score", 0) if profile else 0
    })

@app.route("/profile/suggestions/<category>", methods=["GET"])
def get_command_suggestions(category):
    """
    Get server-specific command suggestions for a category.
    
    Categories: 'package', 'service', 'network', 'monitoring'
    
    Returns:
    {
        "category": "package",
        "suggestions": [
            "sudo apt update && sudo apt upgrade",
            "apt search <package>",
            "sudo apt install <package>"
        ],
        "server_aware": true
    }
    """
    suggestions = system_context.get_command_suggestions(category)
    
    return jsonify({
        "category": category,
        "suggestions": suggestions,
        "server_aware": system_context.get_current_profile() is not None
    })

# ===========================
# WebSocket Terminal Support
# ===========================

# Initialize SocketIO for real-time terminal communication
# Use threading mode for better Windows compatibility
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Add CORS headers for all routes
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Dictionary to store active SSH sessions by session ID
ssh_sessions = {}

# @app.route("/terminal")
# def terminal():
#     """
#     Serve terminal interface (legacy route with hardcoded values).
#     Note: This route contains hardcoded connection details and should be updated
#     to use dynamic parameters or removed if not needed.
#     """
#     # TODO: Remove hardcoded values or make this route dynamic
#     ip = "10.4.5.70" 
#     user = "root"
#     password = ""
#     return render_template("terminal.html", ip=ip, user=user, password=password)

def _reader_thread(sid: str):
    """
    Background thread to read SSH output and send to WebSocket client.
    
    Args:
        sid (str): Socket.IO session ID
    """
    session = ssh_sessions.get(sid)
    
    if not session:
        return
    
    chan = session["chan"]
    
    try:
        while True:
            # Check if channel is closed or session was removed
            if chan.closed or sid not in ssh_sessions:
                break
            
            # Read stdout data if available
            if chan.recv_ready():
                data = chan.recv(4096).decode(errors="ignore")
                socketio.emit("terminal_output", {"output": data}, room=sid)
            
            # Read stderr data if available
            if chan.recv_stderr_ready():
                data = chan.recv_stderr(4096).decode(errors="ignore")
                socketio.emit("terminal_output", {"output": data}, room=sid)
            
            # Small delay to prevent CPU spinning
            time.sleep(0.01)
            
    except Exception as e:
        # Send error message to client
        socketio.emit("terminal_output", {"output": f"\r\n[reader error] {e}\r\n"}, room=sid)
    finally:
        # Clean up session on thread exit
        session = ssh_sessions.pop(sid, None)
        if session:
            try: 
                session["chan"].close()
            except Exception: 
                pass
            try: 
                session["client"].close()
            except Exception: 
                pass

@socketio.on("start_ssh")
def start_ssh(data):
    """
    Initialize SSH connection for WebSocket terminal.
    
    Expected data:
    {
        "ip": "server IP/hostname",
        "user": "SSH username", 
        "password": "SSH password (optional)",
        "profileId": "connection profile ID (optional)"
    }
    """
    sid = request.sid
    profile_id = (data or {}).get("profileId")
    ip = (data or {}).get("ip")
    user = (data or {}).get("user")
    password = (data or {}).get("password", "")
    
    # Close existing session if any
    old = ssh_sessions.pop(sid, None)
    if old:
        try: 
            old["chan"].close()
        except Exception: 
            pass
        try: 
            old["client"].close()
        except Exception: 
            pass
    
    try:
        client = None
        
        # Try profile-based connection first if enhanced SSH is enabled
        if profile_id and os.getenv('OSPILOT_SSH_ENHANCED', 'true').lower() == 'true':
            try:
                from ai_shell_agent.modules.ssh.session_manager import _get_profile_by_id
                from ai_shell_agent.modules.ssh.client import connect_with_profile
                
                profile = _get_profile_by_id(profile_id)
                if profile:
                    # Host key callback for WebSocket
                    def hostkey_callback(hostname, key_type, fingerprint):
                        emit("hostkey_unknown", {
                            "hostname": hostname,
                            "key_type": key_type,
                            "fingerprint": fingerprint
                        })
                        # For now, auto-accept (can be enhanced with user interaction)
                        return True
                    
                    # Auth prompt callback for WebSocket
                    def auth_callback(title, instructions, prompts):
                        emit("auth_prompt", {
                            "title": title,
                            "instructions": instructions,
                            "prompts": prompts
                        })
                        # For now, return empty (can be enhanced with user interaction)
                        return []
                    
                    client = connect_with_profile(
                        profile,
                        on_auth_prompt=auth_callback,
                        on_hostkey_decision=hostkey_callback
                    )
                    
                    if client:
                        ip = profile['host']
                        user = profile['username']
                else:
                    emit("terminal_output", {"output": f"\r\nProfile {profile_id} not found.\r\n"})
                    return
            except Exception as e:
                emit("terminal_output", {"output": f"\r\nProfile connection failed: {e}\r\n"})
                # Fall through to legacy connection
        
        # Fallback to legacy connection
        if client is None:
            # Validate required parameters for legacy mode
            if not ip or not user:
                emit("terminal_output", {"output": "\r\nMissing IP/Username or valid profile.\r\n"})
                return
            
            # Create legacy SSH client
            client = paramiko.SSHClient()
            
            # Use enhanced host key policy if available
            if os.getenv('OSPILOT_SSH_ENHANCED', 'true').lower() == 'true':
                try:
                    from ai_shell_agent.modules.ssh.hostkeys import host_key_manager
                    policy = host_key_manager.create_policy(strict_mode="no")
                    client.set_missing_host_key_policy(policy)
                except ImportError:
                    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            else:
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect with appropriate authentication method
            client.connect(
                hostname=str(ip),
                username=str(user),
                password=password if password else None,
                look_for_keys=not password,  # Only use keys if password not provided
                allow_agent=not password,    # Allow agent if no password
                timeout=10
            )
        
        # Create interactive shell channel
        chan = client.invoke_shell(term="xterm")
        chan.settimeout(0.0)
        
        # Store session and start reader thread
        ssh_sessions[sid] = {"client": client, "chan": chan}
        threading.Thread(target=_reader_thread, args=(sid,), daemon=True).start()
        
        emit("terminal_output", {"output": f"Connected to {ip} as {user}\r\n"})
        
    except Exception as e:
        emit("terminal_output", {"output": f"\r\nSSH Connection Failed: {e}\r\n"})

@socketio.on("terminal_input")
def handle_terminal_input(data):
    """
    Handle keyboard input from WebSocket terminal client.
    
    Expected data:
    {
        "input": "text to send to terminal"
    }
    """
    sid = request.sid
    session = ssh_sessions.get(sid)
    
    if not session:
        emit("terminal_output", {"output": "\r\n[Error] No SSH session. Refresh and try again.\r\n"})
        return
    
    try:
        text = (data or {}).get("input", "")
        if text:
            session["chan"].send(text)
    except Exception as e:
        emit("terminal_output", {"output": f"\r\n[send error] {e}\r\n"})

@socketio.on("resize")
def handle_resize(data):
    """
    Handle terminal resize events from client.
    
    Expected data:
    {
        "cols": terminal_columns,
        "rows": terminal_rows
    }
    """
    sid = request.sid
    session = ssh_sessions.get(sid)
    
    if not session:
        return
    
    try:
        cols = int((data or {}).get("cols", 80))
        rows = int((data or {}).get("rows", 24))
        session["chan"].resize_pty(width=cols, height=rows)
    except Exception:
        pass

@socketio.on("disconnect")
def on_disconnect():
    """
    Clean up SSH session when WebSocket client disconnects.
    """
    sid = request.sid
    session = ssh_sessions.pop(sid, None)
    
    if session:
        try: 
            session["chan"].close()
        except Exception: 
            pass
        try: 
            session["client"].close()
        except Exception: 
            pass

# ===========================
# Application Entry Point
# ===========================

if __name__ == "__main__":
    # Get port from environment variable or default to 8080
    port = int(os.environ.get("PORT", 8080))
    
    print(f"Starting OpsPilot server on port {port}...")
    # Run the Flask application with SocketIO support
    # Use threading mode for Windows compatibility
    socketio.run(app, host="0.0.0.0", port=port, debug=False, use_reloader=False)
