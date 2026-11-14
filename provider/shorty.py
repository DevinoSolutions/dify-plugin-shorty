from typing import Any

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

from shorty_api import ShortyError, check_credentials


class ShortyProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        # GET /v1/usage fails when the key is not valid and costs nothing.
        try:
            check_credentials(credentials.get("api_key"))
        except ShortyError as error:
            raise ToolProviderCredentialValidationError(str(error)) from None
