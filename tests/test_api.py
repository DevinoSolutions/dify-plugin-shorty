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
    assert api.wait_seconds({"max_wait": 99999}, 240) == api.MAX_WAIT == 360
    assert api.wait_seconds({}, 240) == 240


def test_wait_for_job_failure(monkeypatch):
    monkeypatch.setattr(api, "get_job", lambda key, job_id: {"status": "error", "error": "boom"})
    with pytest.raises(api.ShortyError, match="boom"):
        api.wait_for_job("k", "j", 10)


def test_wait_for_job_status_error_has_useful_message(monkeypatch):
    monkeypatch.setattr(api, "get_job", lambda key, job_id: {"status": "error"})
    with pytest.raises(api.ShortyError) as caught:
        api.wait_for_job("k", "j", 10)
    assert str(caught.value) == (
        "Shorty could not process this link (status: error). Check the link or try another."
    )


def test_worst_case_wait_stays_under_dify_request_timeout():
    # cap + one sleep + one poll + two result fetches, each request up to DEFAULT_TIMEOUT
    assert api.MAX_WAIT + api.POLL_INTERVAL + 3 * api.DEFAULT_TIMEOUT < 600


def test_wait_for_job_keeps_polling_after_transient_error(monkeypatch):
    answers = iter([api.ShortyError("Shorty error 429: x", retryable=True), {"status": "success"}])

    def fake(key, job_id):
        answer = next(answers)
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(api, "get_job", fake)
    monkeypatch.setattr(api, "POLL_INTERVAL", 0)
    assert api.wait_for_job("k", "j", 10) == {"status": "success"}


def test_wait_for_job_pending_when_polls_keep_failing(monkeypatch):
    def fake(key, job_id):
        raise api.ShortyError("Shorty error 503: x", retryable=True)

    monkeypatch.setattr(api, "get_job", fake)
    monkeypatch.setattr(api, "POLL_INTERVAL", 0)
    with pytest.raises(api.JobPending) as caught:
        api.wait_for_job("k", "job-1", 0)
    assert caught.value.job_id == "job-1"


def test_wait_for_job_raises_non_transient_error(monkeypatch):
    def fake(key, job_id):
        raise api.ShortyError("Shorty error 401: The API key is not valid.")

    monkeypatch.setattr(api, "get_job", fake)
    with pytest.raises(api.ShortyError, match="401"):
        api.wait_for_job("k", "j", 10)


def test_wait_for_job_pending(monkeypatch):
    monkeypatch.setattr(api, "get_job", lambda key, job_id: {"status": "queued"})
    monkeypatch.setattr(api, "POLL_INTERVAL", 0)
    with pytest.raises(api.JobPending):
        api.wait_for_job("k", "j", 0)


def test_api_key_required():
    with pytest.raises(api.ShortyError):
        api.api_key("  ")
