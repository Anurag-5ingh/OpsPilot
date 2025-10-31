"""
Troubleshooting endpoints for analyzing and fixing server issues.
"""

from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import logging
from ai_shell_agent.modules.troubleshooting.engine import TroubleshootingEngine
try:
    # Prefer the AI handler which returns a full troubleshooting structure
    from ai_shell_agent.modules.troubleshooting.ai_handler import ask_ai_for_troubleshoot
except Exception:
    ask_ai_for_troubleshoot = None

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

        # If AI handler is available, prefer it so we can return fixes and verification commands
        if ask_ai_for_troubleshoot:
            try:
                ai_result = ask_ai_for_troubleshoot(error_text)
                if ai_result and ai_result.get("success"):
                    tr = ai_result.get("troubleshoot_response", {})
                    logger.info("AI troubleshooting analysis completed successfully")
                    return jsonify({
                        "success": True,
                        "analysis": tr.get("analysis", "Analysis completed"),
                        "diagnostic_commands": tr.get("diagnostic_commands", []),
                        "fix_commands": tr.get("fix_commands", []),
                        "verification_commands": tr.get("verification_commands", []),
                        "risk_level": tr.get("risk_level", "medium"),
                        "reasoning": tr.get("reasoning", ""),
                    })
                else:
                    logger.warning("AI troubleshooting handler returned no usable response, falling back to engine")
            except Exception as e:
                logger.exception(f"AI handler failed: {e}. Falling back to engine.")

        # Fallback to simple engine analysis (diagnostic only)
        analysis = engine.analyze_error(error_text)
        logger.info("Engine analysis completed (fallback)")

        return jsonify({
            "success": True,
            "analysis": analysis.get("analysis", "Analysis completed"),
            "diagnostic_commands": analysis.get("diagnostic_commands", []),
            "fix_commands": [],
            "verification_commands": [],
            "risk_level": "low",
            "reasoning": "Fallback analysis (no AI)"
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
        # Prefer AI handler for richer suggestions when available
        if ask_ai_for_troubleshoot:
            try:
                ai_result = ask_ai_for_troubleshoot('', context={"diagnostic_results": diagnostic_results})
                if ai_result and ai_result.get("success"):
                    tr = ai_result.get("troubleshoot_response", {})
                    normalized = {
                        "fix_commands": tr.get("fix_commands", []),
                        "verification_commands": tr.get("verification_commands", []),
                        "reasoning": tr.get("reasoning", ""),
                        "risk_level": tr.get("risk_level", "medium")
                    }
                    return jsonify(normalized)
                else:
                    logger.warning("AI suggest-fix returned no usable response, falling back to engine")
            except Exception as e:
                logger.exception(f"AI suggest-fix handler failed: {e}. Falling back to engine.")

        # Fallback: Get fix suggestions from the engine
        fixes = engine.analyze_diagnostic_output(diagnostic_results)
        normalized = {
            "fix_commands": fixes.get("fix_commands", []) if isinstance(fixes, dict) else [],
            "verification_commands": fixes.get("verification_commands", []) if isinstance(fixes, dict) else [],
            "reasoning": fixes.get("reasoning", "") if isinstance(fixes, dict) else "",
            "risk_level": fixes.get("risk_level", "medium") if isinstance(fixes, dict) else "medium"
        }
        return jsonify(normalized)
        
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