import os
import json
import hashlib
import logging
import yaml
import zipfile
import shutil
import time
from datetime import datetime
from pathlib import Path
from collections import defaultdict

from pinecone import Pinecone, ServerlessSpec
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings


# ================================
# CONFIG
# ================================

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "config.yaml"
DOCS_PATH = BASE_DIR / "docs"
LOG_DIR = BASE_DIR / "logs"
MANIFEST_FILE = BASE_DIR / "manifests" / "document_manifest.json"

def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

config = load_config()

INDEX_NAME = config["INDEX_NAME"]
PINECONE_API_KEY = config["PINECONE_API_KEY"]
OPENAI_API_KEY = config["OPENAI_API_KEY"]

INDEX_DIMENSION = 3072
INDEX_METRIC = "cosine"
INDEX_CLOUD = "aws"
INDEX_REGION = "us-east-1"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
UPSERT_BATCH = 100

ZIP_PATH = BASE_DIR / "unb.zip"
EXTRACT_PATH = DOCS_PATH / "unb"


DOC_TYPE_LABELS = {
    "ato": "Ato",
    "circular": "Circular",
    "circular_conjunta": "Circular Conjunta",
    "decreto": "Decreto",
    "instrucao": "Instrução",
    "instrucao_conjunta": "Instrução Conjunta",
    "instrucao_normativa": "Instrução Normativa",
    "lei": "Lei",
    "manual": "Manual",
    "memorando_circular": "Memorando Circular",
    "portaria": "Portaria",
    "resolucao": "Resolução"
}

BODY_LABELS = {
    "cad": "Conselho de Administração",
    "ceg": "Câmara de Ensino de Graduação",
    "cepe": "Conselho de Ensino, Pesquisa e Exetensão",
    "consuni": "Conselho Universitário",
    "deg": "Decanato de Ensino de Graduação",
    "mec": "Ministério da Educação",
    "reitoria": "Reitoria",
    "saa": "Secretaria de Administração Academica",
}


def extract_zip():

    if not ZIP_PATH.exists():
        raise FileNotFoundError(f"ZIP file not found: {ZIP_PATH}")

    if EXTRACT_PATH.exists():
        shutil.rmtree(EXTRACT_PATH)

    EXTRACT_PATH.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(ZIP_PATH, "r") as zip_ref:
        zip_ref.extractall(EXTRACT_PATH)

    return EXTRACT_PATH


# ================================
# LOGGER
# ================================

def setup_logger():

    LOG_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"ingestion_{timestamp}.txt"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler()
        ]
    )

    logging.info(f"Log file: {log_file}")


# ================================
# UTIL
# ================================

def normalize_path(path):
    return str(Path(path).as_posix())

def file_hash(path):

    h = hashlib.sha256()

    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)

    return h.hexdigest()

def content_hash(text):

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ================================
# MANIFEST
# ================================

def load_manifest():

    if not MANIFEST_FILE.exists():
        return {}

    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_manifest(manifest):

    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


# ================================
# DISCOVER DOCS
# ================================

def discover_pdf_paths(base_path):

    pdfs = []

    for root, _, files in os.walk(base_path):

        for file in files:

            if file.lower().endswith(".pdf"):
                pdfs.append(os.path.join(root, file))

    return pdfs


def list_index_names(pc):

    indexes = pc.list_indexes()

    if hasattr(indexes, "names"):
        return set(indexes.names())

    return {i.name for i in indexes}


def wait_for_index_ready(pc, index_name, timeout_seconds=180):

    deadline = time.time() + timeout_seconds

    while time.time() < deadline:

        description = pc.describe_index(index_name)
        status = getattr(description, "status", None)

        if isinstance(status, dict):
            if status.get("ready"):
                return
        elif status is not None and getattr(status, "ready", False):
            return
        else:
            return

        time.sleep(2)

    raise TimeoutError(f"Index '{index_name}' is not ready after {timeout_seconds}s")


def ensure_index_exists(pc):

    if INDEX_NAME in list_index_names(pc):
        return False

    pc.create_index(
        name=INDEX_NAME,
        dimension=INDEX_DIMENSION,
        metric=INDEX_METRIC,
        spec=ServerlessSpec(
            cloud=INDEX_CLOUD,
            region=INDEX_REGION,
        ),
    )

    wait_for_index_ready(pc, INDEX_NAME)
    return True


# ================================
# PINECONE AUDIT
# ================================

def pinecone_audit(index, label):

    stats = index.describe_index_stats()

    total_vectors = stats["total_vector_count"]

    namespaces = stats.get("namespaces", {})

    logging.info("")
    logging.info(f"=== PINECONE AUDIT ({label}) ===")
    logging.info(f"Total vectors: {total_vectors}")

    if namespaces:
        for ns, data in namespaces.items():
            logging.info(f"Namespace {ns}: {data['vector_count']}")

    logging.info("")

    return total_vectors


# ================================
# DETECT CHANGES
# ================================

def detect_document_changes(pdf_paths):

    manifest = load_manifest()

    current_hashes = {
        normalize_path(p): file_hash(p)
        for p in pdf_paths
    }

    new_docs = []
    updated_docs = []
    unchanged_docs = []
    removed_docs = []

    for path in pdf_paths:

        norm = normalize_path(path)

        if norm not in manifest:
            new_docs.append(path)

        elif manifest[norm]["hash"] != current_hashes[norm]:
            updated_docs.append(path)

        else:
            unchanged_docs.append(path)

    for stored in manifest:

        if stored not in current_hashes:
            removed_docs.append(stored)

    return manifest, current_hashes, new_docs, updated_docs, removed_docs, unchanged_docs


# ================================
# LOAD DOCUMENTS
# ================================

def load_documents(paths):

    documents = []
    failed = []

    for path in paths:

        try:

            loader = PyPDFLoader(path)

            docs = loader.load()

            source_file = Path(path).name

            for doc in docs:

                doc.metadata["document_id"] = source_file
                doc.metadata["source_file"] = source_file
                doc.metadata["source_path"] = normalize_path(path)

            documents.extend(docs)

            logging.info(f"Loaded: {path}")

        except Exception as e:

            logging.error(f"Error loading {path}: {e}")
            failed.append(path)

    return documents, failed


# ================================
# SPLIT DOCUMENTS
# ================================

def split_documents(documents):

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )

    chunks = splitter.split_documents(documents)

    logging.info(f"Chunks generated: {len(chunks)}")

    return chunks


# ================================
# DOCUMENT AUDIT
# ================================

def document_audit(pdf_paths, documents, chunks, failed):

    doc_files = set()
    chunk_files = set()

    pages_per_file = defaultdict(int)
    chunks_per_file = defaultdict(int)

    for d in documents:

        source = d.metadata["source_path"]

        doc_files.add(source)
        pages_per_file[source] += 1

    for c in chunks:

        source = c.metadata["source_path"]

        chunk_files.add(source)
        chunks_per_file[source] += 1

    skipped = set(pdf_paths) - doc_files

    logging.info("")
    logging.info("=== COUNTS ===")

    logging.info(f"Expected PDFs (ZIP): {len(pdf_paths)}")
    logging.info(f"PDFs loaded into documents: {len(doc_files)}")
    logging.info(f"PDFs present in chunks: {len(chunk_files)}")

    total_pages = sum(pages_per_file.values())

    logging.info(f"Total pages in documents: {total_pages}")
    logging.info(f"Total chunks: {len(chunks)}")

    logging.info(f"Files skipped (no extractable text): {len(skipped)}")
    logging.info(f"Files with loader errors: {len(failed)}")

    logging.info("")
    logging.info("=== MISSING FILES ===")

    missing_docs = set(pdf_paths) - doc_files
    missing_chunks = set(pdf_paths) - chunk_files
    no_chunks = doc_files - chunk_files

    logging.info(f"Missing in documents: {len(missing_docs)}")
    logging.info(f"Missing in chunks: {len(missing_chunks)}")
    logging.info(f"Loaded but without chunks: {len(no_chunks)}")

    logging.info("")
    logging.info("=== FILES USED ===")

    for f in sorted(doc_files):
        logging.info(f"- {Path(f).name}")

    logging.info("")
    logging.info("=== FILES SKIPPED (NO EXTRACTABLE TEXT) ===")

    for f in sorted(skipped):
        logging.info(f"- {Path(f).name}")

    logging.info("")
    logging.info("First files missing in documents:")

    for f in list(missing_docs)[:10]:
        logging.info(f"- {f}")

    logging.info("")
    logging.info("First files missing in chunks:")

    for f in list(missing_chunks)[:10]:
        logging.info(f"- {f}")

    logging.info("")
    logging.info("=== CHUNKS PER FILE ===")

    sorted_chunks = sorted(
        chunks_per_file.items(),
        key=lambda x: x[1],
        reverse=True
    )

    for file, count in sorted_chunks:
        logging.info(f"{count} - {Path(file).name}")


# ================================
# UPSERT
# ================================

def upsert_chunks(index, chunks, embeddings):

    vectors = []

    for chunk in chunks:

        text = chunk.page_content

        chunk_hash = content_hash(text)

        vector_id = f"{chunk.metadata['document_id']}_{chunk_hash}"

        embedding = embeddings.embed_query(text)

        vectors.append({
            "id": vector_id,
            "values": embedding,
            "metadata": {
                **chunk.metadata,
                "chunk_hash": chunk_hash
            }
        })

        if len(vectors) >= UPSERT_BATCH:

            index.upsert(vectors=vectors)

            logging.info(f"Upsert batch: {len(vectors)}")

            vectors = []

    if vectors:

        index.upsert(vectors=vectors)

        logging.info(f"Upsert batch: {len(vectors)}")


# ================================
# DELETE DOCUMENT
# ================================

def delete_document(index, document_id):

    logging.info(f"Deleting document: {document_id}")

    index.delete(filter={"document_id": document_id})


# ================================
# INGEST
# ================================

def ingest():

    logging.info("Starting ingestion")

    if ZIP_PATH.exists():
        logging.info(f"ZIP detected, extracting: {ZIP_PATH}")
        extracted = extract_zip()
        logging.info(f"ZIP extracted to: {extracted}")
    else:
        logging.info(f"ZIP not found, using existing docs folder: {DOCS_PATH}")

    pdf_paths = discover_pdf_paths(DOCS_PATH)

    if not pdf_paths:
        raise RuntimeError(f"No PDF files found under {DOCS_PATH}")

    manifest, hashes, new_docs, updated_docs, removed_docs, unchanged_docs = detect_document_changes(pdf_paths)

    logging.info("=== DOCUMENT STATUS ===")

    logging.info(f"NEW: {len(new_docs)}")
    logging.info(f"UPDATED: {len(updated_docs)}")
    logging.info(f"REMOVED: {len(removed_docs)}")
    logging.info(f"UNCHANGED: {len(unchanged_docs)}")

    pc = Pinecone(api_key=PINECONE_API_KEY)

    created_index = ensure_index_exists(pc)

    if created_index:
        logging.info(f"Pinecone index created: {INDEX_NAME}")

    index = pc.Index(INDEX_NAME)

    before_vectors = pinecone_audit(index, "BEFORE INGESTION")

    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-large",
        api_key=OPENAI_API_KEY
    )

    for removed in removed_docs:

        delete_document(index, Path(removed).name)

    for updated in updated_docs:

        delete_document(index, Path(updated).name)

    docs_to_process = new_docs + updated_docs

    # If index is empty but manifest says unchanged, force a full backfill.
    if not docs_to_process and before_vectors == 0 and unchanged_docs:
        logging.info("Index is empty; forcing full reindex from unchanged documents")
        docs_to_process = unchanged_docs

    if docs_to_process:

        documents, failed = load_documents(docs_to_process)

        chunks = split_documents(documents)

        document_audit(pdf_paths, documents, chunks, failed)

        upsert_chunks(index, chunks, embeddings)

    else:

        logging.info("No documents to process")

    new_manifest = {}

    for path in pdf_paths:

        norm = normalize_path(path)

        new_manifest[norm] = {
            "hash": hashes[norm]
        }

    save_manifest(new_manifest)

    logging.info("Manifest updated")

    after_vectors = pinecone_audit(index, "AFTER INGESTION")
    logging.info(f"PINECONE DELTA VECTORS: {after_vectors - before_vectors}")

    logging.info("Ingestion completed")


# ================================
# MAIN
# ================================

if __name__ == "__main__":

    setup_logger()

    ingest()