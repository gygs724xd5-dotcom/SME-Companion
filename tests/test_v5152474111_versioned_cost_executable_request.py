from dataclasses import fields, replace
from datetime import datetime, timezone
import inspect

from brain.business_skill_cost_execution import CostExecutionRequest, execute_cost_skill
from brain.isolated_qualification_configuration_binding import *
from brain.isolated_gate_enabled_pre_authorization_qualification import *
from brain.production_feature_gate_owner import *
from brain.production_turn_context import create_production_turn_context
from brain.production_turn_reference_time import create_production_turn_reference_time
from brain.versioned_cost_executable_request import *


def chain(message="cost changed from 100 to 120 baht", turn=1):
    context = create_production_turn_context("request-foundation", turn, message)
    reference = create_production_turn_reference_time(context, datetime(2026, 7, 16, tzinfo=timezone.utc))
    config = create_production_feature_gate_configuration(PURE_TEST_TRUSTED_SOURCE_IDENTITY,
        ((LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, True),))
    evaluation = evaluate_production_feature_gate(config, context, LIMITED_COST_RESPONSE_RUNTIME_BRIDGE)
    binding = create_isolated_qualification_feature_gate_binding(context, reference, config, evaluation)
    evidence = create_isolated_qualification_skill_evidence_envelope(binding)
    limited = create_isolated_qualification_limited_activation_binding(evidence)
    foundation = create_isolated_qualification_pre_execution_result(limited)
    report = create_isolated_gate_enabled_pre_authorization_report(foundation)
    return foundation, report


def test_historical_contract_and_executor_signature_unchanged():
    assert tuple(f.name for f in fields(CostExecutionRequest)) == (
        "execution_id", "request_id", "requested_skill_id", "decision", "authority_inputs")
    assert tuple(inspect.signature(execute_cost_skill).parameters) == ("request", "policy")


def test_deterministic_standalone_request_and_integrity():
    foundation, report = chain()
    one = create_versioned_cost_executable_request(foundation, report)
    two = create_versioned_cost_executable_request(foundation, report)
    assert one == two and verify_versioned_cost_executable_request(one, foundation, report)
    assert all(verify_cost_executable_operand(x) for x in one.operands)
    assert verify_cost_executable_formula_binding(one.formula)
    assert verify_cost_executable_policy_binding(one.policy)
    assert tuple(x.semantic_role for x in one.operands) == ("previous_cost", "current_cost")
    assert one.formula.ordered_operand_roles == ("previous_cost", "current_cost")
    unit_foundation, unit_report = chain("ต้นทุนต่อชิ้น ต้นทุนรวม 300 บาท ทำได้ 20 ชิ้น")
    unit = create_versioned_cost_executable_request(unit_foundation, unit_report)
    assert verify_versioned_cost_executable_request(unit, unit_foundation, unit_report)
    assert unit.skill_id == "cost.per_unit_calculation.v1"
    assert tuple(x.semantic_role for x in unit.operands) == ("total_cost", "unit_quantity")
    assert unit.formula.ordered_operand_roles == ("total_cost", "unit_quantity")


def test_foundation_and_authority_remain_non_authorizing():
    foundation, report = chain()
    request = create_versioned_cost_executable_request(foundation, report)
    assert not foundation.requirement_qualified and not foundation.executable_request_qualified
    assert foundation.executable_request is None and not foundation.execute_allowed
    assert request.execution_result is None and not request.requirement_qualified
    assert not request.execute_allowed and not request.dispatch_permitted and not request.runtime_invocation_permitted


def test_tampering_cross_turn_and_old_type_fail_closed():
    foundation, report = chain()
    request = create_versioned_cost_executable_request(foundation, report)
    other_foundation, other_report = chain(turn=2)
    assert not verify_versioned_cost_executable_request(request, other_foundation, other_report)
    assert not verify_versioned_cost_executable_request(replace(request, request_digest="0" * 64), foundation, report)
    assert not verify_versioned_cost_executable_request(replace(request, execute_allowed=True), foundation, report)
    assert not verify_versioned_cost_executable_request(CostExecutionRequest("e", "r", request.skill_id, None), foundation, report)
    assert create_versioned_cost_executable_request(foundation, other_report) is None


def test_operand_formula_policy_and_topology_tampering_rejected():
    foundation, report = chain()
    request = create_versioned_cost_executable_request(foundation, report)
    operand = replace(request.operands[0], decimal_digits=(9,))
    mutations = (
        replace(request, operands=(operand,) + request.operands[1:]),
        replace(request, operands=tuple(reversed(request.operands))),
        replace(request, formula=replace(request.formula, formula_id="arbitrary")),
        replace(request, policy=replace(request.policy, policy_version="x")),
        replace(request, topology=tuple(reversed(request.topology))),
    )
    assert all(not verify_versioned_cost_executable_request(x, foundation, report) for x in mutations)
