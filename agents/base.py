"""
OrthoBraceForge — Base Agent Interface
Defines AgentResult and BaseAgent abstract class used by all agent wrappers.
"""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List

logger = logging.getLogger("orthobraceforge.agents")


@dataclass
class AgentResult:
    """Standardized result from any agent invocation."""
    success: bool
    agent_name: str
    output_data: Dict[str, Any] = field(default_factory=dict)
    output_files: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    iterations_used: int = 0
    trace_log: List[str] = field(default_factory=list)


class BaseAgent(ABC):
    """Abstract base for all agent wrappers."""

    def __init__(self, name: str):
        self.name = name
        self._trace: List[str] = []

    def _log(self, msg: str):
        entry = f"[{self.name}] {msg}"
        self._trace.append(entry)
        logger.info(entry)

    def run(self, params: Dict[str, Any]) -> AgentResult:
        """Wrapper around execute() that logs start/end with timing."""
        start = datetime.now(timezone.utc)
        run_id = params.get("run_id", "")
        patient_id = params.get("patient_id", "")
        self._log(f"START execute | run_id={run_id} patient_id={patient_id}")
        try:
            result = self.execute(params)
        except Exception as e:
            elapsed = (datetime.now(timezone.utc) - start).total_seconds()
            self._log(f"FAILED execute | error={e} elapsed={elapsed:.2f}s")
            raise
        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        self._log(f"END execute | success={result.success} elapsed={elapsed:.2f}s")
        return result

    @abstractmethod
    def execute(self, params: Dict[str, Any]) -> AgentResult:
        ...
