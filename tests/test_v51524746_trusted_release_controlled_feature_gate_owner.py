"""V5.15.24.7.4.6 trusted release-controlled gate owner contract."""
import ast
import copy
import dataclasses
from pathlib import Path

import pytest

from brain.production_feature_gate_owner import (
    GATE_MISSING_DEFAULT_DENY,
    LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
    PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION,
    evaluate_production_feature_gate,
    verify_production_feature_gate_configuration,
)
from brain.production_feature_gate_release_owner import (
    CURRENT_RELEASE_REVISION_ID,
    NO_TRANSITION_APPLIED,
    PRODUCTION_FEATURE_GATE_RELEASE_OWNER_SCOPE,
    PRODUCTION_FEATURE_GATE_RELEASE_OWNER_VERSION,
    PRODUCTION_RELEASE_CONTROLLED_DEFAULT_DENY_FEATURE_GATE_OWNER,
    PROPOSED_NOT_AUTHORIZED,
    SOURCE_CONTROLLED_RELEASE_CONFIGURATION,
    ProductionFeatureGateTransitionProposal,
    create_production_feature_gate_transition_proposal,
    get_production_feature_gate_release_owner,
    verify_production_feature_gate_release_owner,
    verify_production_feature_gate_release_revision,
    verify_production_feature_gate_rollback_target,
    verify_production_feature_gate_transition_proposal,
    verify_production_feature_gate_transition_record,
)
from brain.production_turn_context import create_production_turn_context


ROOT = Path(__file__).parents[1]
MODULE = ROOT / "brain" / "production_feature_gate_release_owner.py"
GATE = LIMITED_COST_RESPONSE_RUNTIME_BRIDGE


def test_exact_singleton_identity_version_scope_source_and_revision():
    owner = get_production_feature_gate_release_owner()
    assert owner is get_production_feature_gate_release_owner()
    assert owner is PRODUCTION_RELEASE_CONTROLLED_DEFAULT_DENY_FEATURE_GATE_OWNER
    assert owner.version == PRODUCTION_FEATURE_GATE_RELEASE_OWNER_VERSION == "5.15.24.7.4.6"
    assert owner.scope == PRODUCTION_FEATURE_GATE_RELEASE_OWNER_SCOPE
    assert owner.source_identity == SOURCE_CONTROLLED_RELEASE_CONFIGURATION
    assert owner.release_revision.revision_id == CURRENT_RELEASE_REVISION_ID
    assert verify_production_feature_gate_release_owner(owner)


def test_owner_is_frozen_deepcopy_equal_and_nested_collections_are_tuples():
    owner = get_production_feature_gate_release_owner()
    assert copy.deepcopy(owner) == owner
    assert isinstance(owner.supported_gate_registry, tuple)
    assert isinstance(owner.configuration.gate_entries, tuple)
    with pytest.raises(dataclasses.FrozenInstanceError):
        owner.effective_state = True


def test_underlying_historical_configuration_is_exact_and_verified():
    owner = get_production_feature_gate_release_owner()
    assert owner.configuration is PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION
    assert owner.release_revision.configuration is PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION
    assert owner.configuration.gate_entries == ()
    assert owner.configuration_digest == PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION.source_digest
    assert verify_production_feature_gate_configuration(owner.configuration)
    assert verify_production_feature_gate_release_revision(owner.release_revision)


def test_existing_evaluator_preserves_missing_default_deny_semantics():
    owner = get_production_feature_gate_release_owner()
    context = create_production_turn_context("release-owner-test", 1, "ต้นทุนต่อชิ้น")
    value = evaluate_production_feature_gate(owner.configuration, context, GATE)
    assert value.configured_state is False
    assert value.effective_state is False
    assert value.default_denied is True
    assert value.evaluation_reason == GATE_MISSING_DEFAULT_DENY
    assert value.activation_permitted is False


def test_owner_current_state_permissions_and_authority_are_all_false():
    owner = get_production_feature_gate_release_owner()
    assert (owner.configured_state, owner.effective_state, owner.default_denied) == (False, False, True)
    assert owner.transition_applied is False and owner.rollback_available is True
    assert owner.activation_permitted is False and owner.mutation_permitted is False
    assert owner.executable_output is None
    assert all(getattr(owner.authority_boundary, field.name) is False
               for field in dataclasses.fields(owner.authority_boundary))


def test_owner_digest_is_deterministic_lowercase_sha256_and_bound():
    one = get_production_feature_gate_release_owner()
    two = get_production_feature_gate_release_owner()
    assert one.owner_digest == two.owner_digest
    assert len(one.owner_digest) == 64 and one.owner_digest.islower()
    assert set(one.owner_digest) <= set("0123456789abcdef")


def test_rollback_target_is_exact_current_empty_configuration_not_applied():
    owner = get_production_feature_gate_release_owner()
    rollback = owner.rollback_target
    assert verify_production_feature_gate_rollback_target(rollback)
    assert rollback.target_revision_id == CURRENT_RELEASE_REVISION_ID
    assert rollback.target_configuration is PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION
    assert rollback.target_entries == ()
    assert rollback.rollback_available is True and rollback.rollback_applied is False
    assert rollback.activation_permitted is False and rollback.mutation_permitted is False
    assert rollback.executable_output is None


@pytest.mark.parametrize("state", (True, False))
def test_proposal_is_deterministic_non_authoritative_evidence(state):
    first = create_production_feature_gate_transition_proposal(GATE, state)
    second = create_production_feature_gate_transition_proposal(GATE, state)
    assert first == second and first.proposal_digest == second.proposal_digest
    assert verify_production_feature_gate_transition_proposal(first)
    assert first.status == PROPOSED_NOT_AUTHORIZED
    assert first.transition_applied is False and first.approval_verified is False
    assert first.activation_permitted is False and first.mutation_permitted is False
    assert first.executable_output is None


def test_future_enable_proposal_does_not_mutate_owner_or_evaluator_result():
    owner = get_production_feature_gate_release_owner()
    before_digest = owner.owner_digest
    proposal = create_production_feature_gate_transition_proposal(GATE, True)
    context = create_production_turn_context("proposal-test", 1, "วิเคราะห์ต้นทุน")
    value = evaluate_production_feature_gate(owner.configuration, context, GATE)
    assert proposal.requested_gate_state is True
    assert get_production_feature_gate_release_owner() is owner
    assert owner.owner_digest == before_digest and owner.configuration.gate_entries == ()
    assert value.configured_state is False and value.effective_state is False and value.default_denied is True


@pytest.mark.parametrize("field,value", (
    ("version", ""), ("version", "5.15.24.5"), ("source_identity", "caller"),
    ("source_revision_id", "other"), ("requested_gate_name", "*"),
    ("status", "APPROVED"), ("transition_applied", True), ("approval_verified", True),
    ("activation_permitted", True), ("mutation_permitted", True),
    ("executable_output", "run"), ("proposal_digest", ""),
    ("proposal_digest", "A" * 64), ("proposal_digest", "g" * 64),
    ("proposal_digest", "0" * 63), ("proposal_digest", "0" * 65),
))
def test_proposal_tampering_approval_activation_and_digest_rejected(field, value):
    proposal = create_production_feature_gate_transition_proposal(GATE, True)
    assert not verify_production_feature_gate_transition_proposal(
        dataclasses.replace(proposal, **{field: value})
    )


@pytest.mark.parametrize("name", ("", "limited_cost_response_runtime_bridge", "*", "GLOBAL", "ALL"))
def test_proposal_rejects_blank_alias_case_global_and_wildcard_gate(name):
    with pytest.raises(ValueError):
        create_production_feature_gate_transition_proposal(name, True)


@pytest.mark.parametrize("state", (1, 0, "true", None, (), []))
def test_proposal_requires_exact_boolean_requested_state(state):
    with pytest.raises(ValueError):
        create_production_feature_gate_transition_proposal(GATE, state)


def test_proposal_cannot_substitute_for_revision_owner_or_applied_configuration():
    proposal = create_production_feature_gate_transition_proposal(GATE, True)
    assert isinstance(proposal, ProductionFeatureGateTransitionProposal)
    assert not verify_production_feature_gate_release_revision(proposal)
    assert not verify_production_feature_gate_release_owner(proposal)
    assert not verify_production_feature_gate_configuration(proposal)


def test_canonical_no_transition_record_is_strict_and_deterministic():
    record = get_production_feature_gate_release_owner().transition_record
    assert verify_production_feature_gate_transition_record(record)
    assert record.status == NO_TRANSITION_APPLIED
    assert record.source_revision_id == record.target_revision_id == CURRENT_RELEASE_REVISION_ID
    assert record.previous_configuration_digest == record.current_configuration_digest
    assert record.transition_applied is False and record.approval_verified is False
    assert record.activation_permitted is False and record.mutation_permitted is False
    assert record.executable_output is None


@pytest.mark.parametrize("field,value", (
    ("status", "APPLIED"), ("source_revision_id", "other"),
    ("target_revision_id", "other"), ("current_configuration_digest", "0" * 64),
    ("transition_applied", True), ("approval_verified", True),
    ("activation_permitted", True), ("mutation_permitted", True),
    ("executable_output", "run"), ("transition_digest", "A" * 64),
))
def test_transition_record_tamper_and_authority_escalation_rejected(field, value):
    record = get_production_feature_gate_release_owner().transition_record
    assert not verify_production_feature_gate_transition_record(dataclasses.replace(record, **{field: value}))


@pytest.mark.parametrize("field,value", (
    ("target_revision_id", "other"), ("target_configuration_digest", "0" * 64),
    ("target_entries", ((GATE, False),)), ("rollback_available", False),
    ("rollback_applied", True), ("activation_permitted", True),
    ("mutation_permitted", True), ("executable_output", "run"),
    ("rollback_digest", "A" * 64),
))
def test_rollback_tamper_explicit_false_substitution_and_escalation_rejected(field, value):
    rollback = get_production_feature_gate_release_owner().rollback_target
    assert not verify_production_feature_gate_rollback_target(dataclasses.replace(rollback, **{field: value}))


@pytest.mark.parametrize("field,value", (
    ("version", ""), ("version", "5.15.24.5"), ("scope", ""),
    ("source_identity", "caller"), ("supported_gate_registry", (GATE, GATE)),
    ("supported_gate_registry", ("*",)), ("configuration_digest", "0" * 64),
    ("configured_state", True), ("effective_state", True), ("default_denied", False),
    ("transition_applied", True), ("rollback_available", False),
    ("activation_permitted", True), ("mutation_permitted", True),
    ("executable_output", "run"), ("owner_digest", ""),
    ("owner_digest", "A" * 64), ("owner_digest", "g" * 64),
    ("owner_digest", "0" * 63), ("owner_digest", "0" * 65),
))
def test_owner_strict_verifier_rejects_substitution_escalation_and_malformed_digest(field, value):
    owner = get_production_feature_gate_release_owner()
    assert not verify_production_feature_gate_release_owner(dataclasses.replace(owner, **{field: value}))


def test_no_runtime_mutation_setter_or_caller_boolean_trust_api():
    import brain.production_feature_gate_release_owner as module
    public = {name for name in dir(module) if not name.startswith("_")}
    forbidden = {"enable", "disable", "toggle", "set", "update", "patch",
                 "enable_gate", "disable_gate", "toggle_gate", "set_gate", "update_gate", "patch_gate"}
    assert not public.intersection(forbidden)
    lookup = ast.parse(MODULE.read_text(encoding="utf-8"))
    function = next(node for node in ast.walk(lookup) if isinstance(node, ast.FunctionDef)
                    and node.name == "get_production_feature_gate_release_owner")
    assert function.args.args == [] and function.args.kwonlyargs == []


def test_source_audit_has_no_external_runtime_configuration_or_forbidden_systems():
    source = MODULE.read_text(encoding="utf-8").lower()
    for forbidden in (
        "import os", "os.getenv", "os.environ", "streamlit", "st.secrets", "session_state",
        "query_params", "demo_mode", "dev_mode", "open(", "write(", "requests", "http",
        "socket", "subprocess", "admission_gateway", "import app", "git rev-parse",
        "cryptographic verification", "human approval verified",
    ):
        assert forbidden not in source
    tree = ast.parse(source)
    imported_roots = {
        alias.name.split(".")[0]
        for node in ast.walk(tree) if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    }
    assert not imported_roots.intersection(
        {"os", "streamlit", "requests", "socket", "subprocess", "llm"}
    )


def test_app_and_historical_owner_remain_unwired_and_unchanged_in_usage():
    app_source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "production_feature_gate_release_owner" not in app_source
    assert app_source.count("PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION") >= 2
    historical = (ROOT / "brain" / "production_feature_gate_owner.py").read_text(encoding="utf-8")
    assert 'PRODUCTION_FEATURE_GATE_OWNER_VERSION = "5.15.24.5"' in historical
    assert "PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION" in historical
