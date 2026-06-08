from __future__ import annotations

import asyncio
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.local_platform.config import PlatformConfig, resolve_platform_config
from src.local_platform.service import (
    LocalFinancialPlatformService,
    UploadParseError,
    UploadStorageError,
    UnsupportedUploadError,
)


class ChatRequest(BaseModel):
    question: str


def create_app(
    config: PlatformConfig | None = None,
    service: Any | None = None,
) -> FastAPI:
    platform_config = config or resolve_platform_config()
    platform_service = service or LocalFinancialPlatformService(platform_config)
    history: list[dict[str, Any]] = []

    app = FastAPI(title="Local Financial Agentic RAG Platform", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=platform_config.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return platform_service.health()

    @app.get("/api/platform")
    def platform() -> dict[str, Any]:
        return platform_service.platform()

    @app.post("/api/chat")
    async def chat(request: ChatRequest) -> dict[str, Any]:
        question = request.question.strip()
        if not question:
            raise HTTPException(status_code=422, detail="Question must not be empty.")
        response = await asyncio.to_thread(platform_service.answer, question)
        history.append(response)
        return response

    @app.post("/api/prospectus/upload")
    async def upload_prospectus(file: UploadFile | None = File(default=None)) -> dict[str, Any]:
        if file is None:
            raise HTTPException(status_code=422, detail="Upload file is required.")
        filename = file.filename or ""
        if not filename:
            raise HTTPException(status_code=422, detail="Upload file is required.")
        if not filename.lower().endswith((".pdf", ".txt")):
            raise HTTPException(status_code=400, detail="Unsupported file type. Upload a .pdf or .txt file.")
        content = await file.read()
        try:
            return await asyncio.to_thread(platform_service.upload_prospectus, filename, content)
        except UnsupportedUploadError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except UploadParseError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except UploadStorageError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/history")
    def get_history() -> dict[str, Any]:
        return {"messages": history}

    @app.delete("/api/history")
    def clear_history() -> dict[str, bool]:
        history.clear()
        return {"cleared": True}

    return app


app = create_app()
