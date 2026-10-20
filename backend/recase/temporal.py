"""A small independent temporal feasibility baseline, never a guilt classifier."""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass(frozen=True)
class Observation:
    subject: str
    place: str
    at: datetime
    tolerance_seconds: float = 0
    identity_verified: bool = True

    def __post_init__(self):
        if self.at.tzinfo is None or self.at.utcoffset() is None:
            raise ValueError("An explicit timezone is required")
        if not 0 <= self.tolerance_seconds <= 86400:
            raise ValueError("Invalid clock tolerance")


def feasibility(first: Observation, second: Observation, minimum_travel_seconds: float | None):
    """Check instantaneous observations against known minimum travel time.

    POSSIBLE only describes temporal compatibility. It does not prove a visit,
    continuous residence, a true statement, or the identity of an unverified person.
    """
    if first.subject != second.subject or not first.identity_verified or not second.identity_verified:
        return {"label": "INSUFFICIENT", "reason": "동일인 식별이 확인되지 않았습니다."}
    if first.place == second.place:
        return {"label": "POSSIBLE", "reason": "같은 장소의 순간 기록입니다. 연속 체류를 입증하지 않습니다."}
    if minimum_travel_seconds is None:
        return {"label": "INSUFFICIENT", "reason": "장소 사이의 검증된 최소 이동시간이 필요합니다."}
    if minimum_travel_seconds < 0:
        raise ValueError("Minimum travel time must be non-negative")
    gap = abs((second.at - first.at).total_seconds())
    error = first.tolerance_seconds + second.tolerance_seconds
    if gap + error < minimum_travel_seconds:
        return {"label": "IMPOSSIBLE", "reason": "기록 오차를 고려해도 검증된 최소 이동시간보다 짧습니다."}
    if max(0, gap - error) >= minimum_travel_seconds:
        return {"label": "POSSIBLE", "reason": "검증된 최소 이동시간과 양립합니다. 실제 이동을 입증하지 않습니다."}
    return {"label": "INSUFFICIENT", "reason": "기록 오차 범위 때문에 이동 가능성을 확정할 수 없습니다."}
