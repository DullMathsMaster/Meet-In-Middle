from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple

from .data import TravelDataset, TravelLeg


@dataclass(frozen=True)
class Route:
    legs: Tuple[TravelLeg, ...]
    total_duration: float
    total_co2: float

    @property
    def stops(self) -> Tuple[str, ...]:
        return tuple(leg.origin for leg in self.legs) + (self.legs[-1].destination,) if self.legs else ()


@dataclass
class ParetoFront:
    entries: List[Tuple[float, float]]

    def __init__(self) -> None:
        self.entries = []

    def add(self, duration: float, co2: float) -> bool:
        """Attempt to add a point to the front, returning True if it was added."""
        if self.is_dominated(duration, co2):
            return False
        self.entries = [
            existing
            for existing in self.entries
            if not (duration <= existing[0] and co2 <= existing[1])
        ]
        self.entries.append((duration, co2))
        return True

    def is_dominated(self, duration: float, co2: float) -> bool:
        return any(d <= duration and c <= co2 for d, c in self.entries)


def multi_objective_routes(
    dataset: TravelDataset,
    origin: str,
    destination: str,
    max_hops: int = 4,
    max_routes: int = 20,
) -> List[Route]:
    """Enumerate Pareto-optimal routes capped by hops and output size."""

    queue: List[Tuple[float, float, int, str, Tuple[TravelLeg, ...], Tuple[str, ...]]]
    queue = [(0.0, 0.0, 0, origin, tuple(), (origin,))]
    pareto: Dict[str, ParetoFront] = {origin: ParetoFront()}
    pareto[origin].add(0.0, 0.0)
    solutions: List[Route] = []

    while queue and len(solutions) < max_routes:
        duration, co2, hops, city, legs, visited = heapq.heappop(queue)
        if city == destination and legs:
            solutions.append(Route(legs=legs, total_duration=duration, total_co2=co2))
            continue
        if hops == max_hops:
            continue
        for leg in dataset.neighbors(city):
            if leg.destination in visited:
                continue
            next_duration = duration + leg.duration_hours
            next_co2 = co2 + leg.co2_kg
            next_legs = legs + (leg,)
            next_visited = visited + (leg.destination,)
            front = pareto.setdefault(leg.destination, ParetoFront())
            if front.add(next_duration, next_co2):
                heapq.heappush(
                    queue,
                    (next_duration, next_co2, hops + 1, leg.destination, next_legs, next_visited),
                )
    return solutions


def select_route(
    routes: Sequence[Route],
    duration_weight: float = 0.5,
    emission_weight: float = 0.5,
) -> Route:
    """Pick a single route from Pareto optimal candidates via weighted scoring."""
    if not routes:
        raise ValueError("No feasible routes provided")
    if duration_weight < 0 or emission_weight < 0:
        raise ValueError("Weights must be non-negative")
    total_weight = duration_weight + emission_weight
    if total_weight == 0:
        raise ValueError("At least one weight must be positive")
    duration_weight /= total_weight
    emission_weight /= total_weight

    max_duration = max(route.total_duration for route in routes)
    min_duration = min(route.total_duration for route in routes)
    max_co2 = max(route.total_co2 for route in routes)
    min_co2 = min(route.total_co2 for route in routes)

    def normalize(value: float, min_value: float, max_value: float) -> float:
        if max_value == min_value:
            return 0.0
        return (value - min_value) / (max_value - min_value)

    best_route = min(
        routes,
        key=lambda route: duration_weight * normalize(route.total_duration, min_duration, max_duration)
        + emission_weight * normalize(route.total_co2, min_co2, max_co2),
    )
    return best_route
