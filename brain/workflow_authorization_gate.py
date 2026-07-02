from __future__ import annotations

from brain.workflow_state_machine import update_workflow_state


def planner_workflow_from_decision(planner_decision: dict | None, resolved_workflow: str | None = None) -> str | None:
    plan = planner_decision or {}
    return (
        resolved_workflow
        or plan.get("workflow")
        or ((plan.get("intent_resolution") or {}).get("resolved_workflow"))
    )


def workflow_id_from_state(workflow_state: dict | None) -> str | None:
    state = workflow_state or {}
    return state.get("workflow") or state.get("workflow_id") or state.get("current_workflow")


def authorize_workflow_mutation(
    *,
    authorized_workflow: str | None,
    candidate_workflow: str | None,
    current_state: dict | None = None,
) -> dict:
    current_workflow = workflow_id_from_state(current_state)
    candidate = candidate_workflow or current_workflow

    if not authorized_workflow:
        return _authorization(
            False,
            "planner_released_workflow",
            authorized_workflow,
            candidate,
            current_workflow,
        )
    if candidate != authorized_workflow:
        return _authorization(
            False,
            "candidate_workflow_not_authorized_by_planner",
            authorized_workflow,
            candidate,
            current_workflow,
        )
    return _authorization(
        True,
        "planner_authorized_workflow_mutation",
        authorized_workflow,
        candidate,
        current_workflow,
    )


def update_workflow_state_if_authorized(
    current_state: dict | None,
    user_message: str,
    *,
    authorized_workflow: str | None,
    detected_workflow: str | None = None,
    canonical_entities: dict | None = None,
) -> tuple[dict | None, dict, dict]:
    authorization = authorize_workflow_mutation(
        authorized_workflow=authorized_workflow,
        candidate_workflow=detected_workflow,
        current_state=current_state,
    )
    if not authorization["workflow_mutation_authorized"]:
        return current_state, {}, authorization

    workflow_state, extracted_fields = update_workflow_state(
        current_state,
        user_message,
        detected_workflow=detected_workflow,
        canonical_entities=canonical_entities,
    )
    return workflow_state, extracted_fields, authorization


def _authorization(
    allowed: bool,
    reason: str,
    authorized_workflow: str | None,
    candidate_workflow: str | None,
    current_workflow: str | None,
) -> dict:
    return {
        "workflow_mutation_authorized": allowed,
        "workflow_authorization_reason": reason,
        "authorized_workflow": authorized_workflow,
        "candidate_workflow": candidate_workflow,
        "current_workflow": current_workflow,
    }
