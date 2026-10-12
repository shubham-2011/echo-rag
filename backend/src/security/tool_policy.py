import re

from src.security.auth import ApiScope, AuthenticatedPrincipal
from src.security.models import SecurityAction, SecurityDecision, SecurityRiskLevel

_TOOL_NAME = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")


class ToolPolicy:
    """Authorize tool names only; execution remains outside this policy and is not provided."""

    def __init__(self, allowed_tools: frozenset[str] = frozenset()):
        if any(not _TOOL_NAME.fullmatch(name) for name in allowed_tools):
            raise ValueError("Allowed tool names must use lowercase alphanumeric, dot, underscore, or hyphen.")
        self._allowed_tools = allowed_tools

    def authorize(self, tool_name: str, principal: AuthenticatedPrincipal) -> SecurityDecision:
        if not _TOOL_NAME.fullmatch(tool_name):
            return self._deny("Tool name is invalid.", "tool.invalid_name")
        if tool_name not in self._allowed_tools:
            return self._deny("Tool is not explicitly allowlisted.", "tool.not_allowlisted")
        if ApiScope.TOOLS_INVOKE not in principal.scopes:
            return SecurityDecision(
                allowed=False,
                action=SecurityAction.DENY,
                risk_level=SecurityRiskLevel.HIGH,
                reason="API key lacks the tool invocation scope.",
                rule_id="tool.scope_required",
            )
        return SecurityDecision(
            allowed=True,
            action=SecurityAction.ALLOW,
            risk_level=SecurityRiskLevel.LOW,
            reason="Tool is allowlisted and caller has the invocation scope.",
            rule_id="tool.allowed",
        )

    @staticmethod
    def _deny(reason: str, rule_id: str) -> SecurityDecision:
        return SecurityDecision(
            allowed=False,
            action=SecurityAction.DENY,
            risk_level=SecurityRiskLevel.HIGH,
            reason=reason,
            rule_id=rule_id,
        )
