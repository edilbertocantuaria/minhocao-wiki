from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from app.models import ChatRequest
from app.memory import get_history, save_message
from app.logger import log_query
from app.rag_chain import build_rag
from app.utils import format_document_title
from app.web_search import get_web_context

app = FastAPI()

retriever, rewrite_llm, answer_llm, rewrite_prompt, answer_prompt = build_rag()

def process_internal_docs(docs):
    context_parts = []
    source_list = []
    for d in docs:
        fmt_src = format_document_title(d.metadata.get("source", ""))
        source_list.append(fmt_src)
        context_parts.append(f"SOURCE: {fmt_src}\nCONTENT: {d.page_content}")
    return "\n\n".join(context_parts), list(set(source_list))

@app.post("/chat")
async def chat(req: ChatRequest):
    history = get_history(req.session_id)
    history_str = "\n".join([f"{m['role']}: {m['content']}" for m in history[-6:]])

    rewrite_query = rewrite_prompt.invoke({"history": history_str, "question": req.question})
    query = rewrite_llm.invoke(rewrite_query).content

    vector_docs = retriever.invoke(query)
    internal_ctx, internal_src = process_internal_docs(vector_docs)
    
    web_ctx, web_src = "", []

    if not internal_ctx:
        
        web_ctx, web_links = get_web_context(query)
        web_src = [f"fonte-web: {link}" for link in web_links]

    full_context = (
        "INSTRUCTION: Be formal, highly detailed, and verbose. "
        "Prioritize 'OFFICIAL SOURCE' if available. "
        "If you use information from 'SOURCE WEB', cite it as 'fonte-web: [URL]'. "
        "List all sources at the very end of your response.\n\n"
        f"--- OFFICIAL REPOSITORY ---\n{internal_ctx if internal_ctx else 'No official documents found.'}\n\n"
        f"--- WEB RESULTS ---\n{web_ctx}"
    )
    
    chain_input = answer_prompt.invoke({
        "history": history_str,
        "context": full_context,
        "question": req.question
    })

    async def stream():
        full_answer = ""
        
        async for chunk in answer_llm.astream(chain_input):
            yield chunk.content
            full_answer += chunk.content

        save_message(req.session_id, "user", req.question)
        save_message(req.session_id, "assistant", full_answer)
        log_query(req.question, internal_src + web_src, full_answer)

    return StreamingResponse(stream(), media_type="text/plain")