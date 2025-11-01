from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional

ISO_Z_SUFFIX = "Z"
ISO_UTC_SUFFIX = "+00:00"


def parse_iso8601(value: str) -> datetime:
    """Parse an ISO-8601 string that may end with a literal Z into an aware datetime."""
    if value.endswith(ISO_Z_SUFFIX):
        value = value[:-1] + ISO_UTC_SUFFIX
    return datetime.fromisoformat(value)


def format_iso8601(value: datetime) -> str:
    """Format an aware datetime into an ISO-8601 string with Z suffix when UTC."""
    if value.tzinfo is None:
        raise ValueError("Datetime must be timezone-aware")
    return value.astimezone(tz=timezone.utc).isoformat().replace(ISO_UTC_SUFFIX, ISO_Z_SUFFIX)


@dataclass(frozen=True)
class TimeWindow:
    start: datetime
    end: datetime

    def clamp(self, duration: timedelta) -> datetime:
        """Return the latest feasible start time for a given duration within the window."""
        latest_start = self.end - duration
        if latest_start < self.start:
            raise ValueError("Duration does not fit within availability window")
        return latest_start


@dataclass(frozen=True)
class Duration:
    days: int
    hours: int

    def to_timedelta(self) -> timedelta:
        return timedelta(days=self.days, hours=self.hours)


@dataclass(frozen=True)
class Scenario:
    attendees: Dict[str, int]
    availability_window: TimeWindow
    event_duration: Duration

    @staticmethod
    def from_payload(payload: Dict) -> "Scenario":
        availability = payload["availability_window"]
        duration = payload["event_duration"]
        return Scenario(
            attendees=payload["attendees"],
            availability_window=TimeWindow(
                start=parse_iso8601(availability["start"]),
                end=parse_iso8601(availability["end"]),
            ),
            event_duration=Duration(
                days=duration.get("days", 0),
                hours=duration.get("hours", 0),
            ),
        )


@dataclass(frozen=True)
class TravelLeg:
    origin: str
    destination: str
    duration_hours: float
    co2_kg: float
    mode: str = "flight"


class TravelDataset:
    """Simple in-memory directed graph of travel legs."""

    def __init__(self, legs: Iterable[TravelLeg]) -> None:
        self._legs: Dict[str, List[TravelLeg]] = {}
        for leg in legs:
            self._legs.setdefault(leg.origin, []).append(leg)

    def neighbors(self, origin: str) -> List[TravelLeg]:
        return self._legs.get(origin, [])

    @property
    def candidate_hosts(self) -> List[str]:
        hosts = set()
        for origin, legs in self._legs.items():
            hosts.add(origin)
            for leg in legs:
                hosts.add(leg.destination)
        return sorted(hosts)

    @staticmethod
    def from_records(records: Iterable[Dict[str, str]]) -> "TravelDataset":
        legs = []
        for record in records:
            legs.append(
                TravelLeg(
                    origin=record["origin"],
                    destination=record["destination"],
                    duration_hours=float(record["duration_hours"]),
                    co2_kg=float(record["co2_kg"]),
                    mode=record.get("mode", "flight"),
                )
            )
        return TravelDataset(legs)



