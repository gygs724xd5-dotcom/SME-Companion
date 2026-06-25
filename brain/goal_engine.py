import json
from datetime import datetime
from pathlib import Path


GOALS_FILE = Path(__file__).resolve().parent.parent / "data" / "business_goals.json"

GOAL_TYPES = {
    "monthly_sales",
    "content_consistency",
    "repeat_customers",
    "new_customers",
    "trust_building",
}

GOAL_LABELS = {
    "monthly_sales": "ยอดขายรายเดือน",
    "content_consistency": "ความสม่ำเสมอของคอนเทนต์",
    "repeat_customers": "ลูกค้าซื้อซ้ำ",
    "new_customers": "ลูกค้าใหม่",
    "trust_building": "สร้างความน่าเชื่อถือ",
}


def _store_key(store_name: str) -> str:
    return str(store_name or "").strip().lower()


def _empty_goals() -> dict:
    return {"stores": {}}


def _load_all_goals() -> dict:
    if not GOALS_FILE.exists():
        return _empty_goals()

    try:
        data = json.loads(GOALS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _empty_goals()

    if not isinstance(data, dict):
        return _empty_goals()
    data.setdefault("stores", {})
    return data


def _save_all_goals(goals: dict) -> None:
    GOALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    GOALS_FILE.write_text(
        json.dumps(goals, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _to_number(value, fallback=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(fallback)


def create_business_goal(
    store_name,
    goal_type,
    target_value,
    current_value=0,
    deadline=None,
) -> dict | None:
    key = _store_key(store_name)
    if not key:
        return None

    normalized_goal_type = str(goal_type or "").strip()
    if normalized_goal_type not in GOAL_TYPES:
        normalized_goal_type = "monthly_sales"

    goal = {
        "goal_type": normalized_goal_type,
        "goal_label": GOAL_LABELS[normalized_goal_type],
        "target_value": _to_number(target_value),
        "current_value": _to_number(current_value),
        "deadline": str(deadline or "").strip() or None,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }

    goals = _load_all_goals()
    store = goals.setdefault("stores", {}).setdefault(
        key,
        {"store_name": str(store_name or "").strip(), "goals": []},
    )
    store["store_name"] = str(store_name or "").strip()
    store.setdefault("goals", []).append(goal)
    store["active_goal"] = goal
    _save_all_goals(goals)
    return goal


def load_business_goals(store_name) -> list[dict]:
    key = _store_key(store_name)
    if not key:
        return []
    return _load_all_goals().get("stores", {}).get(key, {}).get("goals", [])


def get_active_business_goal(store_name) -> dict | None:
    key = _store_key(store_name)
    if not key:
        return None
    store = _load_all_goals().get("stores", {}).get(key, {})
    active_goal = store.get("active_goal")
    if active_goal:
        return active_goal
    goals = store.get("goals", [])
    return goals[-1] if goals else None


def evaluate_business_goal(
    store_name,
    goal_data,
    business_insight,
    recent_topics,
) -> dict:
    goal = goal_data or {}
    insight = business_insight or {}
    topics = recent_topics or []
    goal_type = goal.get("goal_type") or "monthly_sales"
    target_value = max(0.0, _to_number(goal.get("target_value")))
    current_value = max(0.0, _to_number(goal.get("current_value")))
    progress_pct = 0 if target_value <= 0 else min(100, round((current_value / target_value) * 100))
    gap_to_goal = max(0.0, target_value - current_value)

    missing_types = insight.get("missing_content_types") or []
    repeated_warning = str(insight.get("repeated_topic_warning") or "")
    has_repeated = "พบหัวข้อซ้ำ" in repeated_warning

    if progress_pct >= 100:
        goal_status = "สำเร็จแล้ว"
        goal_risk = "ต่ำ"
    elif progress_pct >= 70:
        goal_status = "ใกล้ถึงเป้าหมาย"
        goal_risk = "ต่ำ" if not missing_types else "กลาง"
    elif progress_pct >= 35:
        goal_status = "กำลังเดินหน้า"
        goal_risk = "กลาง"
    else:
        goal_status = "ต้องเร่งเครื่อง"
        goal_risk = "สูง" if missing_types or has_repeated else "กลาง"

    action_map = {
        "monthly_sales": [
            "ทำแคมเปญ 3 วันด้วยข้อเสนอที่ชัดเจน",
            "เพิ่มโพสต์รีวิวหรือหลักฐานก่อนโพสต์ขาย",
            "ติดตามจำนวนแชทจากแต่ละโพสต์ทุกวัน",
        ],
        "content_consistency": [
            "วางโพสต์ 7 วันให้ครบมุมความรู้ รีวิว เบื้องหลัง และโปร",
            "เลี่ยงหัวข้อซ้ำกับ 3 โพสต์ล่าสุด",
            "กำหนดเวลาลงโพสต์เดิมทุกวันเพื่อสร้างวินัย",
        ],
        "repeat_customers": [
            "ทำข้อเสนอเฉพาะลูกค้าเก่า",
            "โพสต์เตือนประโยชน์ของการซื้อซ้ำ",
            "ชวนลูกค้าเก่าทักเพื่อรับเซตแนะนำ",
        ],
        "new_customers": [
            "ทำโพสต์ลดความเสี่ยงครั้งแรก เช่น รีวิว วิธีสั่ง และคำถามที่พบบ่อย",
            "ทำโปรเริ่มต้นที่ไม่ลดคุณค่าร้าน",
            "อธิบายว่าลูกค้าใหม่ควรเริ่มจากสินค้าไหน",
        ],
        "trust_building": [
            "ลงรีวิวลูกค้าจริงหรือผลลัพธ์ก่อนขาย",
            "เปิดเบื้องหลังร้านหรือขั้นตอนการทำงาน",
            "ทำโพสต์ตอบข้อกังวลก่อนซื้อ",
        ],
    }
    recommended_actions = action_map.get(goal_type, action_map["monthly_sales"])
    if missing_types:
        recommended_actions = [
            f"เติมคอนเทนต์ที่ยังขาด: {', '.join(missing_types[:2])}",
            *recommended_actions[:2],
        ]

    next_best_action = recommended_actions[0]
    if goal_type == "content_consistency" and topics:
        next_best_action = f"โพสต์มุมใหม่ที่ไม่ซ้ำกับ {topics[0]}"

    return {
        "store_name": str(store_name or "").strip(),
        "goal_type": goal_type,
        "goal_label": GOAL_LABELS.get(goal_type, goal_type),
        "goal_status": goal_status,
        "progress_pct": progress_pct,
        "gap_to_goal": gap_to_goal,
        "goal_risk": goal_risk,
        "recommended_actions": recommended_actions[:3],
        "next_best_action": next_best_action,
        "target_value": target_value,
        "current_value": current_value,
        "deadline": goal.get("deadline"),
    }
