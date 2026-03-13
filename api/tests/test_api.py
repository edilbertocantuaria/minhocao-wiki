import requests

URL = "http://localhost:8000/chat"

payload = {
    "session_id": "test1",
    "question": "Quais cursos existem na UnB?"
}

r = requests.post(URL, json=payload)

print(r.text)
