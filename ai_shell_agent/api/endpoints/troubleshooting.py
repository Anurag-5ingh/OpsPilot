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
    try:
        data = request.get_json()
        if not data:
            logger.error("No JSON data received")
            return jsonify({"error": "No JSON data received"}), 400
            
        error_text = data.get("error_text")
        if not error_text:
            logger.error("error_text field is required")
            return jsonify({"error": "error_text is required"}), 400
        
        logger.info(f"Analyzing error: {error_text[:100]}...")
        analysis = engine.analyze_error(error_text)
        logger.info("Analysis completed successfully")
        
        return jsonify({
            "success": True,
            "analysis": analysis.get("analysis", "Analysis completed"),
            "diagnostic_commands": analysis.get("diagnostic_commands", []),
            "risk_level": "low",  # Add risk level for UI compatibility
            "reasoning": "AI-based error analysis"  # Add reasoning for UI compatibility
        })
        
    except Exception as e:
        logger.error(f"Error analyzing troubleshooting request: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"Analysis failed: {str(e)}",
            "diagnostic_commands": []
        }), 500

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