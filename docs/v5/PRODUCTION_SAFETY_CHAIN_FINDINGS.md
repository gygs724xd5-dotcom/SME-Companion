# Production Safety Chain Findings Register

Review: `PSC-ARCH-REVIEW-R1`  
Baseline: `265b423dd32444d17d48a2a6ca084a2db8290b67`

No Critical findings identified from the reviewed scope.

## Findings

### PSC-H-001 — Operational failure-containment coverage is incomplete

- **Severity:** High
- **Affected modules:** `production_failure_containment_acceptance`, `production_rollback_evidence_foundation`, `controlled_production_activation_qualification`
- **Evidence:** `production_failure_containment_acceptance.py` declares `ACTUAL_EXECUTOR_OR_CALCULATOR_FAILURE`, `ACTUAL_DELIVERY_FAILURE`, `ACTUAL_PRODUCTION_RESPONSE_EXCEPTION`, and `DEPLOYED_PRODUCTION_INCIDENT` in `UNCOVERED_BOUNDARIES` (lines 73–80). V5.15.24.7.4.22 nevertheless requires this report as the failure-containment prerequisite (lines 183–195).
- **Why it matters:** A structurally qualified chain does not yet prove containment for the operational paths an activation executor would introduce.
- **Current mitigation:** Default-deny remains intact; qualification creates no permission or executor.
- **Recommended action:** Before any gate activation, add canonical containment evidence for actual executor, delivery, response-exception, and deployed-incident paths, or constrain the activation design so those paths cannot run.
- **Action timing:** Must fix before any gate activation.

### PSC-M-001 — Runtime artifact continuity depends on object identity

- **Severity:** Medium
- **Affected modules:** `production_rollback_evidence_foundation`, `production_deployment_rollback_attestation_foundation`, `controlled_production_activation_qualification`
- **Evidence:** rollback evidence requires the release-owner singleton with `is` (line 137); attestation foundation requires deployment/readiness/rollback/containment object identity (lines 218–222); qualification repeats identity continuity (lines 196–198).
- **Why it matters:** Correct artifacts reconstructed from canonical serialization cannot pass across process boundaries, persistence, queues, or restarts solely through value/digest equality.
- **Current mitigation:** In-process substitution resistance is strong; canonical IDs and digests are also present.
- **Recommended action:** Retain `is` for explicit code-owned singletons only. Define durable verification using exact type, canonical ID, schema/version, and digest for replayable artifacts.
- **Action timing:** Before operational activation implementation.

### PSC-M-002 — Nested verification produces quadratic-like practical cost

- **Severity:** Medium
- **Affected modules:** V5.15.24.7.4.18–22 verifiers and tests
- **Evidence:** each verifier reconstructs its expected artifact and calls upstream verifiers; V5.15.24.7.4.22 calls acceptance, foundation, deployment, rollback, readiness, and containment verifiers (lines 177–198). Observed focused execution grew to 458 seconds for 78 V5.15.24.7.4.22 tests; V5.15.24.7.4.21–22 combined took about 754 seconds.
- **Why it matters:** Verification latency, CI duration, and denial-of-service exposure grow rapidly with chain depth and tamper-case count.
- **Current mitigation:** Inputs are immutable and deterministic; repeated verification improves safety isolation.
- **Recommended action:** Design an immutable verification context keyed by root digest, with verified sub-results cached only within one call/session. Preserve independent strict verifier entry points.
- **Action timing:** Before operational activation implementation; performance refactor after baseline freeze.

### PSC-M-003 — Canonical serialization is duplicated across layers

- **Severity:** Medium
- **Affected modules:** all V5.15.24.7.4.16–22 core modules
- **Evidence:** each module independently defines `_canonical`, `_digest`, and `_material` (for example rollback readiness lines 104–123, deployment artifact lines 107–126, attestation foundation lines 151–170, qualification lines 137–154).
- **Why it matters:** A future local change in list/tuple, mapping, numeric, or dataclass handling could silently create incompatible digest semantics.
- **Current mitigation:** Current implementations use compatible SHA-256, versioned labels, deterministic field order, and sorted mapping keys.
- **Recommended action:** After baseline freeze, introduce a versioned canonical-serialization package and cross-module conformance vectors. Do not refactor during activation work.
- **Action timing:** Safe refactoring after baseline freeze.

### PSC-L-001 — Rejection status is generally not an immutable audit artifact

- **Severity:** Low
- **Affected modules:** V5.15.24.7.4.18–22 constructors/classifiers
- **Evidence:** invalid constructors return `None`; separate classifier functions map that outcome to a rejected string (for example rollback readiness lines 199–216 and qualification lines 255–266).
- **Why it matters:** A caller can know rejection status but does not receive a canonical rejected object containing ordered issues and a digest for durable audit.
- **Current mitigation:** Fail-closed behavior is unambiguous and no permission is created.
- **Recommended action:** Decide in the next design phase whether operational audit requires immutable rejection receipts. Do not retrofit casually because it changes digest contracts.
- **Action timing:** Design decision before operational activation; implementation only if audit requirements demand it.

### PSC-L-002 — Status vocabulary is semantically dense

- **Severity:** Low
- **Affected modules:** readiness, attestation acceptance, qualification
- **Evidence:** `ACCEPTED` and `QUALIFIED` statuses coexist with fields such as `readiness_evidence_permitted`, while all operational permission fields remain false.
- **Why it matters:** Integrators may misread accepted/qualified as approved/permitted despite correct code boundaries.
- **Current mitigation:** Docstrings, explicit false fields, policy checks, and tests consistently state non-operational meaning.
- **Recommended action:** Publish a status taxonomy and integration rule: only a future authority decision may produce operational permission.
- **Action timing:** Documentation before the next design phase completes.

## Observations

### PSC-O-001 — Safety redundancy is intentional and valuable

Exact-type checks, digest reconstruction, ordered-check verification, and repeated false-boundary checks are duplicated by design. They should not be removed merely to reduce line count.

### PSC-O-002 — V5.15.24.7.4.16 process termination remains unexplained

The V5.15.24.7.4.16 suite has repeatedly displayed progress without returning a final summary before task timeouts. This review did not modify test infrastructure or claim a root cause. Investigate process/thread teardown, fixture lifecycle, and external plugin interaction separately.

## Decision Impact

The findings support `GO_WITH_REQUIRED_REMEDIATIONS` for the next **design** phase. They do not authorize activation, transition approval, deployment, rollback, or runtime mutation.
