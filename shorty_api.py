"""Calls to the Shorty API and conversion of its responses to tool output.

The provider and the tools share this module. A tool file must hold only one
Tool subclass, so the shared code is here and not in tools/.
"""

import json
import time
from typing import Any
from urllib.parse import quote

import requests

API_BASE = "https://aishorty.com/v1"
USER_AGENT = "shorty-dify-plugin/0.1.0"
DEFAULT_TIMEOUT = 60
POLL_INTERVAL = 3
# Dify stops a tool call after MAX_REQUEST_TIMEOUT (600 s). Worst case is this wait,
# one sleep, one poll that is still running at the deadline (60 s) and two result
# fetches (2 x 60 s): 360 + 3 + 60 + 120 = 543 s.
MAX_WAIT = 360
DONE = {"success", "completed"}
FAILED = {"error", "failed", "cancelled", "canceled"}


class ShortyError(Exception):
    """An error message that is safe to show to the user and to the model. It never contains the key.

    retryable is True for a rate limit, a server error or a network failure.
    """

    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


class JobPending(Exception):
    """The job did not finish inside the wait time. It keeps running at Shorty."""

    def __init__(self, job_id: str, status: str):
        super().__init__(job_id)
        self.job_id = job_id
        self.status = status


def api_key(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ShortyError("A Shorty API key is required.")
    return value.strip()


def _error_message(response: requests.Response) -> str:
    detail = ""
    try:
        body = response.json()
    except ValueError:
        body = None
    if isinstance(body, dict):
        detail = str(body.get("detail") or body.get("title") or "")
    status = response.status_code
    if status == 401:
        label = "The API key is not valid."
    elif status == 403:
        label = "The API key does not allow this."
    elif status == 402:
        label = "Your Shorty plan does not include this."
    elif status == 429:
        label = "A limit was reached. Try again later."
    elif status == 404:
        label = "Not found."
    else:
        label = "The request failed."
    return f"Shorty error {status}: {label}" + (f" ({detail[:300]})" if detail and detail not in label else "")


def request(
    method: str,
    path: str,
    key: Any,
    body: dict | None = None,
    params: dict | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> requests.Response:
    """Call API_BASE + path with the key, and return the successful response."""
    secret = api_key(key)
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {secret}",
        "User-Agent": USER_AGENT,
    }
    try:
        response = requests.request(
            method, API_BASE + path, params=params, json=body, headers=headers, timeout=timeout
        )
    except requests.Timeout:
        raise ShortyError("Shorty did not answer in time. Try again.", retryable=True) from None
    except requests.RequestException:
        raise ShortyError("Could not connect to aishorty.com. Check the network.", retryable=True) from None
    if response.status_code >= 400:
        status = response.status_code
        raise ShortyError(
            _error_message(response).replace(secret, "***"), retryable=status == 429 or status >= 500
        )
    return response


def body_json(response: requests.Response) -> dict:
    try:
        data = response.json()
    except ValueError:
        raise ShortyError("Shorty sent a response that is not JSON.") from None
    if not isinstance(data, dict):
        raise ShortyError("Shorty sent an unexpected response.")
    return data


def check_credentials(key: Any) -> None:
    """GET /usage fails when the key is not valid and costs nothing."""
    request("GET", "/usage", key, timeout=30)


def text_param(params: dict, name: str, required: bool = False) -> str:
    value = params.get(name)
    value = value.strip() if isinstance(value, str) else ""
    if required and not value:
        raise ShortyError(f"{name} is required.")
    return value


def wait_seconds(params: dict, default: int) -> int:
    try:
        value = int(params.get("max_wait") or default)
    except (TypeError, ValueError):
        value = default
    return max(10, min(value, MAX_WAIT))


def start_summary(key: Any, source: str, url: str, language: str) -> dict:
    body = {"source": source, "url": url}
    if language:
        body["language"] = language
    return body_json(request("POST", "/summaries", key, body=body))


def start_transcription(key: Any, url: str, language: str, output_language: str) -> dict:
    body: dict[str, Any] = {"url": url}
    if language:
        body["language"] = language
    if output_language:
        body["output_language"] = output_language
    return body_json(request("POST", "/transcriptions", key, body=body))


def get_job(key: Any, job_id: str) -> dict:
    # Job ids can contain colons, as in YOUTUBE_ARTICLE:<id>:english.
    return body_json(request("GET", "/jobs/" + quote(job_id, safe=""), key))


def failed_message(job: dict, status: str) -> str:
    detail = str(job.get("error") or "").strip()
    message = f"Shorty could not process this link (status: {status}). Check the link or try another."
    if detail and detail.lower() != status:
        message += f" Details: {detail[:300]}"
    return message


def wait_for_job(key: Any, job_id: str, max_wait: int) -> dict:
    """Poll the job until it succeeds.

    Raises ShortyError if the job fails and JobPending if time runs out. A transient
    error while polling (429, 5xx, network) is retried until the deadline; if the
    last poll still failed, the job is reported as pending so the id is not lost.
    """
    deadline = time.monotonic() + max_wait
    status = "unknown"
    while True:
        try:
            job = get_job(key, job_id)
        except ShortyError as error:
            if not error.retryable:
                raise
        else:
            status = str(job.get("status") or "").lower()
            if status in DONE:
                return job
            if status in FAILED:
                raise ShortyError(failed_message(job, status))
        if time.monotonic() >= deadline:
            raise JobPending(job_id, status)
        time.sleep(POLL_INTERVAL)


def get_article(key: Any, article_id: str) -> dict:
    return body_json(request("GET", "/articles/" + quote(article_id, safe=""), key))


def get_transcription(key: Any, transcription_id: str) -> dict:
    return body_json(request("GET", "/transcriptions/" + quote(transcription_id, safe=""), key))


def summary_result(article: dict) -> tuple[str, dict]:
    """Return the summary as Markdown text, and the same data for workflow variables."""
    parts = []
    summary = article.get("summary")
    if isinstance(summary, dict):
        for part in summary.get("parts") or []:
            if isinstance(part, dict):
                parts.append({"title": part.get("title"), "content": part.get("content")})
    lines = []
    title = article.get("title")
    if title:
        lines.append(f"# {title}")
    for part in parts:
        if part["title"]:
            lines.append(f"## {part['title']}")
        if part["content"]:
            lines.append(str(part["content"]))
    if not parts and article.get("description"):
        lines.append(str(article["description"]))
    data = {
        "article_id": article.get("id"),
        "title": title,
        "description": article.get("description"),
        "source_url": article.get("source_url"),
        "article_type": article.get("article_type"),
        "summary": parts,
    }
    return "\n\n".join(lines), data


def transcript_result(detail: dict) -> tuple[str, dict]:
    """Return the transcript text, and the same data (with timed segments) for workflow variables."""
    raw = detail.get("output_text")
    output: Any = {}
    if isinstance(raw, str) and raw.strip():
        try:
            output = json.loads(raw)
        except ValueError:
            output = {"text": raw}
    elif isinstance(raw, dict):
        output = raw
    if not isinstance(output, dict):
        output = {}
    text = str(output.get("text") or "").strip()
    segments = [
        {"start": s.get("start"), "end": s.get("end"), "text": str(s.get("text") or "").strip()}
        for s in output.get("segments") or []
        if isinstance(s, dict)
    ]
    data = {
        "transcription_id": detail.get("id"),
        "language": output.get("language") or detail.get("language"),
        "duration": output.get("duration"),
        "input_file": detail.get("input_file"),
        "text": text,
        "segments": segments,
    }
    return text, data


def result_for_job(key: Any, job: dict) -> tuple[str, dict]:
    """Fetch what a finished job produced: a summary or a transcript."""
    output = job.get("output") if isinstance(job.get("output"), dict) else {}
    job_type = str(output.get("jobType") or "")
    result_id = output.get("articleId") or output.get("transcriptionId") or output.get("outputId")
    if not result_id:
        raise ShortyError("The job finished but Shorty returned no result id.")
    if job_type == "TRANSCRIPTION":
        text, data = transcript_result(get_transcription(key, str(result_id)))
        if not text:
            raise ShortyError(
                "Shorty returned an empty transcript. The link may not be a direct audio or video file "
                "(YouTube links are not transcribed; use the summarize tool for YouTube)."
            )
        return text, data
    return summary_result(get_article(key, str(result_id)))


def run_job(tool: Any, key: Any, started: dict, max_wait: int):
    """Shared tool body: wait for a started job and yield the text and JSON messages."""
    article_id = started.get("article_id")
    if started.get("status") == "already_complete" and article_id:
        try:
            text, data = summary_result(get_article(key, str(article_id)))
        except ShortyError as error:
            raise ShortyError(
                "Shorty says this was already summarized, but the summary is not in your account "
                f"({error}). Run it again with a different language setting to create a new summary."
            ) from None
        yield tool.create_text_message(text)
        yield tool.create_json_message(data)
        return
    job_id = started.get("job_id")
    if not job_id:
        raise ShortyError("Shorty did not return a job id.")
    try:
        job = wait_for_job(key, str(job_id), max_wait)
    except JobPending as pending:
        yield tool.create_text_message(
            f"Still running at Shorty (status {pending.status}). Job id: {pending.job_id}. "
            "Use the Get Job Result tool with this id later."
        )
        yield tool.create_json_message({"job_id": pending.job_id, "status": pending.status})
        return
    text, data = result_for_job(key, job)
    yield tool.create_text_message(text)
    yield tool.create_json_message(data)
