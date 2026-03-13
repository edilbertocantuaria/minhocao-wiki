import shutil
import time
import zipfile
from collections import Counter
from pathlib import Path
import re

from langchain_community.document_loaders import PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Pinecone as PineconeVectorStore

from pinecone import ServerlessSpec

from app.config import pinecone_client, INDEX_NAME

from app.logger import log_ingestion_audit

ZIP_FILE = "unb.zip"
EXTRACT_FOLDER = "docs/unb"
INDEX_DIMENSION = 3072
INDEX_METRIC = "cosine"
INDEX_CLOUD = "aws"
INDEX_REGION = "us-east-1"

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

    zip_path = Path(ZIP_FILE)
    extract_path = Path(EXTRACT_FOLDER)

    if not zip_path.exists():
        raise FileNotFoundError(f"ZIP file not found: {zip_path.resolve()}")

    if extract_path.exists():
        shutil.rmtree(extract_path)

    extract_path.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_path)

    return extract_path


def recreate_index(index_name):

    indexes = pinecone_client.list_indexes().names()

    if index_name in indexes:
        pinecone_client.delete_index(index_name)

        while index_name in pinecone_client.list_indexes().names():
            time.sleep(1)

    pinecone_client.create_index(
        name=index_name,
        dimension=INDEX_DIMENSION,
        metric=INDEX_METRIC,
        spec=ServerlessSpec(
            cloud=INDEX_CLOUD,
            region=INDEX_REGION
        )
    )

    index = pinecone_client.Index(index_name)

    for _ in range(60):
        try:
            index.describe_index_stats()
            return index
        except Exception:
            time.sleep(2)

    raise TimeoutError(f"Index {index_name} was not ready after creation")


def discover_pdf_paths(folder):

    return sorted(
        [path for path in Path(folder).rglob("*") if path.is_file() and path.suffix.lower() == ".pdf"]
    )


def normalize_path(path_value):

    return str(Path(path_value).resolve()).lower()


def to_posix_relative(path_value, root_folder):

    return str(Path(path_value).resolve().relative_to(Path(root_folder).resolve())).replace("\\", "/")


def format_document_number(number):

    digits = re.sub(r"\D", "", str(number))

    if not digits:
        return None

    return digits.zfill(4) if len(digits) <= 4 else digits


def build_fallback_source_title(file_path):

    return file_path.stem.replace("_", " ").replace("-", " ").upper()


def build_source_title(file_path):

    normalized_stem = re.sub(r"\s+", "_", file_path.stem.strip().lower())
    normalized_stem = normalized_stem.replace("-", "_")
    normalized_stem = re.sub(r"_+", "_", normalized_stem)
    tokens = [token for token in normalized_stem.split("_") if token]

    if len(tokens) < 3:
        return build_fallback_source_title(file_path)

    document_type = None
    body = None
    number = None
    year = None

    if tokens[0] in BODY_LABELS and len(tokens) >= 3 and tokens[1].isdigit() and tokens[2].isdigit():
        document_type = "resolucao"
        body = tokens[0]
        number = tokens[1]
        year = tokens[2]
    elif tokens[0] == "resolucao" and len(tokens) >= 4:
        document_type = "resolucao"
        body = tokens[1]
        number = tokens[2]
        year = tokens[3]
    elif tokens[0] == "ato" and len(tokens) >= 4:
        document_type = "ato"
        body = tokens[1]
        number = tokens[2]
        year = tokens[3]
    elif tokens[0] == "instrucao" and len(tokens) >= 5 and tokens[1] == "normativa":
        document_type = "instrucao_normativa"
        body = tokens[2]
        number = tokens[3]
        year = tokens[4]
    elif tokens[0] == "instrucao" and len(tokens) >= 4 and tokens[1] == "conjunta":
        document_type = "instrucao_conjunta"
        number = tokens[2]
        year = tokens[3]
    elif tokens[0] == "circular" and len(tokens) >= 4 and tokens[1] == "conjunta":
        document_type = "circular_conjunta"
        number = tokens[2]
        year = tokens[3]
        joint_bodies = [BODY_LABELS[token] for token in tokens[4:] if token in BODY_LABELS]

        if joint_bodies:
            return f"{DOC_TYPE_LABELS[document_type]} {' / '.join(joint_bodies)} Nº {format_document_number(number)}/{year}"
    elif tokens[0] == "circular" and len(tokens) >= 3:
        document_type = "circular"

        if len(tokens) >= 4 and tokens[1] in BODY_LABELS:
            body = tokens[1]
            number = tokens[2]
            year = tokens[3]
        else:
            number = tokens[1]
            year = tokens[2]
    elif tokens[0] == "memorando" and len(tokens) >= 5 and tokens[1] == "circular":
        document_type = "memorando_circular"

        if tokens[2] in BODY_LABELS:
            body = tokens[2]
            number = tokens[3]
            year = tokens[4]
    elif tokens[0] == "portaria" and len(tokens) >= 4:
        document_type = "portaria"
        body = tokens[1]
        number = tokens[2]
        year = tokens[3]
    elif tokens[0] == "decreto" and len(tokens) >= 3 and tokens[1].isdigit() and tokens[2].isdigit():
        document_type = "decreto"
        number = tokens[1]
        year = tokens[2]
    elif tokens[0] == "lei" and len(tokens) >= 2 and tokens[1].isdigit():
        document_type = "lei"
        number = tokens[1]

    if not document_type or not number:
        return build_fallback_source_title(file_path)

    number_text = format_document_number(number)

    if not number_text:
        return build_fallback_source_title(file_path)

    title = DOC_TYPE_LABELS.get(document_type, document_type.upper())

    if body in BODY_LABELS:
        title = f"{title} DO {BODY_LABELS[body]}"

    if year and str(year).isdigit() and len(str(year)) == 4:
        return f"{title} Nº {number_text}/{year}"

    return f"{title} Nº {number_text}"


def load_documents(pdf_paths, root_folder):

    documents = []
    failed_files = []

    for file_path in pdf_paths:

        try:
            loader = PyMuPDFLoader(str(file_path))
            pages = loader.load()
        except Exception as exc:
            failed_files.append(
                {
                    "source": build_source_title(file_path),
                    "source_file": to_posix_relative(file_path, root_folder),
                    "source_path": str(Path(file_path).resolve()),
                    "reason": str(exc)
                }
            )
            continue

        source = build_source_title(file_path)
        source_file = to_posix_relative(file_path, root_folder)
        source_path = str(Path(file_path).resolve())

        for doc in pages:

            text = (doc.page_content or "").strip()

            if text:
                doc.page_content = " ".join(text.split())
                doc.metadata["source"] = source
                doc.metadata["source_file"] = source_file
                doc.metadata["source_path"] = source_path
                documents.append(doc)

    return documents, failed_files


def build_ingestion_audit(pdf_paths, documents, chunks, failed_files, vector_count, extracted_folder):

    discovered_files = [to_posix_relative(path, extracted_folder) for path in pdf_paths]
    expected_files = {normalize_path(path) for path in pdf_paths}

    used_files = sorted(
        {
            doc.metadata.get("source_file", "unknown")
            for doc in documents
            if doc.metadata.get("source_file")
        }
    )

    used_sources = sorted(
        {
            doc.metadata.get("source", "unknown")
            for doc in documents
            if doc.metadata.get("source")
        }
    )

    used_file_paths = {
        normalize_path(doc.metadata["source_path"])
        for doc in documents
        if doc.metadata.get("source_path")
    }

    failed_file_paths = {
        normalize_path(item["source_path"])
        for item in failed_files
        if item.get("source_path")
    }

    chunk_file_paths = [
        chunk.metadata.get("source_path", "unknown")
        for chunk in chunks
    ]
    loaded_chunks = {
        normalize_path(source_path)
        for source_path in chunk_file_paths
        if source_path != "unknown"
    }

    skipped_no_text_files = sorted(
        discovered_file
        for discovered_file in discovered_files
        if normalize_path(Path(extracted_folder) / discovered_file) not in used_file_paths
        and normalize_path(Path(extracted_folder) / discovered_file) not in failed_file_paths
    )

    missing_in_documents = sorted(
        to_posix_relative(path, extracted_folder)
        for path in pdf_paths
        if normalize_path(path) not in used_file_paths
    )
    missing_in_chunks = sorted(
        to_posix_relative(path, extracted_folder)
        for path in pdf_paths
        if normalize_path(path) not in loaded_chunks
    )
    docs_without_chunks = sorted(
        source
        for source in used_files
        if normalize_path(Path(extracted_folder) / source) not in loaded_chunks
    )

    chunks_per_file = Counter(
        chunk.metadata.get("source_file", "unknown")
        for chunk in chunks
    )

    return {
        "timestamp": str(time.strftime("%Y-%m-%d %H:%M:%S")),
        "zip_file": str(Path(ZIP_FILE).resolve()),
        "extracted_folder": str(Path(extracted_folder).resolve()),
        "index": {
            "name": INDEX_NAME,
            "dimension": INDEX_DIMENSION,
            "metric": INDEX_METRIC,
            "cloud": INDEX_CLOUD,
            "region": INDEX_REGION,
            "total_vector_count": vector_count
        },
        "counts": {
            "expected_pdfs": len(expected_files),
            "pdfs_loaded_into_documents": len(used_file_paths),
            "pdfs_present_in_chunks": len(loaded_chunks),
            "total_pages_in_documents": len(documents),
            "total_chunks": len(chunks),
            "files_skipped_no_text": len(skipped_no_text_files),
            "files_with_loader_errors": len(failed_files),
            "missing_in_documents": len(missing_in_documents),
            "missing_in_chunks": len(missing_in_chunks),
            "loaded_without_chunks": len(docs_without_chunks)
        },
        "files": {
            "discovered": discovered_files,
            "used": used_files,
            "used_sources": used_sources,
            "skipped_no_text": skipped_no_text_files,
            "missing_in_documents": missing_in_documents,
            "missing_in_chunks": missing_in_chunks,
            "loaded_without_chunks": docs_without_chunks,
            "failed": failed_files
        },
        "chunks_per_file": [
            {"source_file": source, "chunk_count": count}
            for source, count in chunks_per_file.most_common()
        ]
    }


def print_audit_summary(audit_report):

    counts = audit_report["counts"]

    print(f"ZIP extraido para: {audit_report['extracted_folder']}")
    print(f"PDF files discovered: {counts['expected_pdfs']}")
    print("=== COUNTS ===")
    print("Expected PDFs (ZIP):", counts["expected_pdfs"])
    print("PDFs loaded into documents:", counts["pdfs_loaded_into_documents"])
    print("PDFs present in chunks:", counts["pdfs_present_in_chunks"])
    print("Total pages in documents:", counts["total_pages_in_documents"])
    print("Total chunks:", counts["total_chunks"])
    print("Files skipped (no extractable text):", counts["files_skipped_no_text"])
    print("Files with loader errors:", counts["files_with_loader_errors"])
    print("Total vectors in Pinecone:", audit_report["index"]["total_vector_count"])

    print("\n=== FILES USED ===")
    for source_file in audit_report["files"]["used"]:
        print("-", source_file)

    if audit_report["files"]["skipped_no_text"]:
        print("\n=== FILES SKIPPED (NO EXTRACTABLE TEXT) ===")
        for source in audit_report["files"]["skipped_no_text"]:
            print("-", source)

    if audit_report["files"]["failed"]:
        print("\n=== LOADER FAILURES ===")
        for item in audit_report["files"]["failed"][:10]:
            print("-", item["source_file"], "->", item["reason"])

    print("\n=== CHUNKS PER FILE ===")
    for item in audit_report["chunks_per_file"]:
        print(item["chunk_count"], "-", item["source_file"])


def ingest():

    path = extract_zip()
    index = recreate_index(INDEX_NAME)
    pdf_paths = discover_pdf_paths(path)

    documents, failed_files = load_documents(pdf_paths, path)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150
    )

    chunks = splitter.split_documents(documents)

    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-large"
    )

    PineconeVectorStore.from_documents(
        chunks,
        embeddings,
        index_name=INDEX_NAME
    )

    stats = index.describe_index_stats()
    vector_count = stats.get("total_vector_count", 0)

    audit_report = build_ingestion_audit(
        pdf_paths=pdf_paths,
        documents=documents,
        chunks=chunks,
        failed_files=failed_files,
        vector_count=vector_count,
        extracted_folder=path
    )

    log_ingestion_audit(audit_report)
    print_audit_summary(audit_report)

    print("Indexação concluída")
    print("Auditoria salva em logs/ingestion_audit_latest.json e logs/ingestion_audit.jsonl")


if __name__ == "__main__":
    ingest()
