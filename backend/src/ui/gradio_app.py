"""Gradio chat UI for HiSpark AI Agent.

Connects to the FastAPI backend at http://localhost:8000/chat and displays
action commands or knowledge Q&A answers returned by the agent.

Launch with:
    python src/ui/gradio_app.py
Then open http://localhost:7860 in a browser.
"""

import httpx
import gradio as gr

BACKEND_URL = "http://localhost:8000/chat"
THREAD_ID = "gradio-session"


def format_response(data: dict) -> str:
    """Format the JSON response from the backend into a display string.

    Args:
        data: Parsed JSON dict from POST /chat.

    Returns:
        Human-readable string for display in the chat interface.
    """
    response_type = data.get("type")

    if response_type == "action":
        command = data.get("command", "")
        description = data.get("description", "")
        requires_confirmation = data.get("requires_confirmation", False)

        lines = [f"[命令] {command}"]
        if description:
            lines.append(description)
        if requires_confirmation:
            lines.append("需要确认")
        return "\n".join(lines)

    if response_type == "answer":
        return data.get("answer", "")

    # Unexpected response shape — surface the raw data
    return str(data)


def chat(message: str, history: list) -> str:
    """Send a message to the FastAPI backend and return the formatted reply.

    Args:
        message: The user's input text.
        history: The chat history (maintained by Gradio; not sent to backend).

    Returns:
        Formatted response string, or a user-friendly error message.
    """
    try:
        response = httpx.post(
            BACKEND_URL,
            json={"message": message, "thread_id": THREAD_ID},
            timeout=30.0,
        )
        response.raise_for_status()
        return format_response(response.json())
    except httpx.ConnectError:
        return "无法连接到后端服务，请先启动 FastAPI 服务器：uvicorn src.api.main:app --port 8000"
    except httpx.HTTPStatusError as exc:
        return f"服务器返回错误 {exc.response.status_code}：{exc.response.text}"
    except Exception as exc:  # noqa: BLE001
        return f"发生意外错误：{exc}"


def build_demo() -> gr.ChatInterface:
    """Build and return the Gradio ChatInterface."""
    return gr.ChatInterface(
        fn=chat,
        title="HiSpark AI Agent",
        description="向 HiSpark Studio AI 助手发送指令，例如：编译项目、烧录、支持哪些芯片",
        examples=["编译项目", "烧录", "支持哪些芯片"],
        type="messages",
    )


if __name__ == "__main__":
    demo = build_demo()
    demo.launch()
