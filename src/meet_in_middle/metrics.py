from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Dict, Iterable, List


def gini(values: Iterable[float]) -> float:
    series = sorted(v for v in values if v >= 0)
    if not series:
        return 0.0
    n = len(series)
    cumulative = 0.0
    weighted_sum = 0.0
    for idx, value in enumerate(series, start=1):
        weighted_sum += value * idx
        cumulative += value
    if cumulative == 0:
        return 0.0
    return (2 * weighted_sum) / (n * cumulative) - (n + 1) / n


@dataclass(frozen=True)
class TravelStatistics:
    total_co2: float
    average_travel_hours: float
    median_travel_hours: float
    max_travel_hours: float
    min_travel_hours: float
    gini_travel_hours: float
    attendee_travel_hours: Dict[str, float]


def travel_stats(attendee_hours: Dict[str, float], attendee_counts: Dict[str, int], leg_co2: Dict[str, float]) -> TravelStatistics:
    expanded_hours: List[float] = []
    for office, hours in attendee_hours.items():
        expanded_hours.extend([hours] * attendee_counts.get(office, 0))
    if expanded_hours:
        avg_hours = sum(expanded_hours) / len(expanded_hours)
        med_hours = median(expanded_hours)
        max_hours = max(expanded_hours)
        min_hours = min(expanded_hours)
        gini_value = gini(expanded_hours)
    else:
        avg_hours = med_hours = max_hours = min_hours = gini_value = 0.0

    total_co2 = 0.0
    for office, co2 in leg_co2.items():
        total_co2 += co2 * attendee_counts.get(office, 0)

    return TravelStatistics(
        total_co2=total_co2,
        average_travel_hours=avg_hours,
        median_travel_hours=med_hours,
        max_travel_hours=max_hours,
        min_travel_hours=min_hours,
        gini_travel_hours=gini_value,
        attendee_travel_hours=attendee_hours,
    )
