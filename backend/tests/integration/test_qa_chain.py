"""Integration tests for qa_chain.build_retriever (requires real ZhipuAI API).

Moved from unit/test_qa_chain.py — this test makes a real embedding API call
and does not belong in the fast unit-test layer.
"""

import pytest

from src.chains.qa_chain import build_retriever


@pytest.mark.integration
def test_build_retriever_returns_non_none():
    """build_retriever must return a non-None object with get_relevant_documents.

    Requires a valid ZHIPU_API_KEY in the .env file.
    """
    docs = [
        "BS21 芯片支持 Wi-Fi 和蓝牙双模，适用于智能家居场景。",
        "BS20 芯片适用于低功耗 IoT 场景，内置 RISC-V 处理器。",
        "烧录固件前需连接 USB 数据线并选择正确的串口号。",
    ]

    retriever = build_retriever(docs)

    assert retriever is not None
    assert hasattr(retriever, "get_relevant_documents")
