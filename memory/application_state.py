from __future__ import annotations

from copy import deepcopy


APPLICATION_STATE_TEMPLATE = {
    "conversation": {},
    "workflow": {},
    "store": {},
    "receipt": {},
    "dashboard": {},
    "ui": {},
    "developer": {},
}


application_state = deepcopy(APPLICATION_STATE_TEMPLATE)


def reset_application_state() -> dict:
    application_state.clear()
    application_state.update(deepcopy(APPLICATION_STATE_TEMPLATE))
    return application_state


def ensure_application_state(state: dict | None = None) -> dict:
    target = state if isinstance(state, dict) else application_state
    for key, value in APPLICATION_STATE_TEMPLATE.items():
        target.setdefault(key, deepcopy(value))
    return target


def update_application_state(section: str, values: dict | None) -> dict:
    ensure_application_state()
    if section not in application_state:
        application_state[section] = {}
    if values:
        application_state[section].update(values)
    return application_state

