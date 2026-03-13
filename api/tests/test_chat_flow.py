import requests

URL = "http://localhost:8000/chat"

session = "conversation-test"

questions = [
    "Quais cursos existem na UnB?",
    "Qual a duração deles?",
    "Existe engenharia de software?"
]

for q in questions:

    payload = {
        "session_id": session,
        "question": q
    }

    r = requests.post(URL, json=payload)

    print("\nPergunta:", q)
    print("Resposta:", r.text)
