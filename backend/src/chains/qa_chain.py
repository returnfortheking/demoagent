"""RetrievalQA knowledge Q&A chain backed by an in-memory Chroma vector store.

The module uses lazy initialization: ``_qa_chain`` is NOT created at import
time.  It is built on the first call to ``answer_question()`` (or the internal
``_get_qa_chain()`` helper).  This means importing the module never triggers
real embedding or LLM API calls, which allows unit tests to mock
``src.chains.qa_chain._get_qa_chain`` without any network side-effects.

Implementation note
-------------------
RetrievalQA (langchain 0.3.x) is a Pydantic v2 model, just like LLMChain.
Pydantic v2 models forbid arbitrary attribute assignment/deletion, which means
``mocker.patch("...._qa_chain.run", ...)`` would fail when pytest-mock tries
to restore the original value via ``delattr``.

The same ``_ChainWrapper`` pattern used in ``intent_classifier.py`` is applied
here: the RetrievalQA instance is wrapped in a plain Python object whose
``run`` method can be freely patched by pytest-mock.
"""

import os
import pathlib
from typing import Optional

from dotenv import load_dotenv
from langchain.chains import RetrievalQA
from langchain.schema import BaseRetriever
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

from src.config import get_llm

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
# Wrapper — makes _qa_chain.run freely patchable by pytest-mock
# ---------------------------------------------------------------------------


class _ChainWrapper:
    """Thin wrapper around RetrievalQA to allow attribute-level mocking.

    RetrievalQA is a Pydantic v2 BaseModel with ``model_config`` that
    prevents ``setattr``/``delattr`` on arbitrary attributes.  By delegating
    through this plain Python class, ``mocker.patch("...._qa_chain.run", ...)``
    works without restriction.
    """

    def __init__(self, retrieval_qa: RetrievalQA) -> None:
        self._retrieval_qa = retrieval_qa

    def run(self, query: str) -> str:
        """Invoke the underlying RetrievalQA chain and return its string output."""
        return self._retrieval_qa.run(query)


# ---------------------------------------------------------------------------
# Lazy-initialized module-level chain
# ---------------------------------------------------------------------------

_qa_chain: Optional[_ChainWrapper] = None


def _load_sample_docs() -> list[str]:
    """Load the sample_docs.md fixture as a list of text chunks.

    The fixture path is resolved relative to this file's location so that the
    module works regardless of the current working directory.
    """
    fixture_path = (
        pathlib.Path(__file__).parent.parent.parent
        / "tests"
        / "fixtures"
        / "sample_docs.md"
    )
    text = fixture_path.read_text(encoding="utf-8")
    return [text]


def _get_qa_chain() -> _ChainWrapper:
    """Return the module-level QA chain, building it on first access.

    The chain is constructed lazily so that importing this module does not
    trigger any embedding or LLM API calls.  Subsequent calls return the
    cached instance.
    """
    global _qa_chain
    if _qa_chain is None:
        retriever = build_retriever(_load_sample_docs())
        _qa_chain = _ChainWrapper(
            RetrievalQA.from_chain_type(
                llm=get_llm(),
                chain_type="stuff",
                retriever=retriever,
            )
        )
    return _qa_chain


# ---------------------------------------------------------------------------
# Public API: answer_question
# ---------------------------------------------------------------------------


def answer_question(question: str) -> str:
    """Answer a question using the lazily-built RetrievalQA chain.

    Args:
        question: The natural-language question from the user.

    Returns:
        A string answer generated by the LLM based on the retrieved context.
    """
    return _get_qa_chain().run(question)
