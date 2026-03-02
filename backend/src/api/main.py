"""FastAPI application exposing the /chat and /health endpoints.

The module imports ``classify_intent`` and ``answer_question`` at module level
so that tests can patch them via:
  - ``mocker.patch("src.api.main.classify_intent", ...)``
  - ``mocker.patch("src.api.main.answer_question", ...)``
"""

from typing import Union

from fastapi import FastAPI, HTTPException

from src.chains.intent_classifier import classify_intent
from src.chains.qa_chain import answer_question

from src.api.models import ActionResponse, AnswerResponse, ChatRequest, HealthResponse

app = FastAPI(title="HiSpark AI Agent", version="0.1.0")


@app.post("/chat", response_model=Union[ActionResponse, AnswerResponse])
def chat(request: ChatRequest):
    """Handle a chat message, classify intent and return an action or answer.

    - If classify_intent returns ``{"type": "action", ...}``, the endpoint
      returns an ActionResponse (with ``args: {}`` always included).
    - If classify_intent returns ``{"type": "answer"}``, the endpoint calls
      answer_question and returns an AnswerResponse (with ``sources: []``).
    """
    try:
        intent = classify_intent(request.message)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    if intent.get("type") == "action":
        return ActionResponse(
            command=intent["command"],
            requires_confirmation=intent["requires_confirmation"],
            description=intent.get("description", ""),
            args=intent.get("args", {}),
        ).model_dump()

    # Default: knowledge Q&A answer
    answer = answer_question(request.message)
    return AnswerResponse(answer=answer).model_dump()


@app.get("/health", response_model=HealthResponse)
def health():
    """Return a simple health-check response."""
    return HealthResponse().model_dump()
