from duckduckgo_search import DDGS

def get_web_context(query: str, max_results: int = 5):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            context = ""
            links = []
            for res in results:
                url = res.get("link") or res.get("href", "")
                links.append(url)
                context += f"WEB SOURCE: {res.get('title')} ({url})\nCONTENT: {res.get('body')}\n\n"
            return context, links
    except:
        return "", []