import re

from src.security.models import (
    SecurityAction,
    SecurityDecision,
    SecurityInputSource,
    SecurityRiskLevel,
    SecurityViolation,
)


class InjectionDetector:
    _rules = (
        (
            "injection.instruction_override",
            re.compile(
                r"(?im)^\s*(?:please\s+)?(?:ignore|disregard|override|forget|bypass)\s+"
                r"(?:all\s+)?(?:the\s+)?(?:previous|prior|above|system|developer|safety|security)?"
                r"\s*(?:instructions?|rules?|prompts?)\b"
            ),
            "Instruction-override directive detected.",
        ),
        (
            "injection.secret_disclosure",
            re.compile(
                r"(?im)(?:^|[.!?]\s*)(?:please\s+)?"
                r"(?:reveal|print|show|output|expose|leak|return|send)\b"
                r"[^.!?\n]{0,100}\b(?:system\s+prompt|api\s+keys?|credentials?|secrets?)\b"
            ),
            "Request to disclose protected instructions or secrets detected.",
        ),
        (
            "injection.command_execution",
            re.compile(
                r"(?im)(?:^|[.!?]\s*)(?:please\s+)?(?:execute|run)\s+"
                r"(?:(?:this|the)\s+)?(?:command|code|script)\b"
            ),
            "Command-execution directive detected.",
        ),
        (
            "injection.data_exfiltration",
            re.compile(
                r"(?im)(?:^|[.!?]\s*)(?:please\s+)?(?:send|upload|forward|exfiltrate)\b"
                r"[^.!?\n]{0,120}\b(?:document|file|data|content|information)\b"
                r"[^.!?\n]{0,80}\b(?:server|website|url|endpoint|external|another)\b"
            ),
            "External data-transfer directive detected.",
        ),
        (
            "injection.security_disable",
            re.compile(
                r"(?im)(?:^|[.!?]\s*)(?:please\s+)?(?:disable|turn\s+off|bypass|remove)\b"
                r"[^.!?\n]{0,80}\b(?:security|safety|guard|filter|protection|policy|controls?)\b"
            ),
            "Security-control bypass directive detected.",
        ),
    )

    def inspect(self, text: str, source: SecurityInputSource) -> SecurityDecision:
        if source is SecurityInputSource.SYSTEM_INSTRUCTION:
            return self._decision(True, SecurityAction.ALLOW, SecurityRiskLevel.LOW,
                                  "System instruction is outside untrusted-input scanning.", "injection.system")

        violations = tuple(
            SecurityViolation(code=rule_id, message=message, risk_level=SecurityRiskLevel.HIGH)
            for rule_id, pattern, message in self._rules
            if pattern.search(text)
        )
        if not violations:
            return self._decision(
                True,
                SecurityAction.ALLOW,
                SecurityRiskLevel.LOW,
                "No high-confidence instruction-injection pattern was detected.",
                "injection.clear",
            )

        severe = len(violations) > 1
        risk = SecurityRiskLevel.CRITICAL if severe else SecurityRiskLevel.HIGH
        return SecurityDecision(
            allowed=False,
            action=SecurityAction.DENY,
            risk_level=risk,
            reason="Potential prompt-injection directives detected.",
            rule_id="injection.multiple_directives" if severe else violations[0].code,
            violations=violations,
        )

    @staticmethod
    def _decision(
        allowed: bool,
        action: SecurityAction,
        risk_level: SecurityRiskLevel,
        reason: str,
        rule_id: str,
    ) -> SecurityDecision:
        return SecurityDecision(
            allowed=allowed,
            action=action,
            risk_level=risk_level,
            reason=reason,
            rule_id=rule_id,
        )
