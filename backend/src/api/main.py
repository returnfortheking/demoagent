"""FastAPI application exposing the /chat, /chat/stream and /health endpoints.

The module imports ``classify_intent``, ``answer_question``, and
``_get_qa_chain`` at module level so that tests can patch them via:
  - ``mocker.patch("src.api.main.classify_intent", ...)``
  - ``mocker.patch("src.api.main.answer_question", ...)``
  - ``mocker.patch("src.chains.qa_chain._get_qa_chain", ...)``
"""

import json
from typing import AsyncGenerator, Union

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

import src.chains.qa_chain as _qa_chain_module

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
    answer = answer_question(request.message, session_id=request.thread_id)
    return AnswerResponse(answer=answer).model_dump()


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Stream a chat response as Server-Sent Events.

    - action intent: yields one action event then [DONE]
    - answer intent: streams LLM tokens as delta events then [DONE]
    """

    async def generate() -> AsyncGenerator[str, None]:
        intent = classify_intent(request.message)

        if intent.get("type") == "action":
            event_data = {
                "thread_id": request.thread_id,
                "type": "action",
                "command": intent["command"],
                "requires_confirmation": intent["requires_confirmation"],
                "description": intent.get("description", ""),
            }
            yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
        else:
            chain = _qa_chain_module._get_qa_chain()
            async for token in chain.astream(
                {"question": request.message},
                config={"configurable": {"session_id": request.thread_id}},
            ):
                event_data = {"thread_id": request.thread_id, "delta": token}
                yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/health", response_model=HealthResponse)
def health():
    """Return a simple health-check response."""
    return HealthResponse().model_dump()
