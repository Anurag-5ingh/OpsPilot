"""
Security Compliance Checker

ML-enhanced policy validation system that checks commands against
security policies, compliance frameworks, and organizational rules.
"""

import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ComplianceFramework(Enum):
    """Supported compliance frameworks"""
    SOX = "sox"
    PCI_DSS = "pci_dss"
    HIPAA = "hipaa"
    SOC2 = "soc2"
    GDPR = "gdpr"
    CIS = "cis"
    NIST = "nist"
    CUSTOM = "custom"


class ViolationSeverity(Enum):
    """Severity levels for compliance violations"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ComplianceViolation:
    """Represents a compliance policy violation"""
    rule_id: str
    framework: ComplianceFramework
    severity: ViolationSeverity
    title: str
    description: str
    recommendation: str
    affected_command: str
    evidence: List[str]
    remediation_commands: List[str] = None


@dataclass
class SecurityPolicy:
    """Represents a security policy rule"""
    id: str
    name: str
    framework: ComplianceFramework
    severity: ViolationSeverity
    pattern: str
    description: str
    recommendation: str
    allowed_contexts: List[str] = None
    blocked_users: List[str] = None
    time_restrictions: Dict = None
    ml_enhanced: bool = False


class MLComplianceAnalyzer:
    """
    ML-enhanced compliance analyzer that learns from policy violations
    and user approvals to improve policy enforcement accuracy.
    """
    
    def __init__(self):
        self.violation_history = []
        self.approval_patterns = {}
        self.context_weights = {}
    
    def analyze_violation_context(self, command: str, violation: ComplianceViolation, 
                                system_context: Dict, user_context: Dict) -> float:
        """
        Use ML to determine if a violation should be flagged based on context
        
        Returns:
            float: Confidence score (0.0 = likely false positive, 1.0 = real violation)
        """
        # Extract contextual features
        features = self._extract_context_features(command, violation, system_context, user_context)
        
        # Look for similar historical patterns
        historical_score = self._analyze_historical_patterns(features)
        
        # Calculate context-based score
        context_score = self._calculate_context_score(features)
        
        # Combine scores with learned weights
        final_score = (historical_score * 0.6) + (context_score * 0.4)
        
        return min(max(final_score, 0.0), 1.0)
    
    def _extract_context_features(self, command: str, violation: ComplianceViolation,
                                system_context: Dict, user_context: Dict) -> Dict:
        """Extract features for ML analysis"""
        return {
            'command_type': command.split()[0] if command.split() else '',
            'violation_framework': violation.framework.value,
            'violation_severity': violation.severity.value,
            'user_role': user_context.get('role', 'unknown'),
            'system_env': system_context.get('environment', 'unknown'),
            'time_of_day': datetime.now().hour,
            'is_maintenance_window': user_context.get('maintenance_window', False),
            'has_approval': user_context.get('has_approval', False),
            'command_frequency': self._get_command_frequency(command)
        }
    
    def _analyze_historical_patterns(self, features: Dict) -> float:
        """Analyze historical violation patterns"""
        # Simplified ML logic - would use trained model in production
        similar_violations = [
            v for v in self.violation_history
            if v.get('command_type') == features['command_type']
            and v.get('violation_framework') == features['violation_framework']
        ]
        
        if not similar_violations:
            return 0.5  # Neutral score for new patterns
        
        # Calculate approval rate for similar violations
        approved_count = sum(1 for v in similar_violations if v.get('user_approved', False))
        approval_rate = approved_count / len(similar_violations)
        
        # Higher approval rate = lower violation confidence
        return 1.0 - approval_rate
    
    def _calculate_context_score(self, features: Dict) -> float:
        """Calculate context-based violation score"""
        score = 0.5  # Base score
        
        # Adjust based on user role
        if features['user_role'] in ['admin', 'devops', 'security']:
            score -= 0.2  # Trusted roles get lower violation scores
        
        # Adjust based on maintenance window
        if features['is_maintenance_window']:
            score -= 0.3  # Maintenance windows are more permissive
        
        # Adjust based on approval
        if features['has_approval']:
            score -= 0.4  # Pre-approved commands are less likely violations
        
        # Adjust based on command frequency
        if features['command_frequency'] > 10:  # Frequent commands
            score -= 0.1  # Common commands are less likely violations
        
        return max(0.0, min(1.0, score))
    
    def _get_command_frequency(self, command: str) -> int:
        """Get frequency of command execution from history"""
        # Simplified - would query actual ML database
        return self.approval_patterns.get(command, 0)
    
    def record_violation_outcome(self, violation: ComplianceViolation, 
                               user_approved: bool, context_features: Dict):
        """Record violation outcome for ML learning"""
        outcome = {
            'violation_id': violation.rule_id,
            'command': violation.affected_command,
            'user_approved': user_approved,
            'timestamp': datetime.now().isoformat(),
            **context_features
        }
        self.violation_history.append(outcome)
        
        # Update approval patterns
        command = violation.affected_command
        if command not in self.approval_patterns:
            self.approval_patterns[command] = 0
        
        if user_approved:
            self.approval_patterns[command] += 1


class SecurityComplianceChecker:
    """
    Comprehensive security compliance checker with ML enhancement.
    
    Validates commands against multiple compliance frameworks and
    organizational security policies with intelligent context awareness.
    """
    
    def __init__(self, policy_file: Optional[str] = None):
        """Initialize compliance checker with security policies"""
        self.policies = self._load_default_policies()
        self.ml_analyzer = MLComplianceAnalyzer()
        self.enabled_frameworks = set()
        self.custom_policies = []
        
        if policy_file:
            self._load_custom_policies(policy_file)
    
    def _load_default_policies(self) -> List[SecurityPolicy]:
        """Load default security policies for common compliance frameworks"""
        return [
            # SOX Compliance Policies
            SecurityPolicy(
                id="sox_001",
                name="Financial Data Access Control",
                framework=ComplianceFramework.SOX,
                severity=ViolationSeverity.CRITICAL,
                pattern=r".*\b(financial|accounting|revenue|audit).*\.(sql|db|csv)",
                description="Direct access to financial data files without proper authorization",
                recommendation="Use approved database interfaces with proper access controls",
                allowed_contexts=["audit_approved", "finance_team"]
            ),
            SecurityPolicy(
                id="sox_002", 
                name="Database Schema Modification",
                framework=ComplianceFramework.SOX,
                severity=ViolationSeverity.HIGH,
                pattern=r"\b(alter|drop|create)\s+(table|database|schema)",
                description="Database schema modifications require approval for SOX compliance",
                recommendation="Submit change request through approved change management process"
            ),
            
            # PCI DSS Policies
            SecurityPolicy(
                id="pci_001",
                name="Credit Card Data Exposure",
                framework=ComplianceFramework.PCI_DSS,
                severity=ViolationSeverity.CRITICAL,
                pattern=r".*\b(card|credit|payment|cardholder).*\.(log|txt|csv|sql)",
                description="Potential exposure of credit card data",
                recommendation="Use PCI-compliant data handling procedures",
                blocked_users=["guest", "temp"]
            ),
            SecurityPolicy(
                id="pci_002",
                name="Network Segmentation Violation",
                framework=ComplianceFramework.PCI_DSS,
                severity=ViolationSeverity.HIGH,
                pattern=r"\b(iptables|firewall).*(-F|flush|disable)",
                description="Disabling network security controls violates PCI DSS requirements",
                recommendation="Maintain network segmentation between cardholder and non-cardholder environments"
            ),
            
            # CIS Security Controls
            SecurityPolicy(
                id="cis_001",
                name="Privileged Account Management",
                framework=ComplianceFramework.CIS,
                severity=ViolationSeverity.HIGH,
                pattern=r"\b(useradd|usermod).*(-u\s+0|-g\s+0|root)",
                description="Creating or modifying privileged accounts without proper controls",
                recommendation="Use centralized identity management system for privileged accounts"
            ),
            SecurityPolicy(
                id="cis_002",
                name="Secure Configuration Management",
                framework=ComplianceFramework.CIS,
                severity=ViolationSeverity.MEDIUM,
                pattern=r"\b(chmod|chown).*777",
                description="Setting overly permissive file permissions",
                recommendation="Follow principle of least privilege for file permissions"
            ),
            
            # NIST Cybersecurity Framework
            SecurityPolicy(
                id="nist_001",
                name="Data Protection Controls",
                framework=ComplianceFramework.NIST,
                severity=ViolationSeverity.HIGH,
                pattern=r"\b(rm|delete|truncate).*\.(backup|bak|archive)",
                description="Deletion of backup or archive files without proper authorization",
                recommendation="Implement data retention policies and backup protection controls"
            ),
            SecurityPolicy(
                id="nist_002",
                name="Access Control Validation", 
                framework=ComplianceFramework.NIST,
                severity=ViolationSeverity.MEDIUM,
                pattern=r"\bsudo\s+(su|bash|sh)\s+",
                description="Privilege escalation command requiring additional validation",
                recommendation="Use specific sudo commands instead of shell escalation"
            ),
            
            # General Security Policies
            SecurityPolicy(
                id="sec_001",
                name="Password Exposure Risk",
                framework=ComplianceFramework.CUSTOM,
                severity=ViolationSeverity.CRITICAL,
                pattern=r".*(-p\s+|--password\s+|password=)[^\s]+",
                description="Command line password usage exposes credentials in process lists",
                recommendation="Use environment variables or secure credential stores"
            ),
            SecurityPolicy(
                id="sec_002",
                name="Remote Code Execution Risk",
                framework=ComplianceFramework.CUSTOM,
                severity=ViolationSeverity.HIGH,
                pattern=r"\b(wget|curl).*\|\s*(bash|sh|python)",
                description="Downloading and executing remote code without validation",
                recommendation="Download scripts first, review content, then execute with explicit permissions"
            )
        ]
    
    def enable_framework(self, framework: ComplianceFramework):
        """Enable compliance checking for specific framework"""
        self.enabled_frameworks.add(framework)
        logger.info(f"Enabled compliance framework: {framework.value}")
    
    def disable_framework(self, framework: ComplianceFramework):
        """Disable compliance checking for specific framework"""
        self.enabled_frameworks.discard(framework)
        logger.info(f"Disabled compliance framework: {framework.value}")
    
    def check_command_compliance(self, command: str, system_context: Dict = None,
                               user_context: Dict = None) -> Dict:
        """
        Check command against all enabled compliance policies
        
        Args:
            command: Shell command to check
            system_context: System context information
            user_context: User context (role, permissions, etc.)
            
        Returns:
            Dict containing compliance check results
        """
        violations = []
        warnings = []
        system_context = system_context or {}
        user_context = user_context or {}
        
        # Check against all applicable policies
        for policy in self.policies:
            if (self.enabled_frameworks and 
                policy.framework not in self.enabled_frameworks and 
                policy.framework != ComplianceFramework.CUSTOM):
                continue
            
            if self._matches_policy(command, policy):
                # Check if violation should be flagged based on context
                if policy.ml_enhanced:
                    violation_confidence = self.ml_analyzer.analyze_violation_context(
                        command, self._create_violation(policy, command), 
                        system_context, user_context
                    )
                    
                    if violation_confidence < 0.3:  # Low confidence = likely false positive
                        continue
                
                violation = self._create_violation(policy, command)
                
                # Check context-based exceptions
                if self._is_contextually_allowed(policy, user_context, system_context):
                    warnings.append({
                        'type': 'policy_exception',
                        'message': f"Policy {policy.name} triggered but allowed by context",
                        'violation': violation
                    })
                else:
                    violations.append(violation)
        
        # Calculate overall compliance score
        compliance_score = self._calculate_compliance_score(violations)
        
        return {
            'compliant': len(violations) == 0,
            'compliance_score': compliance_score,
            'violations': [self._violation_to_dict(v) for v in violations],
            'warnings': warnings,
            'recommendations': self._generate_recommendations(violations),
            'approved_alternatives': self._suggest_compliant_alternatives(command, violations)
        }
    
    def _matches_policy(self, command: str, policy: SecurityPolicy) -> bool:
        """Check if command matches policy pattern"""
        return bool(re.search(policy.pattern, command, re.IGNORECASE))
    
    def _create_violation(self, policy: SecurityPolicy, command: str) -> ComplianceViolation:
        """Create violation object from policy and command"""
        evidence = [f"Command matches pattern: {policy.pattern}"]
        
        return ComplianceViolation(
            rule_id=policy.id,
            framework=policy.framework,
            severity=policy.severity,
            title=policy.name,
            description=policy.description,
            recommendation=policy.recommendation,
            affected_command=command,
            evidence=evidence,
            remediation_commands=self._generate_remediation(policy, command)
        )
    
    def _is_contextually_allowed(self, policy: SecurityPolicy, user_context: Dict, 
                               system_context: Dict) -> bool:
        """Check if policy violation is allowed based on context"""
        # Check user-based exceptions
        if policy.blocked_users:
            user_id = user_context.get('user_id', 'unknown')
            if user_id in policy.blocked_users:
                return False
        
        # Check allowed contexts
        if policy.allowed_contexts:
            current_context = user_context.get('context', 'default')
            if current_context not in policy.allowed_contexts:
                return False
        
        # Check time restrictions
        if policy.time_restrictions:
            current_hour = datetime.now().hour
            allowed_hours = policy.time_restrictions.get('allowed_hours', [])
            if allowed_hours and current_hour not in allowed_hours:
                return False
        
        # Check maintenance window
        if user_context.get('maintenance_window') and policy.severity != ViolationSeverity.CRITICAL:
            return True
        
        # Check pre-approval
        if user_context.get('has_approval'):
            return True
        
        return False
    
    def _calculate_compliance_score(self, violations: List[ComplianceViolation]) -> float:
        """Calculate overall compliance score (0.0 to 1.0)"""
        if not violations:
            return 1.0
        
        # Weight violations by severity
        severity_weights = {
            ViolationSeverity.INFO: 0.1,
            ViolationSeverity.LOW: 0.2,
            ViolationSeverity.MEDIUM: 0.5,
            ViolationSeverity.HIGH: 0.8,
            ViolationSeverity.CRITICAL: 1.0
        }
        
        total_weight = sum(severity_weights[v.severity] for v in violations)
        max_possible_weight = len(violations)  # Assuming worst case (all critical)
        
        return max(0.0, 1.0 - (total_weight / max_possible_weight))
    
    def _generate_recommendations(self, violations: List[ComplianceViolation]) -> List[str]:
        """Generate actionable recommendations based on violations"""
        recommendations = []
        
        for violation in violations:
            if violation.severity == ViolationSeverity.CRITICAL:
                recommendations.append(f"🚨 CRITICAL: {violation.recommendation}")
            elif violation.severity == ViolationSeverity.HIGH:
                recommendations.append(f"⚠️ HIGH PRIORITY: {violation.recommendation}")
            else:
                recommendations.append(f"ℹ️ {violation.recommendation}")
        
        return recommendations
    
    def _suggest_compliant_alternatives(self, command: str, 
                                     violations: List[ComplianceViolation]) -> List[Dict]:
        """Suggest compliant alternatives for violating commands"""
        alternatives = []
        
        for violation in violations:
            if violation.remediation_commands:
                alternatives.append({
                    'violation_id': violation.rule_id,
                    'original_command': command,
                    'compliant_alternatives': violation.remediation_commands,
                    'explanation': f"Alternative approaches that comply with {violation.framework.value.upper()}"
                })
        
        return alternatives
    
    def _generate_remediation(self, policy: SecurityPolicy, command: str) -> List[str]:
        """Generate remediation commands based on policy"""
        remediation = []
        
        # Pattern-based remediation suggestions
        if "chmod.*777" in policy.pattern:
            remediation.append(command.replace("777", "755"))
            remediation.append(command.replace("777", "644"))
        
        elif "password=" in policy.pattern:
            remediation.append("# Set password via environment variable:")
            remediation.append("export DB_PASSWORD='your_password'")
            remediation.append(re.sub(r"password=[^\s]+", "password=$DB_PASSWORD", command))
        
        elif "wget.*|.*bash" in policy.pattern:
            script_url = re.search(r"wget\s+([^\s]+)", command)
            if script_url:
                remediation.extend([
                    f"wget {script_url.group(1)} -O script.sh",
                    "# Review script content first",
                    "cat script.sh",
                    "# Execute only after verification",
                    "chmod +x script.sh && ./script.sh"
                ])
        
        return remediation
    
    def _violation_to_dict(self, violation: ComplianceViolation) -> Dict:
        """Convert violation to dictionary for JSON serialization"""
        return {
            'rule_id': violation.rule_id,
            'framework': violation.framework.value,
            'severity': violation.severity.value,
            'title': violation.title,
            'description': violation.description,
            'recommendation': violation.recommendation,
            'affected_command': violation.affected_command,
            'evidence': violation.evidence,
            'remediation_commands': violation.remediation_commands or []
        }
    
    def _load_custom_policies(self, policy_file: str):
        """Load custom policies from file"""
        try:
            with open(policy_file, 'r') as f:
                custom_policies_data = json.load(f)
            
            for policy_data in custom_policies_data:
                policy = SecurityPolicy(
                    id=policy_data['id'],
                    name=policy_data['name'],
                    framework=ComplianceFramework(policy_data.get('framework', 'custom')),
                    severity=ViolationSeverity(policy_data['severity']),
                    pattern=policy_data['pattern'],
                    description=policy_data['description'],
                    recommendation=policy_data['recommendation'],
                    allowed_contexts=policy_data.get('allowed_contexts'),
                    blocked_users=policy_data.get('blocked_users'),
                    time_restrictions=policy_data.get('time_restrictions'),
                    ml_enhanced=policy_data.get('ml_enhanced', False)
                )
                self.custom_policies.append(policy)
                
            logger.info(f"Loaded {len(self.custom_policies)} custom policies")
            
        except Exception as e:
            logger.error(f"Failed to load custom policies from {policy_file}: {e}")
    
    def record_user_decision(self, violation_id: str, user_approved: bool, 
                           user_context: Dict, command: str):
        """Record user decision on policy violation for ML learning"""
        # Find the violation
        violation = None
        for policy in self.policies + self.custom_policies:
            if policy.id == violation_id:
                violation = self._create_violation(policy, command)
                break
        
        if violation:
            context_features = {
                'user_role': user_context.get('role', 'unknown'),
                'maintenance_window': user_context.get('maintenance_window', False),
                'has_approval': user_context.get('has_approval', False)
            }
            
            self.ml_analyzer.record_violation_outcome(
                violation, user_approved, context_features
            )
    
    def get_framework_status(self) -> Dict:
        """Get status of all compliance frameworks"""
        return {
            'enabled_frameworks': [f.value for f in self.enabled_frameworks],
            'available_frameworks': [f.value for f in ComplianceFramework],
            'total_policies': len(self.policies) + len(self.custom_policies),
            'custom_policies': len(self.custom_policies)
        }