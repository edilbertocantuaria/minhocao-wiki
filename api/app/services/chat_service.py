from app.rag_chain import build_rag
from app.utils import format_document_title
from app.web_search import get_web_context

retriever, rewrite_llm, answer_llm, rewrite_prompt, answer_prompt = build_rag()


def process_internal_docs(docs):
    context_parts = []
    source_list = []
    for doc in docs:
        formatted_source = format_document_title(doc.metadata.get("source", ""))
        source_list.append(formatted_source)
        context_parts.append(f"SOURCE: {formatted_source}\nCONTENT: {doc.page_content}")
    return "\n\n".join(context_parts), list(set(source_list))


def build_history_str(history: list[dict]) -> str:
    return "\n".join([f"{item['role']}: {item['content']}" for item in history[-6:]])


def build_chain_input(question: str, history_str: str):
    rewrite_query = rewrite_prompt.invoke({"history": history_str, "question": question})
    query = rewrite_llm.invoke(rewrite_query).content

    vector_docs = retriever.invoke(query)
    internal_ctx, internal_src = process_internal_docs(vector_docs)

    web_ctx = ""
    web_sources = []
    if not internal_ctx:
        web_ctx, web_links = get_web_context(query)
        web_sources = [f"fonte-web: {link}" for link in web_links]

    full_context = (
        "INSTRUCTION: Be formal, highly detailed, and verbose. "
        "Prioritize 'OFFICIAL SOURCE' if available. "
        "If you use information from 'SOURCE WEB', cite it as 'fonte-web: [URL]'. "
        "List all sources at the very end of your response.\n\n"
        f"--- OFFICIAL REPOSITORY ---\n{internal_ctx if internal_ctx else 'No official documents found.'}\n\n"
        f"--- WEB RESULTS ---\n{web_ctx}"
    )

    chain_input = answer_prompt.invoke(
        {
            "history": history_str,
            "context": full_context,
            "question": question,
        }
    )

    return chain_input, internal_src + web_sources
