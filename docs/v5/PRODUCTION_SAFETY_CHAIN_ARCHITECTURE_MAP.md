# Production Safety Chain Architecture Map

Baseline: `265b423dd32444d17d48a2a6ca084a2db8290b67`

## End-to-End Safety Chain

```mermaid
flowchart TD
    P["ProductionFeatureGateTransitionProposal"] --> R["ProductionFeatureGateReleaseRevision"]
    R --> G["ProductionFeatureGateReleaseOwnerSnapshot<br/>default-deny configuration + rollback target"]
    F["ProductionFailureContainmentAcceptanceReport<br/>V5.15.24.7.4.16"] --> RB["ProductionRollbackEvidenceFoundation<br/>V5.15.24.7.4.17"]
    P --> RB
    G --> RB
    RB --> RR["ProductionRollbackReadinessAcceptance<br/>V5.15.24.7.4.18"]
    RR --> DA["ProductionDeploymentArtifactEvidence<br/>V5.15.24.7.4.19"]
    DA --> AF["ProductionDeploymentRollbackAttestationFoundation<br/>V5.15.24.7.4.20"]
    RB --> AF
    RR --> AF
    F --> AF
    AF --> AA["ProductionDeploymentRollbackAttestationAcceptance<br/>V5.15.24.7.4.21"]
    AA --> Q["ControlledProductionActivationQualification<br/>V5.15.24.7.4.22"]
    Q --> N["No activation authority yet"]
```

## Module Dependency Graph

```mermaid
flowchart LR
    O["production_feature_gate_owner"] --> RO["production_feature_gate_release_owner"]
    FC0["verifiable_isolated_failure_containment_record"] --> FC["production_failure_containment_acceptance"]
    FC1["immutable_failure_response_state_containment"] --> FC
    O --> FC
    RO --> RB["production_rollback_evidence_foundation"]
    O --> RB
    FC --> RB
    RB --> RR["production_rollback_readiness_acceptance"]
    RR --> DA["production_deployment_artifact_evidence_foundation"]
    DA --> AF["production_deployment_rollback_attestation_foundation"]
    RB --> AF
    RR --> AF
    FC --> AF
    AF --> AA["production_deployment_rollback_attestation_acceptance"]
    RR --> AA
    AA --> Q["controlled_production_activation_qualification"]
    AF --> Q
    DA --> Q
    RB --> Q
    RR --> Q
    FC --> Q
```

No circular import was identified in the reviewed core chain. Dependencies point from downstream aggregation layers toward upstream evidence layers.

## Evidence and Digest Lineage

```mermaid
flowchart TD
    C["Configuration digest"] --> RD["Rollback target/artifact digests"]
    PD["Proposal digest"] --> RD
    FD["Failure containment report + topology digests"] --> RBF["Rollback foundation digest"]
    RD --> RBF
    RBF --> RA["Rollback readiness acceptance digest"]
    RA --> DD["Deployment artifact identity/content/evidence digests"]
    DD --> SD["Attestation subject digest"]
    RBF --> SD
    FD --> SD
    SD --> AFD["Attestation foundation digest"]
    AFD --> AAD["Attestation acceptance digest"]
    AAD --> QD["Qualification digest"]
```

## Authority and Operational Boundary

```mermaid
flowchart LR
    E["Evidence construction"] --> V["Strict verification"] --> Q["Qualification"]
    Q -. "does not imply" .-> A["Approval authority"]
    Q -. "does not imply" .-> X["Activation executor"]
    Q -. "does not imply" .-> D["Deployment/rollback executor"]
    B["All operational boundary flags = false"] --> E
    DD["Production default-deny"] --> E
```

## Qualification Versus Activation Boundary

```mermaid
stateDiagram-v2
    [*] --> DefaultDeny
    DefaultDeny --> EvidencePrepared: pure construction
    EvidencePrepared --> EvidenceAccepted: strict verification
    EvidenceAccepted --> Qualified: safety-chain qualification
    Qualified --> Qualified: no permission created
    state "Not implemented in reviewed scope" as FutureAuthority
    Qualified --> FutureAuthority: requires separate canonical authority design
```

## Node Reference

| Node | Status | Input | Output verifier | Operational boundary | Consumer |
|---|---|---|---|---|---|
| Failure containment | `PRODUCTION_FAILURE_CONTAINMENT_ACCEPTED` | batch + state binding | report verifier | no deployment/rollback authority | rollback foundation |
| Rollback evidence | `ROLLBACK_EVIDENCE_BOUND_NOT_ATTESTED` | owner + proposal + containment | foundation verifier | all authority false | readiness |
| Rollback readiness | `ROLLBACK_READINESS_ACCEPTED` | rollback foundation | acceptance verifier | no execution | deployment/attestation |
| Deployment artifact | `DEPLOYMENT_ARTIFACT_EVIDENCE_PREPARED` | readiness | evidence verifier | no deployment | attestation foundation |
| Attestation foundation | `DEPLOYMENT_ROLLBACK_ATTESTATION_PREPARED` | deployment + rollback + readiness + containment | foundation verifier | no successful attestation | acceptance |
| Attestation acceptance | `DEPLOYMENT_ROLLBACK_ATTESTATION_ACCEPTED` | prepared foundation | acceptance verifier | no operational attestation | qualification |
| Activation qualification | `CONTROLLED_PRODUCTION_ACTIVATION_QUALIFIED` | attestation acceptance | qualification verifier | no permission/activation | none |

