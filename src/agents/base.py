from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
import math

@dataclass
class AgentOutput:
    agent_id: str
    domain: str
    source: str
    fetched_at: datetime
    freshness_status: str          # 'fresh' | 'stale' | 'unavailable'
    confidence: float              # post-penalty confidence
    raw_confidence: float          # pre-penalty confidence
    data: dict[str, Any]
    raw_text: str
    escalation_flags: list[str] = field(default_factory=list)
    stale_seconds: int = 0         # seconds past TTL

class ICUAgent(ABC):
    agent_id: str
    domain: str
    ttl_seconds: Optional[int]
    publish_threshold: float
    gate_threshold: float
    staleness_penalty_per_ttl: float

    def __init__(self, tenant_id: str = "default-tenant"):
        self.tenant_id = tenant_id

    @abstractmethod
    async def fetch(self, patient_id: str, **kwargs) -> AgentOutput:
        """Fetch clinical domain details for a patient."""
        pass

    def _apply_staleness_penalty(self, output: AgentOutput, evaluation_time: datetime) -> AgentOutput:
        """
        Reduce confidence based on duration past TTL.
        Formula:
          stale_seconds = max(0, age_seconds - ttl_seconds)
          penalty = staleness_penalty_per_ttl * floor(stale_seconds / ttl_seconds)
        """
        if self.ttl_seconds is None or self.ttl_seconds <= 0:
            output.freshness_status = "fresh"
            output.stale_seconds = 0
            output.confidence = output.raw_confidence
            return output

        age = (evaluation_time - output.fetched_at).total_seconds()
        if age > self.ttl_seconds:
            output.freshness_status = "stale"
            stale_seconds = int(age - self.ttl_seconds)
            output.stale_seconds = stale_seconds
            
            # Calculate breaches past the first TTL interval
            num_breaches = int(stale_seconds // self.ttl_seconds)
            penalty = self.staleness_penalty_per_ttl * num_breaches
            output.confidence = round(max(0.0, min(1.0, output.raw_confidence - penalty)), 3)
        else:
            output.freshness_status = "fresh"
            output.stale_seconds = 0
            output.confidence = output.raw_confidence

        return output
