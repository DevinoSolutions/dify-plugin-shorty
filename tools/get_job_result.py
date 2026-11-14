from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from shorty_api import ShortyError, get_job, result_for_job, text_param, DONE, FAILED


class GetJobResultTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        key = self.runtime.credentials.get("api_key")
        try:
            job_id = text_param(tool_parameters, "job_id", required=True)
            job = get_job(key, job_id)
            status = str(job.get("status") or "").lower()
            if status in FAILED:
                raise ShortyError(f"The Shorty job failed: {str(job.get('error') or status)[:300]}")
            if status not in DONE:
                yield self.create_text_message(f"The job is not finished yet (status {status}). Try again later.")
                yield self.create_json_message({"job_id": job_id, "status": status})
                return
            text, data = result_for_job(key, job)
            yield self.create_text_message(text)
            yield self.create_json_message(data)
        except ShortyError as error:
            yield self.create_text_message(str(error))
