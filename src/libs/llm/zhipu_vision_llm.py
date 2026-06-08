"""Zhipu Vision LLM implementation.

This module provides a Zhipu AI vision provider implementation using the
OpenAI-compatible API surface exposed by BigModel.
"""

from __future__ import annotations

from typing import Any, Optional

from src.libs.llm.openai_vision_llm import OpenAIVisionLLM, OpenAIVisionLLMError


class ZhipuVisionLLMError(OpenAIVisionLLMError):
    """Raised when Zhipu Vision API call fails."""


class ZhipuVisionLLM(OpenAIVisionLLM):
    """Zhipu AI vision provider implementation."""

    DEFAULT_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"

    def __init__(
        self,
        settings: Any,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_image_size: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        resolved_base_url = (
            base_url
            or getattr(getattr(settings, "vision_llm", None), "base_url", None)
            or getattr(settings.llm, "base_url", None)
            or self.DEFAULT_BASE_URL
        )
        super().__init__(
            settings=settings,
            api_key=api_key,
            base_url=resolved_base_url,
            max_image_size=max_image_size,
            **kwargs,
        )