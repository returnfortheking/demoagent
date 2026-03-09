"""LCEL RAG QA chain with RunnableWithMessageHistory (v0.2).

The chain pipeline:
  itemgetter("question") | _to_str | retriever | _format_docs   -> {context}
  itemgetter("question") | _to_str                              -> {question}
  | ChatPromptTemplate | llm | StrOutputParser()

Wrapped by RunnableWithMessageHistory to accumulate per-session conversation
history.  History is stored in-process (dict); cross-process persistence is
added in v0.6 (MemorySaver Checkpoint).

Note on _to_str: RunnableWithMessageHistory with input_messages_key wraps the
question string as [HumanMessage(text)] before passing to the base chain.
_to_str normalises both str and [HumanMessage] forms back to a plain string so
the retriever always receives the expected type.

The module uses lazy initialization: ``_qa_chain`` is NOT created at import
time.  It is built on the first call to ``_get_qa_chain()``.  This means
importing the module never triggers real embedding or LLM API calls, which
allows unit tests to mock ``src.chains.qa_chain._get_qa_chain`` without any
network side-effects.
"""

import os
import pathlib
from operator import itemgetter

from dotenv import load_dotenv
from langchain.schema import BaseRetriever
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_community.vectorstores import Chroma
from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import OpenAIEmbeddings

from src.config import get_llm
from src.prompts.qa_v1 import QA_PROMPT_TEMPLATE

load_dotenv()

# ---------------------------------------------------------------------------
# Embeddings model (ZhipuAI embedding-3, OpenAI-compatible)
# ---------------------------------------------------------------------------

_embeddings = OpenAIEmbeddings(
    model="embedding-3",
    openai_api_key=os.getenv("ZHIPU_API_KEY"),
    openai_api_base="https://open.bigmodel.cn/api/paas/v4/",
)

# ---------------------------------------------------------------------------
# In-process session history store
# ---------------------------------------------------------------------------

_session_store: dict[str, ChatMessageHistory] = {}


def get_session_history(session_id: str) -> ChatMessageHistory:
    """Return (or create) the ChatMessageHistory for the given session_id.

    Args:
        session_id: Opaque identifier for the conversation session (e.g. thread_id).

    Returns:
        The ChatMessageHistory instance for this session.
    """
    if session_id not in _session_store:
        _session_store[session_id] = ChatMessageHistory()
    return _session_store[session_id]


# ---------------------------------------------------------------------------
# Public API: build_retriever
# ---------------------------------------------------------------------------


def build_retriever(docs: list[str]) -> BaseRetriever:
    """Build an in-memory Chroma retriever from a list of plain-text strings.

    Args:
        docs: A list of plain-text document strings to index.

    Returns:
        A Chroma-backed retriever configured to return the top-3 matches (k=3).
    """
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks: list[str] = []
    for doc in docs:
        chunks.extend(splitter.split_text(doc))

    vectorstore = Chroma.from_texts(
        texts=chunks,
        embedding=_embeddings,
    )
    return vectorstore.as_retriever(search_kwargs={"k": 3})


# ---------------------------------------------------------------------------
# Lazy-initialized module-level chain
# ---------------------------------------------------------------------------

_qa_chain: RunnableWithMessageHistory | None = None


def _load_sample_docs() -> list[str]:
    """Load the sample_docs.md fixture as a list of text chunks."""
    fixture_path = (
        pathlib.Path(__file__).parent.parent.parent
        / "tests"
        / "fixtures"
        / "sample_docs.md"
    )
    text = fixture_path.read_text(encoding="utf-8")
    return [text]


def _format_docs(docs) -> str:
    """Convert a list of Document objects to a single context string."""
    return "\n\n".join(doc.page_content for doc in docs)


def _to_question_str(x) -> str:
    """Normalise question input to a plain string.

    RunnableWithMessageHistory with input_messages_key wraps the question
    value as [HumanMessage(text)] before it reaches the base chain.
    This helper handles both str and [HumanMessage] forms.
    """
    if isinstance(x, list) and x:
        last = x[-1]
        return last.content if isinstance(last, BaseMessage) else str(last)
    if isinstance(x, BaseMessage):
        return x.content
    return str(x)


_to_str = RunnableLambda(_to_question_str)


def _get_qa_chain() -> RunnableWithMessageHistory:
    """Return the module-level chain, building it on first access."""
    global _qa_chain
    if _qa_chain is None:
        retriever = build_retriever(_load_sample_docs())
        prompt = ChatPromptTemplate.from_template(QA_PROMPT_TEMPLATE)
        base_chain = (
            {
                "context": itemgetter("question") | _to_str | retriever | _format_docs,
                "question": itemgetter("question") | _to_str,
            }
            | prompt
            | get_llm()
            | StrOutputParser()
        )
        _qa_chain = RunnableWithMessageHistory(
            base_chain,
            get_session_history,
            input_messages_key="question",
        )
    return _qa_chain


# ---------------------------------------------------------------------------
# Public API: answer_question
# ---------------------------------------------------------------------------


def answer_question(question: str, session_id: str) -> str:
    """Answer a question using the LCEL RAG chain with session memory.

    Args:
        question: The natural-language question from the user.
        session_id: Conversation session identifier (e.g. request thread_id).

    Returns:
        A string answer generated by the LLM based on the retrieved context.
    """
    return _get_qa_chain().invoke(
        {"question": question},
        config={"configurable": {"session_id": session_id}},
    )
