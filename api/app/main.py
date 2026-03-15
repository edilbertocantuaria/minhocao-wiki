from fastapi import FastAPI

from app.database import init_db
from app.routers.auth import router as auth_router
from app.routers.chat import router as chat_router
from app.routers.conversations import router as conversations_router

app = FastAPI(
    title="Minhocão Wiki API",
    description=(
        "API RAG com autenticação JWT.\n\n"
        "**How to authenticate in Swagger:**\n"
        "1. `POST /auth/register` — create your account\n"
        "2. `POST /auth/login` — log in and copy the `access_token`\n"
        "3. Click the **Authorize 🔒** button (top of page) → paste the token → click **Authorize**\n"
        "4. All protected endpoints (🔒) will automatically send the token"
    ),
    version="2.0.0",
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


app.include_router(auth_router)
app.include_router(conversations_router)
app.include_router(chat_router)