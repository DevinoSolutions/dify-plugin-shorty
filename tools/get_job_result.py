from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from shorty_api import DONE, FAILED, ShortyError, failed_message, get_job, result_for_job, text_param


class GetJobResultTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        key = self.runtime.credentials.get("api_key")
        job_id = text_param(tool_parameters, "job_id", required=True)
        job = get_job(key, job_id)
        status = str(job.get("status") or "").lower()
        if status in FAILED:
            raise ShortyError(failed_message(job, status))
        if status not in DONE:
            yield self.create_text_message(f"The job is not finished yet (status {status}). Try again later.")
            yield self.create_json_message({"job_id": job_id, "status": status})
            return
        text, data = result_for_job(key, job)
        yield self.create_text_message(text)
        yield self.create_json_message(data)
