"""
OrthoBraceForge — TalkCAD Agent
Wraps outerreaches/talkcad (Conversational CAD orchestrator).
"""
import json
from typing import Any, Dict

from .base import AgentResult, BaseAgent


class TalkCADAgent(BaseAgent):
    """
    Wraps talkcad for conversational CAD refinement.
    Accepts natural language modification requests and applies them
    to existing CAD parameters.
    """

    def __init__(self):
        super().__init__("talkcad")

    def execute(self, params: Dict[str, Any]) -> AgentResult:
        self._trace = []
        self._log("Processing conversational CAD modification")

        instruction = params.get("instruction", "")
        current_params = params.get("current_parameters", {})

        # Parse the natural language instruction into parameter modifications
        modifications = self._parse_instruction(instruction, current_params)
        self._log(f"Parsed modifications: {json.dumps(modifications, indent=2)}")

        # Apply modifications
        updated_params = {**current_params, **modifications}

        return AgentResult(
            success=True,
            agent_name=self.name,
            output_data={
                "original_instruction": instruction,
                "modifications": modifications,
                "updated_parameters": updated_params,
            },
            iterations_used=1,
            trace_log=list(self._trace),
        )

    def _parse_instruction(self, instruction: str, current: Dict) -> Dict:
        """
        Parse NL instruction into parameter changes.
        In production: uses local LLM for NLU.
        Here: rule-based parsing for common AFO modifications.
        """
        mods = {}
        inst_lower = instruction.lower()

        # Thickness modifications
        if "thicker" in inst_lower or "increase thickness" in inst_lower:
            mods["wall_thickness_mm"] = current.get("wall_thickness_mm", 3.0) + 0.5
        elif "thinner" in inst_lower or "decrease thickness" in inst_lower:
            mods["wall_thickness_mm"] = max(2.5, current.get("wall_thickness_mm", 3.0) - 0.5)

        # Angle modifications
        if "more dorsiflexion" in inst_lower:
            mods["ankle_target_deg"] = current.get("ankle_target_deg", 0) + 2
        elif "more plantarflexion" in inst_lower or "less dorsiflexion" in inst_lower:
            mods["ankle_target_deg"] = current.get("ankle_target_deg", 0) - 2

        # AFO type changes
        if "hinged" in inst_lower:
            mods["afo_type"] = "hinged"
        elif "solid" in inst_lower:
            mods["afo_type"] = "solid"
        elif "leaf spring" in inst_lower or "pls" in inst_lower:
            mods["afo_type"] = "posterior_leaf_spring"

        # Flex zone
        if "add flex" in inst_lower or "flex zone" in inst_lower:
            mods["flex_zone"] = True
        elif "remove flex" in inst_lower or "rigid" in inst_lower:
            mods["flex_zone"] = False

        if not mods:
            self._log("No recognized modifications — passing instruction to LLM")
            mods["_unresolved_instruction"] = instruction

        return mods
