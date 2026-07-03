from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


PERSPECTIVE_RUNTIME_VERSION = "5.8.1"
PERSPECTIVE_RUNTIME_SOURCE = "perspective_runtime"
PERSPECTIVE_DIAGNOSTICS_VERSION = "5.8.1"
UNKNOWN_SITUATION_FRAME = "UNKNOWN_SITUATION"
PERSPECTIVE_FOUNDATION_REASON = "Perspective frame recognition is not implemented in V5.8.1."


class PerspectiveFrameStatus(str, Enum):
    FOUNDATION_ONLY = "FOUNDATION_ONLY"


def _as_dict(value: Any) -> dict:
    return deepcopy(value) if isinstance(value, dict) else {}


def _source_layers(
    business_situation: dict,
    evidence_runtime: dict,
    truth_runtime: dict,
    evidence_gap_runtime: dict,
) -> dict:
    return {
        "business_situation": bool(business_situation),
        "evidence_runtime": bool(evidence_runtime),
        "truth_runtime": bool(truth_runtime),
        "evidence_gap_runtime": bool(evidence_gap_runtime),
    }


def _constitutional_invariants() -> dict:
    return {
        "routing_changed": False,
        "planner_changed": False,
        "workflow_changed": False,
        "responses_changed": False,
        "execution_changed": False,
        "commit_changed": False,
        "business_memory_changed": False,
        "business_situation_changed": False,
        "evidence_runtime_changed": False,
        "truth_runtime_changed": False,
        "evidence_gap_runtime_changed": False,
        "knowledge_invoked": False,
        "judgment_invoked": False,
        "decision_invoked": False,
        "recommendations_generated": False,
        "root_causes_diagnosed": False,
    }


@dataclass
class PerspectiveCandidateFrame:
    frame_id: str = ""
    frame_name: str = ""
    confidence: float = 0.0
    selection_reason: str = PERSPECTIVE_FOUNDATION_REASON
    diagnostic_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PerspectiveRuntime:
    selected_frame: str = UNKNOWN_SITUATION_FRAME
    candidate_frames: list = field(default_factory=list)
    frame_confidence: float = 0.0
    frame_selection_reason: str = PERSPECTIVE_FOUNDATION_REASON
    frame_status: str = PerspectiveFrameStatus.FOUNDATION_ONLY.value
    source_layers: dict = field(default_factory=dict)
    diagnostics_version: str = PERSPECTIVE_DIAGNOSTICS_VERSION
    constitutional_invariants: dict = field(default_factory=_constitutional_invariants)
    diagnostics: dict = field(default_factory=dict)
    version: str = PERSPECTIVE_RUNTIME_VERSION
    source: str = PERSPECTIVE_RUNTIME_SOURCE
    runtime_only: bool = True
    diagnostic_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


def build_perspective_runtime(
    *,
    business_situation: dict | None = None,
    evidence_runtime: dict | None = None,
    truth_runtime: dict | None = None,
    evidence_gap_runtime: dict | None = None,
) -> dict:
    """Create diagnostics-only Perspective Runtime foundation.

    Perspective Runtime is a shell in V5.8.1. It records that no situation
    frame recognition has run and does not classify, interpret, retrieve
    knowledge, judge, decide, recommend, alter behavior, or write memory.
    """

    situation = _as_dict(business_situation)
    situation_diagnostics = _as_dict(situation.get("diagnostics"))
    evidence = _as_dict(evidence_runtime) or _as_dict(situation_diagnostics.get("evidence"))
    truth = _as_dict(truth_runtime) or _as_dict(situation_diagnostics.get("truth"))
    evidence_gap = _as_dict(evidence_gap_runtime) or _as_dict(situation_diagnostics.get("evidence_gap"))
    invariants = _constitutional_invariants()
    sources = _source_layers(situation, evidence, truth, evidence_gap)
    diagnostics = {
        "perspective_runtime_created": True,
        "perspective_runtime_version": PERSPECTIVE_RUNTIME_VERSION,
        "perspective_runtime_source": PERSPECTIVE_RUNTIME_SOURCE,
        "diagnostics_version": PERSPECTIVE_DIAGNOSTICS_VERSION,
        "selected_frame": UNKNOWN_SITUATION_FRAME,
        "candidate_frame_count": 0,
        "frame_confidence": 0.0,
        "frame_selection_reason": PERSPECTIVE_FOUNDATION_REASON,
        "frame_status": PerspectiveFrameStatus.FOUNDATION_ONLY.value,
        "source_layers": deepcopy(sources),
        "constitutional_invariants": deepcopy(invariants),
        "diagnostic_only": True,
        "runtime_only": True,
        "reads_business_situation_diagnostics": True,
        "reads_evidence_runtime_diagnostics": True,
        "reads_truth_runtime_diagnostics": True,
        "reads_evidence_gap_runtime_diagnostics": True,
        "frame_recognition_implemented": False,
        "classification_performed": False,
        "knowledge_invoked": False,
        "judgment_invoked": False,
        "decision_invoked": False,
        "recommendations_generated": False,
        "root_causes_diagnosed": False,
        **invariants,
    }
    runtime = PerspectiveRuntime(
        source_layers=sources,
        constitutional_invariants=invariants,
        diagnostics=diagnostics,
    )
    return runtime.to_dict()
