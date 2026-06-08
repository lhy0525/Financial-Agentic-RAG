"""Zhipu LLM implementation.

This module provides a Zhipu AI provider implementation using the
OpenAI-compatible API surface exposed by BigModel.
"""

from __future__ import annotations

from typing import Any, Optional

from src.libs.llm.openai_llm import OpenAILLM, OpenAILLMError


class ZhipuLLMError(OpenAILLMError):
    """Raised when Zhipu API call fails."""


class ZhipuLLM(OpenAILLM):
    """Zhipu AI LLM provider implementation.

    This class reuses the OpenAI-compatible transport and simply defaults
    the base URL to Zhipu's compatible endpoint.
    """

    DEFAULT_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"

    def __init__(
        self,
        settings: Any,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        resolved_base_url = (
            base_url
            or getattr(settings.llm, "base_url", None)
            or self.DEFAULT_BASE_URL
        )
        super().__init__(
            settings=settings,
            api_key=api_key,
            base_url=resolved_base_url,
            **kwargs,
        )