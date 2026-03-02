"""Pydantic v2 request/response models for the FastAPI /chat endpoint."""

from typing import Any

from pydantic import BaseModel


class ChatRequest(BaseModel):
    """Request body for POST /chat."""

    message: str
    thread_id: str


class ActionResponse(BaseModel):
    """Response body when the intent is an action command."""

    type: str = "action"
    command: str
    args: dict[str, Any] = {}
    requires_confirmation: bool
    description: str


class AnswerResponse(BaseModel):
    """Response body when the intent is a knowledge Q&A answer."""

    type: str = "answer"
    answer: str
    sources: list[Any] = []


class HealthResponse(BaseModel):
    """Response body for GET /health."""

    status: str = "ok"
