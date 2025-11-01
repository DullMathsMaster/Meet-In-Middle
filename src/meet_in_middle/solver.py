from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Dict, List, Optional, Sequence, Tuple

from .data import Scenario, TravelDataset, format_iso8601
from .metrics import TravelStatistics, travel_stats
from .routing import Route, multi_objective_routes, select_route

DEFAULT_HOST_WEIGHTS = {
    "total_co2": 0.4,
    "average_travel_hours": 0.3,
    "gini_travel_hours": 0.2,
    "max_travel_hours": 0.1,
}


@dataclass(frozen=True)
class CandidateEvaluation:
    host: str
    stats: TravelStatistics
    per_office_route: Dict[str, Route]
    per_office_hours: Dict[str, float]
    per_office_co2: Dict[str, float]
    composite_score: float
    score_components: Dict[str, float]


def evaluate_host(
    scenario: Scenario,
    dataset: TravelDataset,
    host: str,
    route_preference: Tuple[float, float],
) -> Optional[Tuple[TravelStatistics, Dict[str, Route], Dict[str, float], Dict[str, float]]]:
    per_office_route: Dict[str, Route] = {}
    per_office_hours: Dict[str, float] = {}
    per_office_co2: Dict[str, float] = {}
    duration_weight, emission_weight = route_preference

    for office, count in scenario.attendees.items():
        if count <= 0:
            continue
        if office == host:
            per_office_route[office] = Route(legs=tuple(), total_duration=0.0, total_co2=0.0)
            per_office_hours[office] = 0.0
            per_office_co2[office] = 0.0
            continue
        routes = multi_objective_routes(dataset, office, host)
        if not routes:
            return None
        chosen_route = select_route(routes, duration_weight=duration_weight, emission_weight=emission_weight)
        per_office_route[office] = chosen_route
        per_office_hours[office] = chosen_route.total_duration * 2.0  # round trip
        per_office_co2[office] = chosen_route.total_co2 * 2.0  # round trip

    stats = travel_stats(per_office_hours, scenario.attendees, per_office_co2)
    return stats, per_office_route, per_office_hours, per_office_co2


def normalize(metric_values: Sequence[float]) -> List[float]:
    if not metric_values:
        return []
    min_value = min(metric_values)
    max_value = max(metric_values)
    if min_value == max_value:
        return [0.0 for _ in metric_values]
    return [(value - min_value) / (max_value - min_value) for value in metric_values]


def score_candidates(
    scenario: Scenario,
    dataset: TravelDataset,
    route_preference: Tuple[float, float],
    weights: Optional[Dict[str, float]] = None,
) -> List[CandidateEvaluation]:
    if weights is None:
        weights = DEFAULT_HOST_WEIGHTS
    positive_weights = {k: v for k, v in weights.items() if v > 0}
    if not positive_weights:
        raise ValueError("At least one host metric weight must be positive")

    evaluations: List[Tuple[str, TravelStatistics, Dict[str, Route], Dict[str, float], Dict[str, float]]] = []
    for host in dataset.candidate_hosts:
        result = evaluate_host(scenario, dataset, host, route_preference)
        if result is None:
            continue
        stats, per_route, per_hours, per_co2 = result
        evaluations.append((host, stats, per_route, per_hours, per_co2))

    if not evaluations:
        raise ValueError("No feasible meeting location found for provided scenario")

    metric_columns: Dict[str, List[float]] = {key: [] for key in positive_weights}
    for _host, stats, _routes, _hours, _co2 in evaluations:
        for metric_key in metric_columns:
            metric_columns[metric_key].append(getattr(stats, metric_key))

    normalized_metrics: Dict[str, List[float]] = {
        metric: normalize(values) for metric, values in metric_columns.items()
    }

    total_weight = sum(positive_weights.values())
    scored: List[CandidateEvaluation] = []
    for idx, (host, stats, per_route, per_hours, per_co2) in enumerate(evaluations):
        score_components: Dict[str, float] = {}
        aggregate_score = 0.0
        for metric_key, weight in positive_weights.items():
            component = normalized_metrics[metric_key][idx] * weight
            score_components[metric_key] = component
            aggregate_score += component
        composite_score = aggregate_score / total_weight
        scored.append(
            CandidateEvaluation(
                host=host,
                stats=stats,
                per_office_route=per_route,
                per_office_hours=per_hours,
                per_office_co2=per_co2,
                composite_score=composite_score,
                score_components=score_components,
            )
        )
    scored.sort(key=lambda item: item.composite_score)
    return scored


def build_output(candidate: CandidateEvaluation, scenario: Scenario) -> Dict:
    event_duration = scenario.event_duration.to_timedelta()
    event_start = scenario.availability_window.start
    scenario.availability_window.clamp(event_duration)
    event_end = event_start + event_duration

    max_travel_hours = candidate.stats.max_travel_hours
    buffer = timedelta(hours=max_travel_hours if max_travel_hours > 0 else 0)

    event_span_start = event_start - buffer
    event_span_end = event_end + buffer

    itineraries = {}
    for office, route in candidate.per_office_route.items():
        itineraries[office] = {
            "stops": route.stops if route.legs else (office,),
            "total_duration_hours": route.total_duration,
            "total_co2": route.total_co2,
            "legs": [
                {
                    "origin": leg.origin,
                    "destination": leg.destination,
                    "duration_hours": leg.duration_hours,
                    "co2_kg": leg.co2_kg,
                    "mode": leg.mode,
                }
                for leg in route.legs
            ],
        }

    return {
        "event_location": candidate.host,
        "event_dates": {
            "start": format_iso8601(event_start),
            "end": format_iso8601(event_end),
        },
        "event_span": {
            "start": format_iso8601(event_span_start),
            "end": format_iso8601(event_span_end),
        },
        "total_co2": candidate.stats.total_co2,
        "average_travel_hours": candidate.stats.average_travel_hours,
        "median_travel_hours": candidate.stats.median_travel_hours,
        "max_travel_hours": candidate.stats.max_travel_hours,
        "min_travel_hours": candidate.stats.min_travel_hours,
        "gini_travel_hours": candidate.stats.gini_travel_hours,
        "attendee_travel_hours": candidate.stats.attendee_travel_hours,
        "attendee_travel_co2": candidate.per_office_co2,
        "itineraries": itineraries,
    }


def solve_scenario(
    scenario: Scenario,
    dataset: TravelDataset,
    route_preference: Tuple[float, float] = (0.6, 0.4),
    weights: Optional[Dict[str, float]] = None,
    include_alternatives: int = 0,
) -> Dict:
    candidates = score_candidates(scenario, dataset, route_preference, weights)
    best = candidates[0]
    output = build_output(best, scenario)
    if include_alternatives > 0 and len(candidates) > 1:
        alternatives = []
        for alt in candidates[1 : include_alternatives + 1]:
            alternatives.append(
                {
                    "event_location": alt.host,
                    "score": alt.composite_score,
                    "metrics": {
                        "total_co2": alt.stats.total_co2,
                        "average_travel_hours": alt.stats.average_travel_hours,
                        "gini_travel_hours": alt.stats.gini_travel_hours,
                        "max_travel_hours": alt.stats.max_travel_hours,
                    },
                }
            )
        output["alternatives"] = alternatives
    output["selected_score"] = best.composite_score
    output["score_breakdown"] = best.score_components
    return output
