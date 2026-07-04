from __future__ import annotations

from dataclasses import asdict, dataclass, field

from brain.contract_provenance import ContractRename


CONTRACT_CHANGE_MANIFEST_VERSION = "5.9.2"


@dataclass(frozen=True)
class ContractChangeManifest:
    from_version: str
    to_version: str
    added_contracts: list[dict] = field(default_factory=list)
    modified_contracts: list[dict] = field(default_factory=list)
    deprecated_contracts: list[dict] = field(default_factory=list)
    removed_contracts: list[dict] = field(default_factory=list)
    renamed_contracts: list[dict] = field(default_factory=list)
    breaking_changes: list[dict] = field(default_factory=list)
    non_breaking_changes: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def build_contract_change_manifest(
    *,
    previous: dict | None = None,
    current: dict | None = None,
    renamed_contracts: list[ContractRename | dict] | None = None,
) -> dict:
    previous = previous or {}
    current = current or {}
    previous_contracts = previous.get("contracts") or {}
    current_contracts = current.get("contracts") or {}
    added = []
    modified = []
    removed = []
    for key, value in sorted(current_contracts.items()):
        if key not in previous_contracts:
            added.append({"contract_id": key, "contract": value})
        elif previous_contracts[key] != value:
            modified.append({"contract_id": key, "previous": previous_contracts[key], "current": value})
    for key, value in sorted(previous_contracts.items()):
        if key not in current_contracts:
            removed.append({"contract_id": key, "contract": value})
    renamed = [item.to_dict() if hasattr(item, "to_dict") else dict(item) for item in (renamed_contracts or [])]
    unapproved_renames = [item for item in renamed if not item.get("approved")]
    return ContractChangeManifest(
        from_version=str(previous.get("version") or ""),
        to_version=str(current.get("version") or ""),
        added_contracts=added,
        modified_contracts=modified,
        removed_contracts=removed,
        renamed_contracts=renamed,
        breaking_changes=removed + unapproved_renames,
        non_breaking_changes=added + modified,
    ).to_dict()
