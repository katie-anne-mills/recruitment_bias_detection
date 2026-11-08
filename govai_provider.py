"""inspect-ai model provider for the GovAI AWS Bedrock brokerage.

The GovAI proxy uses Bearer-token auth instead of SigV4 (matching the .NET
Au.Gov.AI.GovAI package). We register a before-send event hook that overwrites
whatever SigV4 Authorization header aiobotocore produced with the Bearer token.
Dummy AWS credentials are injected so aiobotocore doesn't raise NoCredentialsError.
"""

from __future__ import annotations

import os
from typing import Any

from typing_extensions import override

from inspect_ai.model._generate_config import GenerateConfig
from inspect_ai.model._model_output import ModelOutput
from inspect_ai.model._providers.bedrock import BedrockAPI
from inspect_ai.model._registry import modelapi
from inspect_ai.tool import ToolChoice, ToolInfo
from inspect_ai.tool._tool_choice import ToolFunction
from inspect_ai.model._chat_message import ChatMessage


@modelapi(name="govai")
class GovAIBedrockAPI(BedrockAPI):
    """Bedrock Converse provider for the GovAI brokerage.

    Reads from .env (loaded by petri-bloom/inspect-ai automatically):
      BEDROCK_BASE_URL or ANTHROPIC_BEDROCK_BASE_URL — proxy endpoint
      AWS_BEARER_TOKEN_BEDROCK                        — bearer token
      AWS_DEFAULT_REGION or AWS_REGION                — region (default ap-southeast-2)
      GOVAI_READ_TIMEOUT                              — read timeout in seconds (default 300)
    """

    def __init__(
        self,
        model_name: str,
        base_url: str | None = None,
        api_key: str | None = None,
        config: GenerateConfig = GenerateConfig(),
        **model_args: Any,
    ):
        bearer = api_key or os.environ.get("AWS_BEARER_TOKEN_BEDROCK") or ""
        resolved_url = (
            base_url
            or os.environ.get("BEDROCK_BASE_URL")
            or os.environ.get("ANTHROPIC_BEDROCK_BASE_URL")
        )
        region = (
            os.environ.get("AWS_DEFAULT_REGION")
            or os.environ.get("AWS_REGION")
            or "ap-southeast-2"
        )

        # Dummy credentials prevent aiobotocore raising NoCredentialsError.
        # The SigV4 Authorization header they produce is overwritten by the
        # before-send hook below, so the proxy only ever sees the Bearer token.
        model_args.setdefault("aws_access_key_id", "govai")
        model_args.setdefault("aws_secret_access_key", "govai")
        model_args.setdefault("region_name", region)

        # botocore's 60s read timeout is too short for long single responses
        # (e.g. ideation generating a batch of scenarios in one call).
        model_args.setdefault("read_timeout", os.environ.get("GOVAI_READ_TIMEOUT", "300"))

        super().__init__(
            model_name=model_name,
            base_url=resolved_url,
            api_key=bearer,
            config=config,
            **model_args,
        )

        def _inject_bearer(request, **_):
            request.headers["Authorization"] = f"Bearer {bearer}"

        # Newer inspect-ai uses an aiobotocore AioSession directly; older versions
        # used an aioboto3.Session wrapping one in ._session.
        session = getattr(self.session, "_session", self.session)
        session.register("before-send.bedrock-runtime.*", _inject_bearer)

    @override
    async def generate(
        self,
        input: list[ChatMessage],
        tools: list[ToolInfo],
        tool_choice: ToolChoice,
        config: GenerateConfig,
    ) -> ModelOutput | tuple[ModelOutput | Exception, Any]:
        # The GovAI proxy only supports tool_choice "auto"; downgrade anything else.
        if tool_choice == "any" or isinstance(tool_choice, ToolFunction):
            tool_choice = "auto"
        return await super().generate(input, tools, tool_choice, config)
