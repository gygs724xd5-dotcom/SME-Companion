from __future__ import annotations

from copy import deepcopy
from types import MappingProxyType
from typing import Any


SIGNAL_REGISTRY_VERSION = "5.5.1"


_SIGNAL_TYPE_DEFINITIONS = {
    "user_message": {
        "signal_type": "user_message",
        "source": "user",
        "modality": "text",
        "description": "Current user message observed by Perception.",
    },
    "conversation_history": {
        "signal_type": "conversation_history",
        "source": "conversation",
        "modality": "reference",
        "description": "Prior conversation context reference observed by Perception.",
    },
    "business_memory_reference": {
        "signal_type": "business_memory_reference",
        "source": "business_memory",
        "modality": "reference",
        "description": "Business memory reference observed by Perception.",
    },
    "store_profile_reference": {
        "signal_type": "store_profile_reference",
        "source": "store_profile",
        "modality": "reference",
        "description": "Store profile reference observed by Perception.",
    },
    "uploaded_document": {
        "signal_type": "uploaded_document",
        "source": "upload",
        "modality": "document",
        "description": "Uploaded document observed by Perception.",
    },
    "uploaded_image": {
        "signal_type": "uploaded_image",
        "source": "upload",
        "modality": "image",
        "description": "Uploaded image observed by Perception.",
    },
    "dashboard_state": {
        "signal_type": "dashboard_state",
        "source": "dashboard",
        "modality": "structured_state",
        "description": "Dashboard state observed by Perception.",
    },
    "active_workspace": {
        "signal_type": "active_workspace",
        "source": "workspace",
        "modality": "runtime_state",
        "description": "Active workspace observed by Perception.",
    },
    "current_context": {
        "signal_type": "current_context",
        "source": "runtime_context",
        "modality": "structured_state",
        "description": "Current runtime context observed by Perception.",
    },
    "execution_result": {
        "signal_type": "execution_result",
        "source": "execution",
        "modality": "result_reference",
        "description": "Execution result observed by Perception.",
    },
}


SIGNAL_TYPE_DEFINITIONS = MappingProxyType(
    {key: MappingProxyType(value) for key, value in _SIGNAL_TYPE_DEFINITIONS.items()}
)


UNKNOWN_SIGNAL_TYPE_DEFINITION = MappingProxyType(
    {
        "signal_type": "unknown",
        "source": "unknown",
        "modality": "unknown",
        "description": "Unknown signal type. Perception preserves it without interpretation.",
    }
)


def list_signal_types() -> tuple[str, ...]:
    return tuple(sorted(SIGNAL_TYPE_DEFINITIONS.keys()))


def signal_type_exists(signal_type: str | None) -> bool:
    return str(signal_type or "") in SIGNAL_TYPE_DEFINITIONS


def get_signal_type_definition(signal_type: str | None) -> dict[str, Any]:
    value = str(signal_type or "")
    definition = SIGNAL_TYPE_DEFINITIONS.get(value, UNKNOWN_SIGNAL_TYPE_DEFINITION)
    return deepcopy(dict(definition))


def get_signal_types_by_source(source: str | None) -> tuple[str, ...]:
    source_value = str(source or "")
    return tuple(
        sorted(
            signal_type
            for signal_type, definition in SIGNAL_TYPE_DEFINITIONS.items()
            if definition.get("source") == source_value
        )
    )
