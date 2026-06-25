import json
from copy import deepcopy
from pathlib import Path


DEMO_DIR = Path(__file__).resolve().parent

DEMO_STORES = {
    "coffee": {
        "label": "ร้านกาแฟ",
        "file_name": "coffee_demo.json",
    },
    "restaurant": {
        "label": "ร้านอาหาร",
        "file_name": "restaurant_demo.json",
    },
    "clothing": {
        "label": "ร้านเสื้อผ้า",
        "file_name": "clothing_demo.json",
    },
    "beauty": {
        "label": "ร้านบิวตี้",
        "file_name": "beauty_demo.json",
    },
    "construction": {
        "label": "ร้านวัสดุก่อสร้าง",
        "file_name": "construction_demo.json",
    },
    "online_store": {
        "label": "ร้านค้าออนไลน์",
        "file_name": "online_store_demo.json",
    },
}

SESSION_KEYS = (
    "store_profile",
    "business_memory",
    "business_goals",
    "business_diagnosis",
    "business_os",
    "knowledge_layer",
    "chat_examples",
    "content_examples",
)


def list_demo_stores() -> list[dict]:
    """Return available demo stores for selectors."""
    return [
        {
            "key": store_key,
            "label": config["label"],
            "file_name": config["file_name"],
        }
        for store_key, config in DEMO_STORES.items()
    ]


def load_demo_store(store_key: str) -> dict:
    """Load one demo store JSON file by key."""
    if store_key not in DEMO_STORES:
        valid_keys = ", ".join(DEMO_STORES)
        raise ValueError(f"Unknown demo store key: {store_key}. Valid keys: {valid_keys}")

    demo_path = DEMO_DIR / DEMO_STORES[store_key]["file_name"]
    try:
        demo_data = json.loads(demo_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Demo file not found: {demo_path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid demo JSON: {demo_path}") from exc

    missing_keys = [key for key in SESSION_KEYS if key not in demo_data]
    if missing_keys:
        raise ValueError(
            f"Demo file {demo_path.name} is missing required keys: {', '.join(missing_keys)}"
        )

    return demo_data


def inject_demo_store_to_session(st, store_key: str) -> dict:
    """Load a demo store and write it into Streamlit session state."""
    demo_data = load_demo_store(store_key)

    st.session_state["demo_mode"] = True
    st.session_state["selected_demo_store"] = store_key
    for key in SESSION_KEYS:
        st.session_state[key] = deepcopy(demo_data[key])

    return demo_data
