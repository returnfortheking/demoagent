import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()  # 模块加载时执行一次，避免每次调用 get_llm() 重复读取磁盘


def get_llm(model: str = "glm-4-flash") -> ChatOpenAI:
    """Return a ChatOpenAI instance configured for ZhipuAI.

    Args:
        model: The model name to use. Defaults to "glm-4-flash".

    Returns:
        A ChatOpenAI instance configured with ZhipuAI credentials.

    Raises:
        ValueError: If ZHIPU_API_KEY environment variable is not set or is empty.
    """

    api_key = os.getenv("ZHIPU_API_KEY")
    if not api_key:
        raise ValueError("ZHIPU_API_KEY environment variable is not set")

    return ChatOpenAI(
        model=model,
        api_key=api_key,
        openai_api_base="https://open.bigmodel.cn/api/paas/v4/",
        temperature=0.1,
    )
