from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest

import audit
import config


@pytest.fixture(autouse=True)
def isolate_audit_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "LOG_DIR", tmp_path)
    monkeypatch.setattr(config, "AUDIT_LOG", tmp_path / "audit.jsonl")


def test_log_appeal_reuses_exact_match() -> None:
    reasoning = "I wrote this.\u2028I have my notes."
    first = audit.log_appeal("text-1", "writer-1", reasoning)
    retry = audit.log_appeal("text-1", "writer-1", reasoning)

    assert retry == first
    assert audit.read_entries() == [first]


def test_log_appeal_records_different_reasoning() -> None:
    first = audit.log_appeal("text-1", "writer-1", "I wrote this.")
    second = audit.log_appeal("text-1", "writer-1", "I have my notes.")

    assert first["reasoning"] == "I wrote this."
    assert second["reasoning"] == "I have my notes."
    assert audit.read_entries() == [first, second]


def test_log_appeal_distinguishes_content_ids() -> None:
    first = audit.log_appeal("text-1", "writer-1", "I wrote this.")
    second = audit.log_appeal("text-2", "writer-1", "I wrote this.")

    assert first["content_id"] == "text-1"
    assert second["content_id"] == "text-2"
    assert audit.read_entries() == [first, second]


def test_log_appeal_deduplicates_concurrent_retries() -> None:
    workers = 8
    start = Barrier(workers, timeout=5)

    def appeal() -> dict[str, object]:
        start.wait()
        return audit.log_appeal("text-1", "writer-1", "I wrote this.")

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(appeal) for _ in range(workers)]
        entries = [future.result() for future in futures]

    assert entries == [entries[0]] * workers
    assert audit.read_entries() == [entries[0]]
