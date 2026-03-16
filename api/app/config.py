import os
import yaml
from pinecone import Pinecone

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f) or {}


def read_config(key: str, default=None):
    return os.getenv(key, config.get(key, default))

OPENAI_API_KEY = read_config("OPENAI_API_KEY")
PINECONE_API_KEY = read_config("PINECONE_API_KEY")
INDEX_NAME = read_config("INDEX_NAME")

DATABASE_URL = read_config(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@db:5432/minhocao_wiki",
)
JWT_SECRET_KEY = read_config("JWT_SECRET_KEY", "change-this-secret-in-production")
JWT_ALGORITHM = read_config("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(read_config("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 60))
GOOGLE_CLIENT_ID = read_config("GOOGLE_CLIENT_ID", "")

os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY

pinecone_client = Pinecone(api_key=PINECONE_API_KEY)
