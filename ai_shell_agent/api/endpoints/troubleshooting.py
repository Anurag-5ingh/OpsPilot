"""
Troubleshooting endpoints for analyzing and fixing server issues.
"""

from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import logging
from ai_shell_agent.modules.troubleshooting.engine import TroubleshootingEngine

# Initialize logger
logger = logging.getLogger(__name__)

# Create blueprint
troubleshooting_bp = Blueprint('troubleshooting', __name__)

# Initialize troubleshooting engine
engine = TroubleshootingEngine()

@troubleshooting_bp.route("/analyze", methods=["POST"])
@cross_origin()
def analyze_error():
    """Analyze error text and suggest diagnostic commands"""
    data = request.get_json()
    error_text = data.get("error_text")
    
    if not error_text:
        return jsonify({"error": "error_text is required"}), 400
    
    try:
        # Get analysis and diagnostic commands
        analysis = engine.analyze_error(error_text)
        return jsonify(analysis)
        
    except Exception as e:
        logger.error(f"Error analyzing troubleshooting request: {e}")
        return jsonify({"error": str(e)}), 500

@troubleshooting_bp.route("/suggest-fix", methods=["POST"])
@cross_origin() 
def suggest_fix():
    """Analyze diagnostic results and suggest fixes"""
    data = request.get_json()
    diagnostic_results = data.get("diagnostic_results")
    
    if not diagnostic_results:
        return jsonify({"error": "diagnostic_results are required"}), 400
    
    try:
        # Get fix suggestions
        fixes = engine.analyze_diagnostic_output(diagnostic_results)
        return jsonify(fixes)
        
    except Exception as e:
        logger.error(f"Error generating fix suggestions: {e}")
        return jsonify({"error": str(e)}), 500

@troubleshooting_bp.route("/verify", methods=["POST"])
@cross_origin()
def verify_fix():
    """Get verification commands"""
    data = request.get_json()
    host = data.get("host")
    username = data.get("username") 
    
    if not host or not username:
        return jsonify({"error": "host and username required"}), 400
    
    # For now return generic verification commands
    # This could be enhanced with system-specific checks
    return jsonify({
        "verification_commands": [
            "systemctl status nginx",
            "curl localhost"
        ]
    })