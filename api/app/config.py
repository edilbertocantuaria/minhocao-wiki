import os
import yaml
from pinecone import Pinecone, ServerlessSpec

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

OPENAI_API_KEY = config["OPENAI_API_KEY"]
PINECONE_API_KEY = config["PINECONE_API_KEY"]
INDEX_NAME = config["INDEX_NAME"]

os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY

pinecone_client = Pinecone(api_key=PINECONE_API_KEY)
