"""
Quality Assurance Agent Shim:
Maintains backward compatibility for imports from agents.qa_critic.
Delegates to agents.qa_validator_agent.QualityAssuranceAgent.
"""

from agents.qa_validator_agent import QualityAssuranceAgent

__all__ = ["QualityAssuranceAgent"]
