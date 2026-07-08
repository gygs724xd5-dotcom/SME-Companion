from __future__ import annotations


DIRECT_SEMANTIC_ANSWER = "DIRECT_SEMANTIC_ANSWER"
DIRECT_BUSINESS_ANALYSIS = "DIRECT_BUSINESS_ANALYSIS"
CLARIFICATION_QUESTION = "CLARIFICATION_QUESTION"
START_WORKFLOW = "START_WORKFLOW"
CONTINUE_WORKFLOW = "CONTINUE_WORKFLOW"
COMPLETE_WORKFLOW = "COMPLETE_WORKFLOW"
REFUSE_WORKFLOW_MUTATION = "REFUSE_WORKFLOW_MUTATION"
LLM_ASSISTED_RESPONSE = "LLM_ASSISTED_RESPONSE"
RESET_ACKNOWLEDGEMENT = "RESET_ACKNOWLEDGEMENT"


_ACTIVE_WORKFLOW_STATUSES = {"collecting", "executing"}


def _normalized_text(value: str | None) -> str:
    return str(value or "").strip()


def _workflow_status(workflow: dict | None) -> str | None:
    if not isinstance(workflow, dict):
        return None

    status = workflow.get("workflow_status") or workflow.get("status") or workflow.get("step")
    if status is None or not isinstance(status, str):
        return None
    return str(status).strip().lower() or None


def _has_active_workflow(workflow: dict | None) -> bool:
    if not isinstance(workflow, dict) or not workflow:
        return False

    status = _workflow_status(workflow)
    if status in _ACTIVE_WORKFLOW_STATUSES:
        return True

    return bool(workflow.get("workflow_id") or workflow.get("workflow")) and status not in {
        None,
        "completed",
        "released",
        "end",
    }


def _decision(
    response_mode: str,
    *,
    workflow_allowed: bool,
    commit_required: bool = False,
    reason: str,
    diagnostics: dict,
) -> dict:
    return {
        "response_mode": response_mode,
        "workflow_allowed": bool(workflow_allowed),
        "commit_required": bool(commit_required),
        "reason": reason,
        "diagnostics": dict(diagnostics),
    }


def decide_response_authority(
    user_message: str,
    *,
    explicit_workflow_intent: bool = False,
    active_workflow: dict | None = None,
    completed_workflow_context: dict | None = None,
    reset_boundary_active: bool = False,
    evidence_sufficient: bool = True,
    semantic_correction_detected: bool = False,
    analytical_statement_detected: bool = False,
) -> dict:
    """Decide the authorized response mode for one user turn.

    This helper is pure: it does not call external services, mutate workflow
    state, or generate final response text.
    """
    message = _normalized_text(user_message)
    active_status = _workflow_status(active_workflow)
    has_active_workflow = _has_active_workflow(active_workflow)
    has_completed_context = isinstance(completed_workflow_context, dict) and bool(completed_workflow_context)
    reset_blocks_completed_reuse = bool(reset_boundary_active and has_completed_context)

    diagnostics = {
        "response_authority_version": "5.11.1",
        "user_message_present": bool(message),
        "explicit_workflow_intent": bool(explicit_workflow_intent),
        "active_workflow_present": has_active_workflow,
        "active_workflow_status": active_status,
        "completed_workflow_context_present": has_completed_context,
        "reset_boundary_active": bool(reset_boundary_active),
        "reset_boundary_respected": bool(reset_boundary_active),
        "completed_workflow_released": has_completed_context,
        "completed_workflow_reuse_blocked": reset_blocks_completed_reuse or has_completed_context,
        "evidence_sufficient": bool(evidence_sufficient),
        "semantic_correction_detected": bool(semantic_correction_detected),
        "analytical_statement_detected": bool(analytical_statement_detected),
        "llm_assistance_allowed": False,
    }

    if reset_boundary_active and not message:
        return _decision(
            RESET_ACKNOWLEDGEMENT,
            workflow_allowed=False,
            reason="reset_boundary_acknowledgement",
            diagnostics=diagnostics,
        )

    if semantic_correction_detected:
        return _decision(
            DIRECT_SEMANTIC_ANSWER,
            workflow_allowed=False,
            reason="semantic_correction_detected",
            diagnostics=diagnostics,
        )

    if analytical_statement_detected:
        return _decision(
            DIRECT_BUSINESS_ANALYSIS,
            workflow_allowed=False,
            reason="analytical_statement_detected",
            diagnostics=diagnostics,
        )

    if not evidence_sufficient:
        return _decision(
            CLARIFICATION_QUESTION,
            workflow_allowed=False,
            reason="insufficient_evidence",
            diagnostics=diagnostics,
        )

    if explicit_workflow_intent:
        if has_active_workflow and not reset_boundary_active:
            return _decision(
                CONTINUE_WORKFLOW,
                workflow_allowed=True,
                reason="explicit_workflow_intent_with_active_workflow",
                diagnostics=diagnostics,
            )
        return _decision(
            START_WORKFLOW,
            workflow_allowed=True,
            reason="explicit_workflow_intent_without_active_workflow",
            diagnostics=diagnostics,
        )

    diagnostics["llm_assistance_allowed"] = True
    return _decision(
        LLM_ASSISTED_RESPONSE,
        workflow_allowed=False,
        reason="fallback_llm_assisted_response",
        diagnostics=diagnostics,
    )
