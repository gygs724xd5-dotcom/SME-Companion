from dataclasses import fields, replace
from datetime import datetime, timezone

import brain.isolated_executable_request_qualification as owner
from brain.isolated_gate_enabled_pre_authorization_qualification import create_isolated_gate_enabled_pre_authorization_report
from brain.isolated_qualification_configuration_binding import *
from brain.production_feature_gate_owner import *
from brain.production_turn_context import create_production_turn_context
from brain.production_turn_reference_time import create_production_turn_reference_time
from brain.versioned_cost_executable_request import verify_versioned_cost_executable_request


def chain(message, ordinal):
    context = create_production_turn_context("request-qualification", ordinal, message)
    reference = create_production_turn_reference_time(context, datetime(2026, 7, 16, tzinfo=timezone.utc))
    config = create_production_feature_gate_configuration(PURE_TEST_TRUSTED_SOURCE_IDENTITY,
        ((LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, True),))
    evaluation = evaluate_production_feature_gate(config, context, LIMITED_COST_RESPONSE_RUNTIME_BRIDGE)
    binding = create_isolated_qualification_feature_gate_binding(context, reference, config, evaluation)
    evidence = create_isolated_qualification_skill_evidence_envelope(binding)
    limited = create_isolated_qualification_limited_activation_binding(evidence)
    foundation = create_isolated_qualification_pre_execution_result(limited)
    return foundation, create_isolated_gate_enabled_pre_authorization_report(foundation)


def inputs(waste=True):
    unit = "ต้นทุนต่อชิ้น ต้นทุนรวม 300 บาท ทำได้ 20 ชิ้น"
    if waste: unit += " ของเสีย 2 ชิ้น"
    return (chain("cost changed from 100 to 120 baht", 1), chain(unit, 2))


def test_both_skills_qualify_deterministically_and_contracts_are_frozen():
    report = owner.create_isolated_executable_request_qualification_report(inputs())
    assert report == owner.create_isolated_executable_request_qualification_report(inputs())
    assert owner.verify_isolated_executable_request_qualification_report(report)
    assert report.qualified and report.status == owner.STATUS
    assert (report.qualified_skill_count, report.failed_skill_count) == (2, 0)
    assert tuple(x.skill_id for x in report.observations) == owner.SUPPORTED_EXECUTABLE_REQUEST_SKILL_IDS
    for contract in (owner.IsolatedExecutableRequestScenario, owner.IsolatedExecutableRequestObservation,
                     owner.IsolatedExecutableRequestQualificationReport,
                     owner.IsolatedExecutableRequestQualificationAuthorityBoundary):
        assert contract.__dataclass_params__.frozen


def test_request_operand_formula_policy_and_optional_evidence_semantics():
    present = owner.create_isolated_executable_request_qualification_report(inputs(True))
    absent = owner.create_isolated_executable_request_qualification_report(inputs(False))
    for report in (present, absent):
        for observation in report.observations:
            request = observation.request
            assert verify_versioned_cost_executable_request(request, observation.foundation, observation.preauth_report)
            assert owner.verify_isolated_executable_request_observation(observation)
        unit = report.observations[1].request
        assert tuple(x.semantic_role for x in unit.operands if x.operand_used_by_formula) == ("total_cost", "unit_quantity")
        assert unit.formula.ordered_operand_roles == ("total_cost", "unit_quantity")
        assert all(x.semantic_role != "waste_or_loss_quantity" or not x.operand_used_by_formula
                   for x in unit.operands)


def test_foundations_remain_non_authorizing_and_all_invocations_are_zero():
    report = owner.create_isolated_executable_request_qualification_report(inputs())
    for observation in report.observations:
        foundation, request = observation.foundation, observation.request
        assert not foundation.requirement_qualified and not foundation.executable_request_qualified
        assert foundation.executable_request is None and not foundation.execute_allowed
        assert request.execution_result is None and not request.requirement_qualified
        assert not request.execute_allowed and not request.dispatch_permitted
    assert (report.calculator_invocation_count, report.bridge_invocation_count,
            report.admission_invocation_count, report.delivery_invocation_count,
            report.controlled_runtime_invocation_count) == (0, 0, 0, 0, 0)


def test_inventory_cross_skill_type_and_tampering_fail_closed():
    pairs = inputs(); report = owner.create_isolated_executable_request_qualification_report(pairs)
    assert owner.create_isolated_executable_request_qualification_report(tuple(reversed(pairs))) is None
    assert owner.create_isolated_executable_request_qualification_report(pairs[:1]) is None
    assert owner.create_isolated_executable_request_qualification_report((pairs[0], pairs[0])) is None
    assert not owner.verify_isolated_executable_request_qualification_report(replace(report, qualified=False))
    assert not owner.verify_isolated_executable_request_qualification_report(replace(report, report_digest="0" * 64))
    obs = report.observations[0]
    assert not owner.verify_isolated_executable_request_observation(replace(obs, request=report.observations[1].request))
    assert not owner.verify_isolated_executable_request_observation(replace(obs, observation_digest="0" * 64))


def test_fixed_scenarios_and_authority_boundary():
    report = owner.create_isolated_executable_request_qualification_report(inputs())
    assert len(set(owner.CANONICAL_SCENARIO_IDS)) == len(owner.CANONICAL_SCENARIO_IDS)
    for observation in report.observations:
        assert tuple(x.scenario_id for x in observation.scenarios) == owner.CANONICAL_SCENARIO_IDS
        assert all(not getattr(observation.authority_boundary, f.name) for f in fields(observation.authority_boundary))
