from __future__ import annotations

import ast
import copy
import dataclasses
import inspect
from pathlib import Path

import pytest

from brain.production_feature_gate_owner import (
    LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
    PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION,
    create_production_feature_gate_configuration,
    evaluate_production_feature_gate,
)
from brain.production_feature_gate_release_owner import (
    PROPOSED_NOT_AUTHORIZED,
    create_production_feature_gate_transition_proposal,
    get_production_feature_gate_release_owner,
)
from brain.production_feature_gate_transition_approval import (
    NO_TRANSITION_REQUIRED,
    PRODUCTION_FEATURE_GATE_TRANSITION_APPROVAL_SCOPE,
    PRODUCTION_FEATURE_GATE_TRANSITION_APPROVAL_VERSION,
    TRANSITION_NOT_APPROVED,
    ProductionFeatureGateApprovalAuthorityBoundary,
    create_production_feature_gate_transition_approval_request,
    evaluate_production_feature_gate_transition_approval,
    get_production_feature_gate_approval_owner,
    verify_production_feature_gate_approval_owner,
    verify_production_feature_gate_approval_requirement,
    verify_production_feature_gate_transition_approval_decision,
    verify_production_feature_gate_transition_approval_request,
)
from brain.production_turn_context import create_production_turn_context


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "brain" / "production_feature_gate_transition_approval.py"
APP = ROOT / "app.py"
GATE = LIMITED_COST_RESPONSE_RUNTIME_BRIDGE
REQUIREMENTS = (
    "RELEASE_OWNER_VERIFIED", "CURRENT_DEFAULT_DENY_CONFIGURATION_VERIFIED",
    "TRANSITION_PROPOSAL_VERIFIED", "ROLLBACK_TARGET_VERIFIED",
    "READ_ONLY_RELEASE_WIRING_ACCEPTED", "GATE_ENABLED_PREAUTH_QUALIFIED",
    "EXECUTABLE_REQUEST_QUALIFIED", "ISOLATED_CONTROLLED_RUNTIME_ACCEPTED",
    "PRODUCTION_FAILURE_CONTAINMENT_ACCEPTED", "DEPLOYMENT_ROLLBACK_ATTESTED",
)


def artifacts(state=True):
    owner = get_production_feature_gate_release_owner()
    proposal = create_production_feature_gate_transition_proposal(GATE, state)
    request = create_production_feature_gate_transition_approval_request(owner, proposal)
    decision = evaluate_production_feature_gate_transition_approval(request)
    return owner, proposal, request, decision


def test_version_scope_and_exact_compatibility_artifacts():
    owner, proposal, request, decision = artifacts()
    assert PRODUCTION_FEATURE_GATE_TRANSITION_APPROVAL_VERSION == "5.15.24.7.4.8"
    assert PRODUCTION_FEATURE_GATE_TRANSITION_APPROVAL_SCOPE == "TRUSTED_RELEASE_CONTROLLED_FEATURE_GATE_TRANSITION_APPROVAL"
    assert proposal.status == PROPOSED_NOT_AUTHORIZED and proposal.requested_gate_state is True
    assert request.release_owner is owner and request.proposal is proposal
    assert request.release_revision_id == owner.release_revision.revision_id
    assert request.configuration_digest == owner.configuration_digest
    assert request.rollback_digest == owner.rollback_target.rollback_digest
    assert verify_production_feature_gate_transition_approval_request(request)
    assert verify_production_feature_gate_transition_approval_decision(decision)


def test_approval_owner_exact_no_argument_singleton_immutable_and_deterministic():
    one = get_production_feature_gate_approval_owner()
    two = get_production_feature_gate_approval_owner()
    assert one is two and copy.deepcopy(one) is one
    assert verify_production_feature_gate_approval_owner(one)
    assert inspect.signature(get_production_feature_gate_approval_owner).parameters == {}
    assert len(one.owner_digest) == 64 and one.owner_digest.islower()
    with pytest.raises(dataclasses.FrozenInstanceError):
        one.activation_permitted = True


def test_owner_is_exact_current_release_default_deny_no_transition_or_permission():
    approval = get_production_feature_gate_approval_owner()
    release = get_production_feature_gate_release_owner()
    assert approval.release_owner is release
    assert release.configuration is PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION
    assert release.configuration.gate_entries == ()
    assert approval.transition_applied is approval.transition_approved is False
    assert approval.application_permitted is approval.activation_permitted is False
    assert approval.mutation_permitted is False and approval.executable_output is None
    assert approval.approved_enable_proposal is None
    assert not any(dataclasses.astuple(approval.authority_boundary))


def test_enable_is_verified_but_deterministically_not_approved():
    _, proposal, _, decision = artifacts(True)
    assert proposal.requested_gate_state is True
    assert decision.proposal_verified is True
    assert decision.status == TRANSITION_NOT_APPROVED
    assert decision.primary_denial == "READ_ONLY_RELEASE_WIRING_ACCEPTED"
    assert decision.transition_approved is decision.application_permitted is False
    assert decision.activation_permitted is decision.transition_applied is False
    assert decision.executable_output is None


def test_requirement_inventory_order_availability_and_no_fake_digest():
    *_, decision = artifacts(True)
    assert tuple(item.requirement_id for item in decision.requirements) == REQUIREMENTS
    assert all(item.required is True for item in decision.requirements)
    assert all(item.verified and item.evidence_digest for item in decision.requirements[:4])
    assert all(not item.verified and item.evidence_digest is None for item in decision.requirements[4:])
    assert all(verify_production_feature_gate_approval_requirement(item) for item in decision.requirements)
    assert decision.reasons == tuple(item.reason for item in decision.requirements[4:])


def test_noop_default_deny_is_no_transition_required_without_permission_or_mutation():
    owner, proposal, request, decision = artifacts(False)
    assert proposal.requested_gate_state is owner.configured_state is False
    assert decision.status == NO_TRANSITION_REQUIRED and decision.primary_denial is None
    assert decision.reasons == ("requested state already equals the exact current default-deny state; no transition required",)
    assert decision.proposal_verified is True
    assert decision.transition_approved is decision.application_permitted is False
    assert decision.activation_permitted is decision.transition_applied is False
    assert evaluate_production_feature_gate_transition_approval(request) == decision


def test_owner_configuration_and_evaluator_unchanged_before_after_decisions():
    owner = get_production_feature_gate_release_owner()
    before = (owner.owner_digest, owner.configuration.source_digest, owner.configuration.gate_entries)
    context = create_production_turn_context("approval", 1, "cost")
    evaluation_before = evaluate_production_feature_gate(owner.configuration, context, GATE)
    artifacts(True); artifacts(False)
    evaluation_after = evaluate_production_feature_gate(owner.configuration, context, GATE)
    assert get_production_feature_gate_release_owner() is owner
    assert before == (owner.owner_digest, owner.configuration.source_digest, owner.configuration.gate_entries)
    assert evaluation_before == evaluation_after
    assert (evaluation_after.configured_state, evaluation_after.effective_state, evaluation_after.default_denied) == (False, False, True)


def test_request_rejects_noncanonical_owner_historical_enabled_and_proposal_substitution():
    owner, proposal, _, _ = artifacts()
    assert create_production_feature_gate_transition_approval_request(dataclasses.replace(owner), proposal) is None
    enabled = create_production_feature_gate_configuration(
        owner.configuration.trusted_source_identity, ((GATE, True),)
    )
    assert create_production_feature_gate_transition_approval_request(enabled, proposal) is None
    assert create_production_feature_gate_transition_approval_request(owner, dataclasses.replace(proposal, requested_gate_name="*")) is None
    assert create_production_feature_gate_transition_approval_request(owner, owner.configuration) is None


@pytest.mark.parametrize("field,value", (
    ("version", "5.15.24.7.4.7"), ("scope", ""), ("approval_owner_digest", "0" * 64),
    ("release_owner_digest", "0" * 64), ("release_revision_id", "other"),
    ("configuration_digest", "0" * 64), ("proposal_digest", "0" * 64),
    ("rollback_digest", "0" * 64), ("request_digest", ""), ("request_digest", "A" * 64),
    ("request_digest", "g" * 64), ("request_digest", "0" * 63), ("request_digest", "0" * 65),
))
def test_request_tamper_and_malformed_digest_rejected(field, value):
    *_, request, _ = artifacts()
    assert not verify_production_feature_gate_transition_approval_request(dataclasses.replace(request, **{field: value}))


@pytest.mark.parametrize("mutation", (
    lambda d: dataclasses.replace(d, requirements=d.requirements[::-1]),
    lambda d: dataclasses.replace(d, requirements=d.requirements[:-1]),
    lambda d: dataclasses.replace(d, requirements=d.requirements + (d.requirements[-1],)),
    lambda d: dataclasses.replace(d, requirements=(d.requirements[0],) + d.requirements),
    lambda d: dataclasses.replace(d, requirements=(dataclasses.replace(d.requirements[0], requirement_id="UNKNOWN"),) + d.requirements[1:]),
))
def test_requirement_reorder_drop_duplicate_unknown_and_silent_drop_rejected(mutation):
    *_, decision = artifacts()
    assert not verify_production_feature_gate_transition_approval_decision(mutation(decision))


@pytest.mark.parametrize("field,value", (
    ("evidence_digest", "0" * 64), ("verified", True), ("required", False),
    ("reason", "passed"), ("requirement_digest", ""), ("requirement_digest", "A" * 64),
    ("requirement_digest", "g" * 64), ("requirement_digest", "0" * 63), ("requirement_digest", "0" * 65),
))
def test_missing_requirement_evidence_injection_and_digest_tamper_rejected(field, value):
    *_, decision = artifacts()
    item = dataclasses.replace(decision.requirements[4], **{field: value})
    altered = dataclasses.replace(decision, requirements=decision.requirements[:4] + (item,) + decision.requirements[5:])
    assert not verify_production_feature_gate_transition_approval_decision(altered)


@pytest.mark.parametrize("field,value", (
    ("proposal_verified", False), ("status", "APPROVED"), ("primary_denial", None),
    ("reasons", ("approved",)), ("transition_approved", True),
    ("application_permitted", True), ("activation_permitted", True),
    ("transition_applied", True), ("executable_output", "run"),
    ("decision_digest", ""), ("decision_digest", "A" * 64), ("decision_digest", "g" * 64),
    ("decision_digest", "0" * 63), ("decision_digest", "0" * 65),
    ("authority_boundary", dataclasses.replace(ProductionFeatureGateApprovalAuthorityBoundary(), approval=True)),
))
def test_decision_status_reason_permission_output_digest_and_authority_tamper_rejected(field, value):
    *_, decision = artifacts()
    assert not verify_production_feature_gate_transition_approval_decision(dataclasses.replace(decision, **{field: value}))


def test_cross_owner_proposal_and_rollback_substitution_rejected():
    owner, proposal, request, decision = artifacts()
    other = create_production_feature_gate_transition_proposal(GATE, False)
    assert not verify_production_feature_gate_transition_approval_request(dataclasses.replace(request, proposal=other))
    assert not verify_production_feature_gate_transition_approval_decision(dataclasses.replace(decision, proposal=other))
    bad_release = dataclasses.replace(owner, configuration_digest="0" * 64)
    assert not verify_production_feature_gate_transition_approval_decision(dataclasses.replace(decision, release_owner=bad_release))
    assert not verify_production_feature_gate_transition_approval_decision(dataclasses.replace(decision, rollback_digest="0" * 64))


def test_no_setter_mutation_or_caller_approval_argument_api():
    import brain.production_feature_gate_transition_approval as module
    public = {name for name in dir(module) if not name.startswith("_")}
    assert not public.intersection({"set", "update", "enable", "apply", "activate", "approve", "authorize"})
    for function in (create_production_feature_gate_transition_approval_request,
                     evaluate_production_feature_gate_transition_approval):
        names = set(inspect.signature(function).parameters)
        assert not names.intersection({"approved", "trusted", "approval_verified", "application_permitted",
                                       "activation_permitted", "approver", "signature", "tests_passed", "smoke_passed"})


def test_source_isolation_no_external_authority_or_execution_claims():
    source = MODULE.read_text(encoding="utf-8").lower()
    for forbidden in (
        "import os", "os.getenv", "os.environ", "streamlit", "session_state", "st.secrets",
        "query_params", "requests", "socket", "subprocess", "open(", "write(", "app.py",
        "calculator", "deliver_response(", "admission_gateway", "import llm", "human reviewer", "signature verified",
        "ci verified", "deployment verified", "smoke passed", "2239", "187",
    ):
        assert forbidden not in source
    roots = {alias.name.split(".")[0] for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Import) for alias in node.names}
    assert not roots.intersection({"os", "streamlit", "requests", "socket", "subprocess"})


def test_app_and_historical_contracts_are_not_imported_or_modified_by_new_module():
    source = MODULE.read_text(encoding="utf-8")
    assert "import app" not in source and "production_feature_gate_release_runtime" not in source
    assert 'PRODUCTION_FEATURE_GATE_OWNER_VERSION = "5.15.24.5"' in (ROOT / "brain" / "production_feature_gate_owner.py").read_text(encoding="utf-8")
    assert 'PRODUCTION_FEATURE_GATE_RELEASE_OWNER_VERSION = "5.15.24.7.4.6"' in (ROOT / "brain" / "production_feature_gate_release_owner.py").read_text(encoding="utf-8")
    assert APP.exists()
