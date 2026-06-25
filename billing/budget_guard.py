from datetime import datetime


DAILY_BUDGET_USD = 0.15
MONTHLY_BUDGET_USD = 5.00


def get_today_key() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def get_month_key() -> str:
    return datetime.now().strftime("%Y-%m")


def get_llm_usage_state(st) -> dict:
    today_key = get_today_key()
    month_key = get_month_key()

    daily = st.session_state.setdefault("llm_usage_daily", {})
    monthly = st.session_state.setdefault("llm_usage_monthly", {})
    daily.setdefault(today_key, 0.0)
    monthly.setdefault(month_key, 0.0)

    return {
        "today_key": today_key,
        "month_key": month_key,
        "daily_used_usd": float(daily.get(today_key) or 0.0),
        "monthly_used_usd": float(monthly.get(month_key) or 0.0),
        "daily_budget_usd": DAILY_BUDGET_USD,
        "monthly_budget_usd": MONTHLY_BUDGET_USD,
    }


def can_call_llm(st) -> bool:
    usage = get_llm_usage_state(st)
    return (
        usage["daily_used_usd"] < DAILY_BUDGET_USD
        and usage["monthly_used_usd"] < MONTHLY_BUDGET_USD
    )


def record_llm_call(st, estimated_cost_usd) -> dict:
    usage = get_llm_usage_state(st)
    cost = max(0.0, float(estimated_cost_usd or 0.0))

    daily = st.session_state["llm_usage_daily"]
    monthly = st.session_state["llm_usage_monthly"]
    daily[usage["today_key"]] = float(daily.get(usage["today_key"]) or 0.0) + cost
    monthly[usage["month_key"]] = float(monthly.get(usage["month_key"]) or 0.0) + cost

    return get_llm_usage_state(st)
