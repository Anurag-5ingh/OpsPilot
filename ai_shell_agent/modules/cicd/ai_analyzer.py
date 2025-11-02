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
from ..shared.ai_client import get_openai_client
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
                r'Operation not permitted',
                r'EACCES',
                r'cannot open.*Permission denied'
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
            'directory_error': [
                r'cannot read directory',
                r'cannot list directory',
                r'opendir.*failed',
                r'directory not found',
                r'chdir.*failed',
                r'cannot create.*directory',
                r'mkdir.*failed'
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
            # Get console logs - fetch more lines for comprehensive analysis
            logger.debug(f"Fetching console logs for analysis (last 2000 lines)")
            console_log = ""
            if jenkins_service:
                console_log = jenkins_service.get_console_log_tail(
                    build_log.job_name, 
                    build_log.build_number, 
                    lines=2000  # Get last 2000 lines for comprehensive analysis
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
                'suggested_steps': fix_suggestions.get('steps', []),
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

            # Call AI directly for log analysis (not via ask_ai_for_command)
            client = get_openai_client()
            messages = [
                {"role": "system", "content": "You are an expert Jenkins/CI-CD log analyst specializing in identifying precise root causes of build failures."},
                {"role": "user", "content": analysis_prompt}
            ]
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                extra_query={"api-version": "2024-08-01-preview"},
                temperature=0.1,  # Very low temperature for accurate analysis
                response_format={"type": "json_object"}  # Require JSON output
            )

            content = response.choices[0].message.content.strip()
            logger.debug(f"Received AI response: {content[:500]}...")
            
            # Parse JSON response
            parsed_analysis = None
            try:
                data = json.loads(content)
                # Normalize expected keys
                parsed_analysis = {
                    'error_summary': data.get('error_summary') or data.get('summary') or '',
                    'root_cause': data.get('root_cause') or data.get('cause') or '',
                    'confidence_score': float(data.get('confidence', data.get('confidence_score', 0.7))),
                    'priority': (data.get('priority') or 'medium').lower(),
                    'full_analysis': content,
                    # Helpful extras for future use
                    'primary_error_line': data.get('primary_error_line'),
                    'primary_error_excerpt': data.get('primary_error_excerpt'),
                    'evidence': data.get('evidence') or [],
                    'error_type': data.get('error_type'),
                    'failure_chain': data.get('failure_chain', [])
                }
                logger.info(f"Successfully parsed AI analysis for {job_name}#{build_number}")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse structured JSON from AI response: {e}")
                logger.debug(f"Raw response: {content}")
                
            if not parsed_analysis:
                # Fallback to legacy parser (pattern-based extraction from free text)
                parsed_analysis = self._parse_ai_analysis(content, quick_analysis)
            
            # Store in conversation memory for context
            self.memory.add(f"Build failure analysis for {job_name}#{build_number}", content)
            
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
        # Structured log preprocessing - create layers for better AI understanding
        log_structure = self._preprocess_logs_for_analysis(console_log)
        
        # Get full context but in a smart, structured way
        lines = console_log.split('\n')
        total_lines = len(lines)
        
        # Send more context - last 500 lines for better error detection
        last_tail_lines = '\n'.join(lines[-500:]) if total_lines > 500 else '\n'.join(lines)
        
        # Also get first 100 lines for initialization context
        first_lines = '\n'.join(lines[:100]) if total_lines > 100 else '\n'.join(lines)

        error_context = (
            f"Jenkins Job: {job_name}#{build_number}\n"
            f"Target Server: {target_server or 'Unknown'}\n"
            f"Total Log Lines: {total_lines}\n"
            f"Error Categories Found (Pattern Analysis): {', '.join(quick_analysis.get('categories', []))}\n"
            f"Error Line Count: {len(quick_analysis.get('error_lines', []))}\n\n"
            "Key Error Lines (Pattern-Detected):\n"
            f"{chr(10).join(quick_analysis.get('error_lines', [])[:10])}\n\n"
            "Log Structure Analysis:\n"
            f"  - Critical sections: {len(log_structure.get('critical_sections', []))}\n"
            f"  - Error blocks: {len(log_structure.get('error_blocks', []))}\n"
            f"  - Failure indicators: {len(log_structure.get('failure_indicators', []))}\n\n"
            "Build Initialization (first 100 lines):\n"
            f"{first_lines}\n\n"
            "Build Termination (last 500 lines - most relevant):\n"
            f"{last_tail_lines}\n\n"
            "Critical Log Sections:\n"
            f"{self._format_log_sections(log_structure.get('critical_sections', []))}\n"
        )

        analysis_prompt = (
            "You are an expert Jenkins/CI-CD log analyst specializing in identifying precise root causes. "
            "Your job is to read the ENTIRE log carefully and identify the EXACT problem.\n\n"
            "CRITICAL REQUIREMENTS:\n"
            "1. READ THE FULL LOG - Do not jump to conclusions based on generic error messages\n"
            "2. Identify the EXACT root cause (e.g., directory missing, permission denied, file not found)\n"
            "3. Distinguish between root causes vs cascading errors\n"
            "4. Trace the failure chain from the first error to the final failure\n\n"
            f"{error_context}\n"
            "SPECIFIC ERROR TYPES TO LOOK FOR:\n"
            "- Directory Issues: directory missing, cannot read directory, opendir failed, chdir failed\n"
            "- Permission Issues: Permission denied, Access denied, EACCES, read-only filesystem, unable to write\n"
            "- File Issues: file not found, cannot access file, No such file or directory\n"
            "- Command Issues: command not found, non-zero exit code, execution failure\n"
            "- Network Issues: Connection refused, Connection timed out, unreachable host\n"
            "- Configuration Issues: invalid config, missing parameter, malformed YAML/JSON\n"
            "- Ansible Specific: TASK FAILED, fatal error, unreachable hosts, permission denied\n\n"
            "DIAGNOSIS APPROACH:\n"
            "1. Read the log from START to END to understand the build flow\n"
            "2. Find the FIRST error that actually broke the process\n"
            "3. For file/directory errors, determine: Does it exist? Are permissions wrong? Is the path correct?\n"
            "4. For permission errors, identify: Which file/directory? What operation was attempted?\n"
            "5. For Ansible playbook errors, identify: Which task failed? What specific error occurred?\n"
            "6. Provide detailed context about what was attempted and why it failed\n\n"
            "Respond ONLY with strict JSON (no markdown, no prose) in the following schema:\n"
            "{\n"
            "  \"error_summary\": string (detailed explanation of what failed - include specific file paths, commands, etc.),\n"
            "  \"root_cause\": string (comprehensive explanation of WHY it failed - NO word limit, be thorough),\n"
            "  \"confidence\": number (0.0-1.0),\n"
            "  \"priority\": \"low\"|\"medium\"|\"high\",\n"
            "  \"primary_error_line\": number | null,\n"
            "  \"primary_error_excerpt\": string,\n"
            "  \"evidence\": [{\"line\": number, \"text\": string}],\n"
            "  \"error_type\": string,\n"
            "  \"failure_chain\": [{\"step\": number, \"description\": string}] (optional - trace how error propagated)\n"
            "}\n\n"
            "CRITICAL INSTRUCTIONS:\n"
            "- Root cause MUST be comprehensive - explain the FULL context with all relevant details\n"
            "- Include EXACT file paths, directory names, permission levels, or configurations involved\n"
            "- NO artificial word limits - explain thoroughly and completely\n"
            "- Use evidence array to cite SPECIFIC log lines that prove your analysis\n"
            "- Be PRECISE: 'directory /var/log/app does not exist' vs 'permission denied on /var/log/app'\n"
            "- AVOID generic explanations like 'Build failed due to ansible error' - be SPECIFIC\n"
        )

        return analysis_prompt
    
    def _preprocess_logs_for_analysis(self, console_log: str) -> Dict[str, Any]:
        """Preprocess logs to extract critical sections for smarter AI analysis."""
        lines = console_log.split('\n')
        critical_sections = []
        error_blocks = []
        failure_indicators = []
        
        # Define section markers to identify important log regions
        section_markers = {
            'ansible_task': [r'TASK \[.*?\]', r'task \[.*?\]'],
            'ansible_fatal': [r'fatal:.*?: FAILED', r'FAILED! =>'],
            'build_failure': [r'Build step.*failed', r'Build failed'],
            'execution_error': [r'ERROR:', r'FATAL:', r'Exception:', r'Error:'],
            'permission_error': [
                r'Permission denied', r'Access denied', r'EACCES', r'EAGAIN',
                r'Operation not permitted', r'cannot open.*Permission denied',
                r'unable to write', r'read-only', r'readonly'
            ],
            'file_error': [
                r'No such file or directory', r'cannot access', r'file not found',
                r'directory not found', r'path not found', r'No such path',
                r'cannot create directory', r'cannot find.*file', r'not a directory',
                r'NotADirectoryError', r'FileNotFoundError', r'Is a directory'
            ],
            'command_failed': [r'command.*failed', r'command not found', r'non-zero exit', r'exit code \d+'],
            'connection_error': [r'Connection refused', r'Connection timed out', r'No route to host'],
            'directory_error': [
                r'cannot read directory', r'cannot list directory', r'opendir.*failed',
                r'directory exists', r'cannot create.*directory', r'mkdir.*failed',
                r'chdir.*failed'
            ]
        }
        
        # Track consecutive error lines to form error blocks
        current_block = []
        block_start_line = -1
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            
            # Check for section markers
            for section_type, patterns in section_markers.items():
                for pattern in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        # Capture a window around this critical line
                        start_idx = max(0, i - 3)
                        end_idx = min(len(lines), i + 8)
                        window_lines = lines[start_idx:end_idx]
                        
                        critical_sections.append({
                            'type': section_type,
                            'line': i + 1,
                            'context': window_lines
                        })
                        
                        # Track this in current error block
                        if section_type in ['ansible_fatal', 'build_failure', 'execution_error']:
                            if not current_block:
                                block_start_line = i + 1
                            current_block.append(line)
                        break
                else:
                    continue
                break
            
            # Check for failure indicators
            if any(indicator in line_lower for indicator in ['failed', 'error', 'fatal', 'unreachable', 'aborted']):
                failure_indicators.append({
                    'line': i + 1,
                    'text': line.strip()
                })
            
            # Close error block if we've moved away from errors
            if current_block and i > block_start_line + 20:  # Close block after 20 lines of silence
                error_blocks.append({
                    'start_line': block_start_line,
                    'end_line': i,
                    'lines': current_block
                })
                current_block = []
                block_start_line = -1
        
        # Close any remaining error block
        if current_block:
            error_blocks.append({
                'start_line': block_start_line if block_start_line > 0 else len(lines),
                'end_line': len(lines),
                'lines': current_block
            })
        
        return {
            'critical_sections': critical_sections[:20],  # Limit to top 20 to avoid overload
            'error_blocks': error_blocks[:5],  # Top 5 error blocks
            'failure_indicators': failure_indicators[:30]  # Top 30 indicators
        }
    
    def _format_log_sections(self, sections: List[Dict[str, Any]]) -> str:
        """Format critical log sections for inclusion in prompt."""
        if not sections:
            return "  (none detected)"
        
        formatted = []
        for section in sections:
            context_lines = '\n    '.join(section['context'][:5])  # Show first 5 lines of context
            formatted.append(
                f"  [{section['type']}] Line {section['line']}:\n"
                f"    {context_lines}"
            )
        
        return '\n'.join(formatted[:10])  # Limit to first 10 sections

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
        elif 'directory_error' in categories:
            root_cause = "Directory access issue - directory may not exist or have incorrect permissions"
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
                # If even after fallback we have no concrete command, ask AI for human-readable steps
                suggested_steps: List[str] = []
                try:
                    if not suggested_commands:
                        steps_prompt = f"""
Given this Jenkins failure analysis, provide a concise, actionable sequence of steps to resolve the issue.

Job: {build_log.job_name}#{build_log.build_number}
Target Server: {build_log.target_server or 'Unknown'}
Error Summary: {error_summary}
Root Cause: {root_cause}

Requirements:
1) Prefer precise commands when safe and known; otherwise write human-readable steps.
2) Keep each step on a single line.
3) Number the steps 1., 2., 3. etc.
4) Do not include prose outside the steps list.
"""
                        steps_result = ask_ai_for_command(
                            steps_prompt,
                            memory=self.memory.get(),
                            system_context=self.system_context,
                        )
                        # Parse steps similar to commands (line-wise), but keep as steps
                        if steps_result:
                            ai_resp = steps_result.get('ai_response', {})
                            steps_text = ai_resp.get('final_command') or ai_resp.get('response') or ''
                            for line in (steps_text or '').split('\n'):
                                ln = line.strip()
                                if not ln:
                                    continue
                                ln = re.sub(r'^\d+[\.\)]\s*', '', ln)
                                ln = re.sub(r'^[-\*]\s*', '', ln)
                                suggested_steps.append(ln)
                except Exception as _e:
                    logger.debug(f"Failed to get suggested steps: {_e}")
            else:
                # Commands exist; still generate concise human-readable steps for UI
                suggested_steps: List[str] = []
                try:
                    steps_prompt = f"""
Given this Jenkins failure analysis, provide a concise, actionable sequence of steps to resolve the issue.

Job: {build_log.job_name}#{build_log.build_number}
Target Server: {build_log.target_server or 'Unknown'}
Error Summary: {error_summary}
Root Cause: {root_cause}

Requirements:
1) Prefer precise commands when safe and known; otherwise write human-readable steps.
2) Keep each step on a single line.
3) Number the steps 1., 2., 3. etc.
4) Do not include prose outside the steps list.
"""
                    steps_result = ask_ai_for_command(
                        steps_prompt,
                        memory=self.memory.get(),
                        system_context=self.system_context,
                    )
                    if steps_result:
                        ai_resp = steps_result.get('ai_response', {})
                        steps_text = ai_resp.get('final_command') or ai_resp.get('response') or ''
                        for line in (steps_text or '').split('\n'):
                            ln = line.strip()
                            if not ln:
                                continue
                            ln = re.sub(r'^\d+[\.\)]\s*', '', ln)
                            ln = re.sub(r'^[-\*]\s*', '', ln)
                            suggested_steps.append(ln)
                except Exception as _e:
                    logger.debug(f"Failed to get suggested steps (commands exist): {_e}")
            
            # Look for relevant Ansible playbook
            suggested_playbook = None
            if ansible_service and build_log.target_server:
                suggested_playbook = ansible_service.suggest_fix_playbook(
                    error_summary, 
                    build_log.target_server
                )
            
            try:
                logger.info(
                    "Fix suggestions prepared: commands=%s steps=%s playbook=%s",
                    len(suggested_commands or []),
                    len(locals().get('suggested_steps', []) or []),
                    bool(suggested_playbook)
                )
            except Exception:
                pass

            return {
                'commands': suggested_commands[:5],  # Limit to 5 commands for safety
                'steps': (locals().get('suggested_steps', []) or [])[:7],  # Limit steps
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
        if command_result:
            # Parse from standard ai_handler response shape first; fall back gracefully
            ai_response = command_result.get('ai_response') or command_result
            command_text = (
                ai_response.get('final_command', '')
                or ai_response.get('response', '')
                or command_result.get('final_command', '')
                or ''
            )

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