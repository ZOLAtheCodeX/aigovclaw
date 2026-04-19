"""PDCA agent-loop orchestrator.

Drives the AI Management System through Plan-Do-Check-Act cycles. Sits on
top of the action-executor and consumes outputs from
certification-path-planner, certification-readiness, and
cascade-impact-analyzer.

Public surface:
    PDCACycle               Top-level orchestrator.
    PDCACycleState          Persisted state record.
    GapResolutionLoop       Gap-resolution inner loop (ReAct style).
    CascadeLoop             Cascade propagation loop with depth limit.
    ValidationLoop          Refine-until-clean loop.
    Loop                    Abstract base class for inner loops.
    UserInteractionBroker   Queues user-input requests on the approval queue.
"""

from __future__ import annotations

from .orchestrator import PDCACycle, PDCAPhase, PDCAError
from .state import PDCACycleState, load_state, save_state, default_state_dir
from .loops.base_loop import Loop, LoopStatus
from .loops.gap_resolution import GapResolutionLoop
from .loops.cascade_loop import CascadeLoop
from .loops.validation_loop import ValidationLoop
from .user_interaction import UserInteractionBroker, UserInteractionRequest

__all__ = [
    "PDCACycle",
    "PDCAPhase",
    "PDCAError",
    "PDCACycleState",
    "load_state",
    "save_state",
    "default_state_dir",
    "Loop",
    "LoopStatus",
    "GapResolutionLoop",
    "CascadeLoop",
    "ValidationLoop",
    "UserInteractionBroker",
    "UserInteractionRequest",
]
