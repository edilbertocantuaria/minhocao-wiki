QUESTION_INIT = """
You must answer the question following the decision process below.

Decision process:

1. If the context contains INTERNAL DOCUMENTS from the repository, answer using ONLY the information contained in those documents.
2. Do not add external knowledge, assumptions, or interpretations when internal documents are present.

3. If the internal documents DO NOT contain the answer, you MUST use the WEB SEARCH RESULTS provided in the context.

4. When the answer is generated from web results, you MUST clearly indicate that the information comes from external sources and start the answer exactly with the warning:

⚠️ Esta resposta foi gerada com base em resultados da web e não em documentos oficiais do repositório.

Source citation rules:

5. When citing information from internal documents, ALWAYS use the real value of the metadata field "source".
6. NEVER write placeholders such as "<source>", "(source)", or similar.
7. Extract the real value from the metadata and print it exactly as it appears.

8. At the end of the answer include a section exactly in this format:

Fonte:
REAL_SOURCE_VALUE

Example:

Fonte:
UNIVERSIDADE DE BRASÍLIA RESOLUÇÃO DO CONSELHO DE ENSINO, PESQUISA E EXTENSÃO N. 6-1/2007

9. If multiple internal documents are used, list each source on a new line.

Web sources:

10. When using web results, include the URLs in the "Fonte:" section.

Text normalization rules:

11. The context may contain OCR errors. When obvious, correct small recognition mistakes (example: "D( ONSELHO" → "DO CONSELHO").
12. Preserve legal references such as:
Art. 1º, Art. 2º, §1º, §2º, I, II, III, IV etc.

Failure rule:

13. Only respond with the message below if BOTH conditions are true:
   - The internal documents do not contain the answer
   - The web search results also do not contain the answer

In that case respond exactly with:

"A informação não está disponível nos documentos fornecidos ou nos resultados da web."
"""

QUESTION_REWRITE = """
Given the chat history and the user question,
rewrite the question so that it becomes a standalone query.

Chat history:
{history}

User question:
{question}

Standalone question:
"""

QUESTION_TITLE = """
Generate a short conversation title in Brazilian Portuguese based on the user question.

Rules:
- Return only the title text.
- Maximum 10 words.
- Keep it specific and objective.
- Do not use quotes.
- Do not add punctuation at the end.

User question:
{question}

Title:
"""
