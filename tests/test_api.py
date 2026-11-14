import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import shorty_api as api  # noqa: E402


def test_summary_result_builds_markdown():
    article = {
        "id": "a1",
        "title": "Capybara",
        "description": "d",
        "source_url": "https://example.com",
        "article_type": "WEBPAGE_ARTICLE",
        "summary": {"parts": [{"title": "Overview", "content": "Big rodent."}]},
    }
    text, data = api.summary_result(article)
    assert text == "# Capybara\n\n## Overview\n\nBig rodent."
    assert data["summary"] == [{"title": "Overview", "content": "Big rodent."}]


def test_transcript_result_parses_embedded_json():
    detail = {
        "id": "t1",
        "language": "english",
        "output_text": json.dumps(
            {"text": "Hello there.", "language": "en", "duration": 2.5, "segments": [{"start": 0, "end": 2.5, "text": " Hello there."}]}
        ),
    }
    text, data = api.transcript_result(detail)
    assert text == "Hello there."
    assert data["segments"][0]["text"] == "Hello there."
    assert data["language"] == "en"


def test_wait_seconds_is_clamped():
    assert api.wait_seconds({"max_wait": 5}, 240) == 10
    assert api.wait_seconds({"max_wait": 99999}, 240) == 540
    assert api.wait_seconds({}, 240) == 240


def test_wait_for_job_failure(monkeypatch):
    monkeypatch.setattr(api, "get_job", lambda key, job_id: {"status": "error", "error": "boom"})
    with pytest.raises(api.ShortyError, match="boom"):
        api.wait_for_job("k", "j", 10)


def test_wait_for_job_pending(monkeypatch):
    monkeypatch.setattr(api, "get_job", lambda key, job_id: {"status": "queued"})
    monkeypatch.setattr(api, "POLL_INTERVAL", 0)
    with pytest.raises(api.JobPending):
        api.wait_for_job("k", "j", 0)


def test_api_key_required():
    with pytest.raises(api.ShortyError):
        api.api_key("  ")
