"""Helpers for parsing device timestamps."""

from datetime import datetime, timezone


def to_utc_datetime(value: datetime | str | float | None) -> datetime | None:
    """Convert a report time to an aware UTC datetime."""
    if value is None or isinstance(value, bool):
        return None
    try:
        if isinstance(value, datetime):
            parsed = value
        elif isinstance(value, (int, float)):
            timestamp = value / 1000 if abs(value) >= 100_000_000_000 else value
            parsed = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        elif isinstance(value, str):
            normalized = value.strip()
            if not normalized:
                return None
            if normalized.endswith(("Z", "z")):
                normalized = f"{normalized[:-1]}+00:00"
            parsed = datetime.fromisoformat(normalized)
        else:
            return None
    except (OverflowError, OSError, ValueError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
