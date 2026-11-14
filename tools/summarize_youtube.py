from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from shorty_api import ShortyError, run_job, start_summary, text_param, wait_seconds


class SummarizeYoutubeTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        key = self.runtime.credentials.get("api_key")
        try:
            url = text_param(tool_parameters, "url", required=True)
            language = text_param(tool_parameters, "language")
            started = start_summary(key, "youtube", url, language)
            yield from run_job(self, key, started, wait_seconds(tool_parameters, 240))
        except ShortyError as error:
            yield self.create_text_message(str(error))
