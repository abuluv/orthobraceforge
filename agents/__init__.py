"""
OrthoBraceForge — Agent Wrappers
Unified interface classes for all 9 vendored repository integrations.
Each agent is a self-contained unit that can be orchestrated by LangGraph.

Re-exports all agent classes and AgentResult/BaseAgent for backward compatibility.
"""
import subprocess  # noqa: F401 — re-exported for test mocks patching "agents.subprocess"
from pathlib import Path  # noqa: F401 — re-exported for test mocks patching "agents.Path"

from .agentic3d import Agentic3DAgent
from .agentic_alloy import AgenticAlloyAgent
from .base import AgentResult, BaseAgent
from .cad_render import CADRenderAgent
from .chat_to_stl import ChatToSTLAgent
from .forma_ai import FormaAIAgent
from .octo_mcp import OctoMCPAgent
from .ortho_insoles import OrthoInsolesAgent
from .print_defect import PrintDefectAgent
from .talkcad import TalkCADAgent
from .vlm_critique import VLMCritiqueAgent

__all__ = [
    "AgentResult",
    "BaseAgent",
    "Agentic3DAgent",
    "AgenticAlloyAgent",
    "CADRenderAgent",
    "ChatToSTLAgent",
    "FormaAIAgent",
    "OctoMCPAgent",
    "OrthoInsolesAgent",
    "PrintDefectAgent",
    "TalkCADAgent",
    "VLMCritiqueAgent",
]
