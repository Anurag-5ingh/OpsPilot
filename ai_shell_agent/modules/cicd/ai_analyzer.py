"""
AI Log Analyzer Service

Analyzes Jenkins build logs using AI to identify errors, root causes, 
and generate suggested fix commands for automated troubleshooting.
"""

import logging
import re
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone

from ..command_generation import ask_ai_for_command
from ..shared import ConversationMemory
from ..system_awareness import SystemContextManager
from .models import BuildLog, FixHistory
from .jenkins_service import JenkinsService
from .ansible_service import AnsibleService

logger = logging.getLogger(__name__)


class AILogAnalyzer:
    """Service for analyzing build logs and generating fix suggestions using AI."""
    
    def __init__(self, memory: ConversationMemory = None, system_context: SystemContextManager = None):
        self.memory = memory or ConversationMemory(max_entries=10)
        self.system_context = system_context or SystemContextManager()
        
        # Common error patterns for faster initial analysis
        self.error_patterns = {
            'package_not_found': [
                r'package .+ is not available',
                r'No package .+ available',
                r'Unable to locate package',
                r'package .+ not found'
            ],
            'service_failed': [
                r'Failed to (start|stop|restart) .+\.service',
                r'systemctl .+ failed',
                r'service .+ failed',
                r'Unit .+ failed to start'
            ],
            'permission_denied': [
                r'Permission denied',
                r'Access denied',
                r'cannot access .+: Permission denied',
                r'Operation not permitted'
            ],
            'connection_failed': [
                r'Connection refused',
                r'No route to host',
                r'Connection timed out',
                r'Network is unreachable',
                r'ssh: connect to host .+ failed'
            ],
            'disk_space': [
                r'No space left on device',
                r'Disk full',
                r'not enough space',
                r'insufficient disk space'
            ],
            'command_not_found': [
                r'command not found',
                r'No such file or directory',
                r'not found in PATH',
                r'executable not found'
            ],
            'syntax_error': [
                r'syntax error',
                r'invalid syntax',
                r'parse error',
                r'malformed'
            ],
            'ansible_error': [
                r'TASK \[.+\] \*+\nfatal:',
                r'FAILED! =>', 
                r'unreachable=\d+',
                r'fatal: \[.+\]: FAILED!',
                r'ERROR! .+'
            ]
        }
    
    def analyze_build_failure(self, build_log: BuildLog, jenkins_service: Optional[JenkinsService] = None,
                             ansible_service: Optional[AnsibleService] = None) -> Dict[str, Any]:
        """
        Analyze a failed build and generate fix suggestions.
        
        Args:
            build_log: BuildLog instance for the failed build
            jenkins_service: Optional Jenkins service for fetching logs
            ansible_service: Optional Ansible service for playbook suggestions
            
        Returns:
            Dictionary with analysis results and fix suggestions
        """
        logger.info(f"Starting analysis of build failure: {build_log.job_name}#{build_log.build_number} (Status: {build_log.status})")
        
        if build_log.status not in ['FAILURE', 'ABORTED', 'UNSTABLE']:
            error_msg = f'Build status is {build_log.status}, not a failure'
            logger.warning(f"Skipping analysis: {error_msg}")
            return {
                'success': False,
                'error': error_msg
            }
        
        try:
            # Get console logs
            logger.debug(f"Fetching console logs for analysis (last 200 lines)")
            console_log = ""
            if jenkins_service:
                console_log = jenkins_service.get_console_log_tail(
                    build_log.job_name, 
                    build_log.build_number, 
                    lines=200  # Get last 200 lines for analysis
                )
                logger.info(f"Retrieved {len(console_log)} characters of console log")
            else:
                logger.warning("No Jenkins service provided for log fetching")
            
            if not console_log:
                logger.warning(f"No console log available for {build_log.job_name}#{build_log.build_number}")
                console_log = "No console log available"
            
            # Perform initial pattern-based analysis
            quick_analysis = self._quick_error_analysis(console_log)
            
            # Use AI for deeper analysis
            ai_analysis = self._ai_analyze_logs(
                job_name=build_log.job_name,
                build_number=build_log.build_number,
                console_log=console_log,
                target_server=build_log.target_server,
                quick_analysis=quick_analysis
            )
            
            # Generate fix suggestions
            fix_suggestions = self._generate_fix_suggestions(
                ai_analysis, 
                build_log, 
                console_log, 
                ansible_service
            )
            
            result = {
                'success': True,
                'build_id': build_log.id,
                'job_name': build_log.job_name,
                'build_number': build_log.build_number,
                'target_server': build_log.target_server,
                'error_summary': ai_analysis.get('error_summary', 'Build failed'),
                'root_cause': ai_analysis.get('root_cause', 'Unable to determine root cause'),
                'error_categories': quick_analysis.get('categories', []),
                'suggested_commands': fix_suggestions.get('commands', []),
                'suggested_playbook': fix_suggestions.get('playbook'),
                'confidence_score': ai_analysis.get('confidence_score', 0.5),
                'requires_confirmation': True,  # Always require confirmation for safety
                'analysis_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze build failure: {e}")
            return {
                'success': False,
                'error': f'Analysis failed: {str(e)}',
                'build_id': build_log.id
            }
    
    def _quick_error_analysis(self, console_log: str) -> Dict[str, Any]:
        """Perform quick pattern-based error analysis."""
        found_patterns = []
        error_lines = []
        
        lines = console_log.split('\n')
        
        # Look for error patterns
        for category, patterns in self.error_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, console_log, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    if category not in found_patterns:
                        found_patterns.append(category)
                    
                    # Find the line containing this error
                    error_line = self._find_error_line(lines, match.start(), console_log)
                    if error_line and error_line not in error_lines:
                        error_lines.append(error_line)
        
        # Look for common failure indicators
        failure_indicators = [
            'FATAL:', 'ERROR:', 'FAILED:', 'FAILURE:', 
            'fatal:', 'error:', 'failed:', 'failure:',
            'TASK [', 'unreachable=', 'changed='
        ]
        
        for line in lines[-50:]:  # Check last 50 lines
            line_lower = line.lower()
            for indicator in failure_indicators:
                if indicator.lower() in line_lower and line.strip() not in error_lines:
                    error_lines.append(line.strip())
                    break
        
        return {
            'categories': found_patterns,
            'error_lines': error_lines[:10],  # Limit to top 10 error lines
            'total_lines': len(lines)
        }
    
    def _find_error_line(self, lines: List[str], match_start: int, full_text: str) -> str:
        """Find the specific line containing an error match."""
        try:
            # Calculate which line the match is in
            text_up_to_match = full_text[:match_start]
            line_number = text_up_to_match.count('\n')
            
            if 0 <= line_number < len(lines):
                return lines[line_number].strip()
        except Exception:
            pass
        return ""
    
    def _ai_analyze_logs(self, job_name: str, build_number: int, console_log: str,
                        target_server: Optional[str], quick_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Use AI to analyze build logs and identify root causes."""
        try:
            analysis_prompt = self._build_analysis_prompt(
                job_name, build_number, console_log, target_server, quick_analysis
            )

            # Use existing AI command generation with system context
            ai_result = ask_ai_for_command(
                analysis_prompt,
                memory=self.memory.get(),
                system_context=self.system_context,
            )
            
            if not ai_result or not ai_result.get('success'):
                logger.warning("AI analysis failed, using fallback analysis")
                return self._fallback_analysis(quick_analysis, console_log)
            
            ai_response = ai_result.get('ai_response', {})
            analysis_text = ai_response.get('final_command', '') or ai_response.get('response', '')

            # Prefer structured JSON if the model provided it
            parsed_analysis = None
            try:
                json_blob = self._extract_json_blob(analysis_text)
                if json_blob:
                    data = json.loads(json_blob)
                    # Normalize expected keys
                    parsed_analysis = {
                        'error_summary': data.get('error_summary') or data.get('summary') or '',
                        'root_cause': data.get('root_cause') or data.get('cause') or '',
                        'confidence_score': float(data.get('confidence', data.get('confidence_score', 0.7))),
                        'priority': (data.get('priority') or 'medium').lower(),
                        'full_analysis': data.get('full_analysis') or analysis_text,
                        # Helpful extras for future use
                        'primary_error_line': data.get('primary_error_line'),
                        'primary_error_excerpt': data.get('primary_error_excerpt'),
                        'evidence': data.get('evidence') or [],
                        'error_type': data.get('error_type')
                    }
            except Exception as e:
                logger.debug(f"Failed to parse structured JSON from AI response: {e}")

            if not parsed_analysis:
                # Fallback to legacy parser (pattern-based extraction from free text)
                parsed_analysis = self._parse_ai_analysis(analysis_text, quick_analysis)
            
            # Store in conversation memory for context
            self.memory.add(f"Build failure analysis for {job_name}#{build_number}", analysis_text)
            
            return parsed_analysis
            
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return self._fallback_analysis(quick_analysis, console_log)
    
    def _parse_ai_analysis(self, analysis_text: str, quick_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Parse AI analysis response into structured data."""
        try:
            # Extract key information using patterns
            summary_match = re.search(r'(?:error summary|summary)[:\-]\s*(.+?)(?:\n|$)', analysis_text, re.IGNORECASE)
            cause_match = re.search(r'(?:root cause|cause)[:\-]\s*(.+?)(?:\n|$)', analysis_text, re.IGNORECASE)
            confidence_match = re.search(r'(?:confidence|score)[:\-]?\s*([0-9.]+)', analysis_text, re.IGNORECASE)
            priority_match = re.search(r'(?:priority)[:\-]?\s*(low|medium|high)', analysis_text, re.IGNORECASE)
            
            return {
                'error_summary': (summary_match.group(1).strip() if summary_match else 
                                'Build failed with multiple errors'),
                'root_cause': (cause_match.group(1).strip() if cause_match else 
                              'Unable to determine specific root cause'),
                'confidence_score': float(confidence_match.group(1)) if confidence_match else 0.7,
                'priority': priority_match.group(1).lower() if priority_match else 'medium',
                'full_analysis': analysis_text
            }
            
        except Exception as e:
            logger.error(f"Failed to parse AI analysis: {e}")
            return self._fallback_analysis(quick_analysis, "")

    def _build_analysis_prompt(self, job_name: str, build_number: int, console_log: str,
                               target_server: Optional[str], quick_analysis: Dict[str, Any]) -> str:
        """Build the AI prompt for analyzing Jenkins build logs (JSON output requested)."""
        # Provide both last N lines and last chars to give context without sending entire log
        lines = console_log.split('\n')
        last_tail_lines = '\n'.join(lines[-200:]) if len(lines) > 200 else '\n'.join(lines)
        last_chars = console_log[-3000:] if len(console_log) > 3000 else console_log

        error_context = (
            f"Jenkins Job: {job_name}#{build_number}\n"
            f"Target Server: {target_server or 'Unknown'}\n"
            f"Error Categories Found: {', '.join(quick_analysis.get('categories', []))}\n"
            "Key Error Lines (heuristic):\n"
            f"{chr(10).join(quick_analysis.get('error_lines', [])[:5])}\n\n"
            "Console Log (tail, last ~200 lines):\n"
            f"{last_tail_lines}\n\n"
            "Console Log (last ~3000 chars for extra context):\n"
            f"{last_chars}\n"
        )

        analysis_prompt = (
            "You are analyzing a Jenkins build failure. Identify the SINGLE most probable failing error that actually caused the build to fail.\n"
            "Disregard subsequent cascading errors. Prefer the first terminal failure near the end of the log (e.g., Ansible fatal, non-zero exit, test failure, missing dependency).\n\n"
            f"{error_context}\n"
            "Respond ONLY with strict JSON (no markdown, no prose) in the following schema:\n"
            "{\n"
            "  \"error_summary\": string,\n"
            "  \"root_cause\": string,\n"
            "  \"confidence\": number (0.0-1.0),\n"
            "  \"priority\": \"low\"|\"medium\"|\"high\",\n"
            "  \"primary_error_line\": number | null,\n"
            "  \"primary_error_excerpt\": string,\n"
            "  \"evidence\": [{\"line\": number, \"text\": string}] ,\n"
            "  \"error_type\": string\n"
            "}\n\n"
            "Constraints:\n"
            "- Choose exactly one primary_error_* corresponding to the trigger line that failed the build.\n"
            "- If line numbers are unknown, set primary_error_line to null but include an excerpt.\n"
            "- Keep error_summary concise (1-2 sentences).\n"
            "- Root cause must be specific and actionable.\n"
        )

        return analysis_prompt

    def _extract_json_blob(self, text: str) -> Optional[str]:
        """Extract the first JSON object string from text, if present."""
        if not text:
            return None
        try:
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1 and end > start:
                candidate = text[start:end+1].strip()
                # Quick validation
                json.loads(candidate)
                return candidate
        except Exception:
            return None
        return None
    
    def _fallback_analysis(self, quick_analysis: Dict[str, Any], console_log: str) -> Dict[str, Any]:
        """Provide fallback analysis when AI fails."""
        categories = quick_analysis.get('categories', [])
        error_lines = quick_analysis.get('error_lines', [])
        
        # Generate basic summary from categories
        if categories:
            category_text = ', '.join(categories).replace('_', ' ')
            error_summary = f"Build failed due to: {category_text}"
        else:
            error_summary = "Build failed - check console logs for details"
        
        # Basic root cause from patterns
        root_cause = "Multiple issues detected"
        if 'package_not_found' in categories:
            root_cause = "Required package not available or not found"
        elif 'service_failed' in categories:
            root_cause = "System service failed to start or restart"
        elif 'permission_denied' in categories:
            root_cause = "Insufficient permissions for required operations"
        elif 'connection_failed' in categories:
            root_cause = "Network connection issues or unreachable host"
        elif 'ansible_error' in categories:
            root_cause = "Ansible playbook execution failed"
        
        return {
            'error_summary': error_summary,
            'root_cause': root_cause,
            'confidence_score': 0.6,
            'priority': 'medium',
            'full_analysis': f"Pattern-based analysis found: {', '.join(categories)}"
        }
    
    def _generate_fix_suggestions(self, ai_analysis: Dict[str, Any], build_log: BuildLog,
                                 console_log: str, ansible_service: Optional[AnsibleService]) -> Dict[str, Any]:
        """Generate fix command suggestions based on analysis."""
        try:
            error_summary = ai_analysis.get('error_summary', '')
            root_cause = ai_analysis.get('root_cause', '')
            # Get command suggestions from AI
            command_result = self._ask_for_fix_commands(
                build_log, error_summary, root_cause
            )

            suggested_commands = self._parse_command_suggestions(command_result)
            
            # Fallback command suggestions based on error categories
            if not suggested_commands:
                suggested_commands = self._generate_fallback_commands(ai_analysis, console_log)
            
            # Look for relevant Ansible playbook
            suggested_playbook = None
            if ansible_service and build_log.target_server:
                suggested_playbook = ansible_service.suggest_fix_playbook(
                    error_summary, 
                    build_log.target_server
                )
            
            return {
                'commands': suggested_commands[:5],  # Limit to 5 commands for safety
                'playbook': suggested_playbook
            }
            
        except Exception as e:
            logger.error(f"Failed to generate fix suggestions: {e}")
            return {
                'commands': ['echo "Manual troubleshooting required - check build logs"'],
                'playbook': None
            }

    def _ask_for_fix_commands(self, build_log: BuildLog, error_summary: str, root_cause: str) -> Dict[str, Any]:
        """Invoke AI to get command suggestions for fixing the build issue."""
        fix_prompt = f"""
Based on this Jenkins build failure analysis, suggest specific shell commands to fix the issue:

Job: {build_log.job_name}#{build_log.build_number}
Target Server: {build_log.target_server or 'Unknown'}
Error Summary: {error_summary}
Root Cause: {root_cause}

Generate 2-3 specific shell commands that could resolve this issue.
Focus on:
1. Commands that address the root cause
2. Safe commands that won't harm the system  
3. Commands appropriate for the target server

Provide only the commands, one per line, without explanation.
"""

        return ask_ai_for_command(
            fix_prompt,
            memory=self.memory.get(),
            system_context=self.system_context,
        )

    def _parse_command_suggestions(self, command_result: Dict[str, Any]) -> List[str]:
        """Parse AI returned command suggestions into a list of cleaned commands."""
        suggested_commands: List[str] = []
        if command_result and command_result.get('success'):
            ai_response = command_result.get('ai_response', {})
            command_text = ai_response.get('final_command', '') or ai_response.get('response', '')

            # Extract individual commands
            lines = command_text.split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('//'):
                    # Clean up common prefixes
                    line = re.sub(r'^\d+[\.\)]\s*', '', line)  # Remove "1. " or "1) "
                    line = re.sub(r'^[-\*]\s*', '', line)      # Remove "- " or "* "
                    if line:
                        suggested_commands.append(line)

        return suggested_commands
    
    def _generate_fallback_commands(self, ai_analysis: Dict[str, Any], console_log: str) -> List[str]:
        """Generate fallback fix commands based on error patterns."""
        commands = []
        full_analysis = ai_analysis.get('full_analysis', '').lower()
        
        # Pattern-based command suggestions
        if 'package' in full_analysis or 'install' in full_analysis:
            commands.extend([
                'sudo apt update && sudo apt upgrade -y',
                'sudo yum update -y'
            ])
        
        if 'service' in full_analysis or 'systemd' in full_analysis:
            commands.extend([
                'sudo systemctl daemon-reload',
                'sudo systemctl status <service-name>',
                'sudo systemctl restart <service-name>'
            ])
        
        if 'permission' in full_analysis:
            commands.extend([
                'ls -la /path/to/file',
                'sudo chmod 755 /path/to/file',
                'sudo chown user:group /path/to/file'
            ])
        
        if 'disk' in full_analysis or 'space' in full_analysis:
            commands.extend([
                'df -h',
                'sudo du -sh /* | sort -rh | head -20',
                'sudo find /tmp -type f -atime +7 -delete'
            ])
        
        if 'network' in full_analysis or 'connection' in full_analysis:
            commands.extend([
                'ping -c 4 target-host',
                'telnet target-host port',
                'sudo systemctl status firewalld'
            ])
        
        # Default diagnostic commands
        if not commands:
            commands = [
                'systemctl --failed',
                'journalctl -xe --no-pager',
                'tail -n 50 /var/log/syslog'
            ]
        
        return commands[:3]  # Return max 3 fallback commands
    
    def create_fix_history(self, analysis_result: Dict[str, Any], user_confirmed: bool = False) -> Optional[FixHistory]:
        """Create a fix history record from analysis results."""
        try:
            fix_history = FixHistory(
                build_id=analysis_result.get('build_id'),
                server_id=analysis_result.get('target_server', 'unknown'),
                commands=analysis_result.get('suggested_commands', []),
                error_summary=analysis_result.get('error_summary', 'Build failed'),
                user_confirmed=user_confirmed,
                success=False  # Will be updated when commands are executed
            )
            
            fix_id = fix_history.save()
            return fix_history if fix_id > 0 else None
            
        except Exception as e:
            logger.error(f"Failed to create fix history: {e}")
            return None