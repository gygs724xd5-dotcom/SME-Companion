from __future__ import annotations

from dataclasses import asdict, dataclass
import re


FOLLOW_UP_RESOLUTION_VERSION = "5.9.4"


@dataclass
class FollowUpResolution:
    matched_gap_id: str = ""
    matched_metric_id: str = ""
    parsed_value: object = None
    parsed_unit: str = ""
    parsed_timeframe: str = ""
    answer_status: str = "UNRELATED"
    ambiguity: str = ""
    confidence: float = 0.0
    continuity_used: bool = False
    duplicate_question_resolved: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def _compact(text: str) -> str:
    return "".join(str(text or "").lower().split())


def _timeframe(text: str) -> str:
    compact = _compact(text)
    if any(token in compact for token in ["ต่อวัน", "วันละ", "perday", "day"]):
        return "day"
    if any(token in compact for token in ["ต่อรอบ", "รอบละ", "perbatch", "batch"]):
        return "batch"
    if any(token in compact for token in ["เดือนนี้", "เดือนก่อน", "month"]):
        return "this_month_vs_last_month" if "กับ" in compact or "vs" in compact else "month"
    return ""


def resolve_follow_up(user_message: str, prior_gap: dict | None = None, *, prior_context: dict | None = None) -> dict:
    gap = prior_gap or {}
    unresolved = (prior_context or {}).get("unresolved_gap_ids") or []
    metric_id = str(gap.get("metric_id") or (unresolved[0] if unresolved else ""))
    text = str(user_message or "")
    compact = _compact(text)
    timeframe = _timeframe(text)
    if any(token in compact for token in ["ไม่สะดวกบอก", "ไม่บอก", "decline", "notshare"]):
        return FollowUpResolution(metric_id, metric_id, answer_status="USER_DECLINED", confidence=0.9, continuity_used=bool(metric_id)).to_dict()
    if any(token in compact for token in ["แล้วแต่วัน", "ประมาณนั้น", "แล้วแต่", "around", "depends"]):
        return FollowUpResolution(metric_id, metric_id, parsed_timeframe=timeframe, answer_status="AMBIGUOUS", ambiguity="answer_not_specific_enough", confidence=0.45, continuity_used=bool(metric_id)).to_dict()
    numbers = [float(item.replace(",", "")) for item in re.findall(r"\d[\d,]*(?:\.\d+)?", text)]
    parsed_value = int(numbers[0]) if numbers and numbers[0].is_integer() else numbers[0] if numbers else None
    if metric_id == "output_time_period" and timeframe:
        return FollowUpResolution(metric_id, metric_id, parsed_value=timeframe, parsed_timeframe=timeframe, answer_status="ANSWERED", confidence=0.92, continuity_used=True, duplicate_question_resolved=True).to_dict()
    if metric_id in {"current_order_volume", "average_daily_sales"} and numbers:
        return FollowUpResolution(metric_id, metric_id, parsed_value=parsed_value, parsed_unit="pieces", parsed_timeframe=timeframe or "day" if "วัน" in text else timeframe, answer_status="ANSWERED", confidence=0.86, continuity_used=True, duplicate_question_resolved=True).to_dict()
    if metric_id == "analysis_timeframe" and timeframe:
        return FollowUpResolution(metric_id, metric_id, parsed_value=timeframe, parsed_timeframe=timeframe, answer_status="ANSWERED", confidence=0.86, continuity_used=True, duplicate_question_resolved=True).to_dict()
    if "ยอดขาย" in text or "revenue" in compact:
        status = "PARTIALLY_ANSWERED" if len(numbers) < 3 else "ANSWERED"
        return FollowUpResolution("total_revenue", "total_revenue", parsed_value=numbers, parsed_unit="THB", answer_status=status, confidence=0.8, continuity_used=bool(metric_id), duplicate_question_resolved=True).to_dict()
    if metric_id and (numbers or timeframe):
        return FollowUpResolution(metric_id, metric_id, parsed_value=parsed_value, parsed_timeframe=timeframe, answer_status="PARTIALLY_ANSWERED", confidence=0.65, continuity_used=True).to_dict()
    return FollowUpResolution(answer_status="UNRELATED", confidence=0.1).to_dict()
