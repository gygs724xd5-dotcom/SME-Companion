from __future__ import annotations

from copy import deepcopy
from typing import Any

from brain.judgment_outcome import build_judgment_outcome


JUDGMENT_RESPONSE_HANDOFF_VERSION = "5.10.4"


def _as_dict(value: Any) -> dict:
    return deepcopy(value) if isinstance(value, dict) else {}


def build_judgment_response_handoff(judgment_result: dict | None, *, unsafe_output: str = "", revision_result: dict | None = None) -> dict:
    outcome = build_judgment_outcome(judgment_result, unsafe_output=unsafe_output, revision_result=revision_result)
    return {
        "judgment_response_handoff_created": True,
        "response_handoff": _as_dict(outcome.get("response_handoff")),
        "outcome": outcome,
        "response_commit_boundary_owner": "response_commit_boundary",
        "direct_response_commit": False,
        "version": JUDGMENT_RESPONSE_HANDOFF_VERSION,
    }

