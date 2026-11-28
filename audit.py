"""
The audit log.

Every decision your service makes gets written here as one JSON object per
line. Not `print()` — a file you can read back.

The reason is next unit: you run an attack against this service, and **an
attack you can't see in a log is an attack you can't diagnose.** An input that
slipped past your detector leaves no other trace.

All nine fields the unit 8 rubric requires are in the entry shape from the
start, even though unit 7 only fills some of them. That's deliberate — adding
fields later means your early entries and your late ones have different shapes,
and the one you most want to compare is the one from before the change.

    from audit import log_decision, read_entries

    log_decision(content_id=..., creator_id=..., guess="ai", ...)
    entries = read_entries(limit=50)
"""

import json
import threading
from datetime import datetime, timezone

import config

# Appeals hold the lock through lookup and call the shared, locked writer.
_lock = threading.RLock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log_decision(
    content_id: str,
    creator_id: str,
    guess: str | None = None,
    model_score: float | None = None,
    style_score: float | None = None,
    combined_score: float | None = None,
    label: str | None = None,
    status: str = "decided",
    **extra,
) -> dict:
    """
    Write one decision to the audit log.

    The nine required fields, all present from unit 7 whether or not you can
    fill them yet:

        timestamp, content_id, creator_id, guess,
        model_score, style_score, combined_score, label, status

    `status` moves over an item's life: `decided` when first judged,
    `under_review` once the writer appeals.

    Anything extra you pass gets written too — useful for `rejected` entries in
    unit 8, where there's no decision but you still want the trace.
    """
    entry = {
        "timestamp": _now(),
        "content_id": content_id,
        "creator_id": creator_id,
        "guess": guess,
        "model_score": model_score,
        "style_score": style_score,
        "combined_score": combined_score,
        "label": label,
        "status": status,
    }
    entry.update(extra)
    return _append(entry)


def log_appeal(
    content_id: str, creator_id: str, reasoning: str
) -> dict[str, object]:
    """Record an appeal beside the original decision or return an exact match.

    Args:
        content_id: ID of the submission being appealed.
        creator_id: Creator ID from the original decision.
        reasoning: The writer's explanation for requesting review.

    Returns:
        The first appeal entry with matching content ID and reasoning.

    Raises:
        TypeError: An argument is not a string.
        ValueError: An argument is empty or contains only whitespace.
    """
    for name, value in (
        ("content_id", content_id),
        ("creator_id", creator_id),
        ("reasoning", reasoning),
    ):
        if not isinstance(value, str):
            raise TypeError(f"{name} must be a string.")
        if not value.strip():
            raise ValueError(f"{name} must be nonblank.")

    with _lock:
        for entry in entries_for(content_id):
            if entry.get("event") == "appeal" and (
                entry.get("reasoning") == reasoning
            ):
                return entry
        return _append(
            {
                "timestamp": _now(),
                "content_id": content_id,
                "creator_id": creator_id,
                "event": "appeal",
                "status": "under_review",
                "reasoning": reasoning,
            }
        )


def log_rejection(creator_id: str, reason: str, **extra) -> dict:
    """
    Record a request that never became a decision — a rate-limit rejection or
    an input your route refused.

    ⚠️ Unit 8 asks for this explicitly, and the reason is worth holding onto:
    **an attack that shows up only as an absence is one you'll never find.** A
    thousand requests that got a 429 and left no trace look exactly like a
    quiet afternoon.
    """
    return _append({
        "timestamp": _now(),
        "creator_id": creator_id,
        "event": "rejected",
        "status": "rejected",
        "reason": reason,
        **extra,
    })


def _append(entry: dict) -> dict:
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    line = json.dumps(entry, ensure_ascii=False)
    with _lock:
        with config.AUDIT_LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    return entry


def read_entries(limit: int | None = None) -> list[dict]:
    """
    Read the log back, oldest first. `limit` keeps the most recent N.

    A malformed line is skipped rather than raising — a log that can't be read
    because of one bad row is worse than a log with a gap.
    """
    if not config.AUDIT_LOG.exists():
        return []

    entries = []
    # Literal Unicode line separators can appear inside JSON string values.
    for line in config.AUDIT_LOG.read_text(encoding="utf-8").split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    return entries[-limit:] if limit else entries


def clear() -> int:
    """Wipe the log. Handy between attack runs; returns how many went."""
    count = len(read_entries())
    if config.AUDIT_LOG.exists():
        config.AUDIT_LOG.unlink()
    return count


def entries_for(content_id: str) -> list[dict]:
    """Every entry touching one content id, in order."""
    return [e for e in read_entries() if e.get("content_id") == content_id]
