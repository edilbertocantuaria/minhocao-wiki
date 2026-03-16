import os
import time
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Pinecone as PineconeVectorStore
from langchain.prompts import ChatPromptTemplate
from pinecone import Pinecone, ServerlessSpec

from app.config import INDEX_NAME, OPENAI_API_KEY, PINECONE_API_KEY
from app.prompts import QUESTION_INIT, QUESTION_REWRITE

INDEX_DIMENSION = int(os.getenv("INDEX_DIMENSION", "3072"))
INDEX_METRIC = os.getenv("INDEX_METRIC", "cosine")
INDEX_CLOUD = os.getenv("INDEX_CLOUD", "aws")
INDEX_REGION = os.getenv("INDEX_REGION", "us-east-1")


def _list_index_names(pc: Pinecone) -> set[str]:
    indexes = pc.list_indexes()
    if hasattr(indexes, "names"):
        return set(indexes.names())
    return {idx.name for idx in indexes}


def _is_index_ready(pc: Pinecone, index_name: str) -> bool:
    description = pc.describe_index(index_name)
    status = getattr(description, "status", None)
    if isinstance(status, dict):
        return bool(status.get("ready"))
    if status is not None and hasattr(status, "ready"):
        return bool(status.ready)
    return True


def _ensure_index_exists(pc: Pinecone, index_name: str) -> None:
    if index_name in _list_index_names(pc):
        return

    pc.create_index(
        name=index_name,
        dimension=INDEX_DIMENSION,
        metric=INDEX_METRIC,
        spec=ServerlessSpec(
            cloud=INDEX_CLOUD,
            region=INDEX_REGION,
        ),
    )

    deadline = time.time() + 180
    while time.time() < deadline:
        if _is_index_ready(pc, index_name):
            return
        time.sleep(2)

    raise RuntimeError(
        f"Pinecone index '{index_name}' was created but is not ready after timeout"
    )

def build_rag():
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
    os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY

    pc = Pinecone(api_key=PINECONE_API_KEY)
    _ensure_index_exists(pc, INDEX_NAME)

    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-large"
    )

    vectorstore = PineconeVectorStore.from_existing_index(
        index_name=INDEX_NAME,
        embedding=embeddings
    )

    retriever = vectorstore.as_retriever(
        search_type='similarity_score_threshold',
        search_kwargs={
            'k': 5, 
            'score_threshold': 0.75
        }
    )

    rewrite_llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.5
    )

    answer_llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.5,
        streaming=True
    )

    rewrite_prompt = ChatPromptTemplate.from_template(QUESTION_REWRITE)

    answer_prompt = ChatPromptTemplate.from_template(
        QUESTION_INIT + """
Chat History:
{history}

Context:
{context}

Question:
{question}
"""
    )

    return retriever, rewrite_llm, answer_llm, rewrite_prompt, answer_prompt