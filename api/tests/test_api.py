import requests

BASE_URL = "http://localhost:8000"

email = "test.user@example.com"
password = "123456"

requests.post(
    f"{BASE_URL}/auth/register",
    json={"email": email, "password": password},
)

login_response = requests.post(
    f"{BASE_URL}/auth/login",
    json={"email": email, "password": password},
)
token = login_response.json()["access_token"]

headers = {"Authorization": f"Bearer {token}"}

conversation_response = requests.post(
    f"{BASE_URL}/conversations",
    json={"title": "Teste rapido"},
    headers=headers,
)
conversation_id = conversation_response.json()["id"]

payload = {
    "conversation_id": conversation_id,
    "question": "Quais cursos existem na UnB?"
}

r = requests.post(f"{BASE_URL}/chat", json=payload, headers=headers)

print(r.text)
