import os
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Pinecone as PineconeVectorStore
from langchain.prompts import ChatPromptTemplate
from pinecone import Pinecone 

from app.config import INDEX_NAME, OPENAI_API_KEY, PINECONE_API_KEY
from app.prompts import QUESTION_INIT, QUESTION_REWRITE

def build_rag():
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
    os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY

    pc = Pinecone(api_key=PINECONE_API_KEY)

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