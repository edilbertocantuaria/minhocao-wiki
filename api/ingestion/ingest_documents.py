import shutil
import sys
import time
import zipfile
import json
import hashlib
import os
from collections import Counter
from pathlib import Path
import re

from langchain_community.document_loaders import PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Pinecone as PineconeVectorStore

from pinecone import ServerlessSpec

API_ROOT = Path(__file__).resolve().parents[1]

if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.config import pinecone_client, INDEX_NAME

from app.logger import log_ingestion_audit

ZIP_FILE = "unb.zip"
EXTRACT_FOLDER = "docs/unb"
INDEX_DIMENSION = 3072
INDEX_METRIC = "cosine"
INDEX_CLOUD = "aws"
INDEX_REGION = "us-east-1"
INGESTION_MANIFEST_FILE = API_ROOT / "logs" / "ingestion_manifest.json"
INGESTION_TEXT_LOG_PATTERN = "ingestion_%Y%m%d_%H%M%S.txt"

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


def print_stage(step, total, message):

    print(f"\n[{step}/{total}] {message}")


def print_item_progress(prefix, current, total, item_name):

    print(f"{prefix} {current}/{total} - {item_name}")


def extract_zip():

    zip_path = Path(ZIP_FILE)
    extract_path = Path(EXTRACT_FOLDER)

    if not zip_path.is_absolute():
        zip_path = API_ROOT / zip_path

    if not extract_path.is_absolute():
        extract_path = API_ROOT / extract_path

    zip_path = zip_path.resolve()
    extract_path = extract_path.resolve()
    force_extract = os.getenv("INGEST_FORCE_EXTRACT", "false").strip().lower() in {"1", "true", "yes"}

    if extract_path.exists() and any(extract_path.iterdir()) and not force_extract:
        return extract_path

    if force_extract and extract_path.exists():
        shutil.rmtree(extract_path)

    if not zip_path.exists():
        raise FileNotFoundError(f"ZIP file not found: {zip_path.resolve()}")

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


def get_or_create_index(index_name):

    indexes = pinecone_client.list_indexes().names()

    if index_name not in indexes:
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

    raise TimeoutError(f"Index {index_name} was not ready")


def file_sha256(file_path):

    digest = hashlib.sha256()

    with Path(file_path).open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)

    return digest.hexdigest()


def load_previous_manifest():

    if not INGESTION_MANIFEST_FILE.exists():
        return {}

    with INGESTION_MANIFEST_FILE.open("r", encoding="utf-8") as handle:
        data = json.load(handle) or {}

    return data.get("files", {})


def save_manifest(files_manifest):

    INGESTION_MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "files": files_manifest
    }

    with INGESTION_MANIFEST_FILE.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def build_current_manifest(pdf_paths, extracted_folder):

    manifest = {}
    total_files = len(pdf_paths)

    if total_files:
        print(f"[MANIFEST] Calculando hash de {total_files} arquivo(s)...")

    for index, path in enumerate(pdf_paths, start=1):
        resolved_path = Path(path).resolve()
        source_file = to_posix_relative(resolved_path, extracted_folder)
        print_item_progress("[MANIFEST]", index, total_files, source_file)
        stat = resolved_path.stat()
        manifest[source_file] = {
            "source_path": str(resolved_path),
            "sha256": file_sha256(resolved_path),
            "size": stat.st_size,
            "modified_at": int(stat.st_mtime)
        }

    return manifest


def detect_manifest_changes(previous_manifest, current_manifest):

    previous_files = set(previous_manifest.keys())
    current_files = set(current_manifest.keys())

    new_files = current_files - previous_files
    removed_files = previous_files - current_files
    intersection = previous_files & current_files

    updated_files = {
        source_file
        for source_file in intersection
        if previous_manifest[source_file].get("sha256") != current_manifest[source_file].get("sha256")
    }

    unchanged_files = intersection - updated_files

    return {
        "new": sorted(new_files),
        "updated": sorted(updated_files),
        "removed": sorted(removed_files),
        "unchanged": sorted(unchanged_files)
    }


def delete_vectors_for_files(index, source_files):

    total_files = len(source_files)

    for position, source_file in enumerate(source_files, start=1):
        print_item_progress("[PINECONE-DELETE]", position, total_files, source_file)
        index.delete(filter={"source_file": {"$eq": source_file}})


def summarize_pinecone_namespaces(index_stats):

    namespaces = index_stats.get("namespaces", {}) or {}

    return [
        {
            "namespace": namespace if namespace else "default",
            "vector_count": data.get("vector_count", 0)
        }
        for namespace, data in sorted(namespaces.items(), key=lambda item: item[0])
    ]


def save_text_audit_log(audit_text):

    logs_dir = API_ROOT / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    log_path = logs_dir / time.strftime(INGESTION_TEXT_LOG_PATTERN)

    with log_path.open("w", encoding="utf-8") as handle:
        handle.write(audit_text + "\n")

    return log_path


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
    loaded_files = set()

    total_files = len(pdf_paths)

    if total_files:
        print(f"[LOAD] Carregando {total_files} arquivo(s) para processamento...")

    for file_position, file_path in enumerate(pdf_paths, start=1):
        file_label = to_posix_relative(file_path, root_folder)
        print_item_progress("[LOAD]", file_position, total_files, file_label)

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
        loaded_files.add(source_file)

        for doc in pages:

            text = (doc.page_content or "").strip()

            if text:
                doc.page_content = " ".join(text.split())
                doc.metadata["source"] = source
                doc.metadata["source_file"] = source_file
                doc.metadata["source_path"] = source_path
                documents.append(doc)

    return documents, failed_files, loaded_files


def build_ingestion_audit(
    pdf_paths,
    documents,
    chunks,
    failed_files,
    vector_count,
    extracted_folder,
    changes,
    pinecone_before,
    pinecone_after,
    files_to_process,
    files_to_delete
):

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
        "zip_file": str((Path(ZIP_FILE) if Path(ZIP_FILE).is_absolute() else (API_ROOT / ZIP_FILE)).resolve()),
        "extracted_folder": str(Path(extracted_folder).resolve()),
        "index": {
            "name": INDEX_NAME,
            "dimension": INDEX_DIMENSION,
            "metric": INDEX_METRIC,
            "cloud": INDEX_CLOUD,
            "region": INDEX_REGION,
            "total_vector_count": vector_count
        },
        "pinecone_audit": {
            "before": {
                "total_vector_count": pinecone_before.get("total_vector_count", 0),
                "index_fullness": pinecone_before.get("index_fullness", 0),
                "namespaces": summarize_pinecone_namespaces(pinecone_before)
            },
            "after": {
                "total_vector_count": pinecone_after.get("total_vector_count", 0),
                "index_fullness": pinecone_after.get("index_fullness", 0),
                "namespaces": summarize_pinecone_namespaces(pinecone_after)
            },
            "delta_total_vectors": pinecone_after.get("total_vector_count", 0) - pinecone_before.get("total_vector_count", 0),
            "operations": {
                "files_deleted": len(files_to_delete),
                "files_reindexed": len(files_to_process),
                "chunks_upserted": len(chunks)
            }
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
            "loaded_without_chunks": len(docs_without_chunks),
            "new_files": len(changes["new"]),
            "updated_files": len(changes["updated"]),
            "removed_files": len(changes["removed"]),
            "unchanged_files": len(changes["unchanged"])
        },
        "files": {
            "discovered": discovered_files,
            "used": used_files,
            "used_sources": used_sources,
            "skipped_no_text": skipped_no_text_files,
            "missing_in_documents": missing_in_documents,
            "missing_in_chunks": missing_in_chunks,
            "loaded_without_chunks": docs_without_chunks,
            "failed": failed_files,
            "changes": changes
        },
        "chunks_per_file": [
            {"source_file": source, "chunk_count": count}
            for source, count in chunks_per_file.most_common()
        ]
    }


def print_audit_summary(audit_report):

    counts = audit_report["counts"]

    lines = [
        f"ZIP extracted to: {audit_report['extracted_folder']}",
        f"PDF files discovered: {counts['expected_pdfs']}",
        "=== COUNTS ===",
        f"Expected PDFs (ZIP): {counts['expected_pdfs']}",
        f"PDFs loaded into documents: {counts['pdfs_loaded_into_documents']}",
        f"PDFs present in chunks: {counts['pdfs_present_in_chunks']}",
        f"Total pages in documents: {counts['total_pages_in_documents']}",
        f"Total chunks: {counts['total_chunks']}",
        f"Files skipped (no extractable text): {counts['files_skipped_no_text']}",
        f"Files with loader errors: {counts['files_with_loader_errors']}",
        f"New files: {counts['new_files']}",
        f"Updated files: {counts['updated_files']}",
        f"Removed files: {counts['removed_files']}",
        f"Unchanged files: {counts['unchanged_files']}",
        f"Total vectors in Pinecone: {audit_report['index']['total_vector_count']}"
    ]

    changes = audit_report["files"].get("changes", {})

    lines.append("\n=== FILE CHANGES ===")

    lines.append("\nNew files:")
    if changes.get("new"):
        for source_file in changes["new"]:
            lines.append(f"- {source_file}")
    else:
        lines.append("- none")

    lines.append("\nUpdated files:")
    if changes.get("updated"):
        for source_file in changes["updated"]:
            lines.append(f"- {source_file}")
    else:
        lines.append("- none")

    lines.append("\nRemoved files:")
    if changes.get("removed"):
        for source_file in changes["removed"]:
            lines.append(f"- {source_file}")
    else:
        lines.append("- none")

    lines.append("\nUnchanged files:")
    if changes.get("unchanged"):
        for source_file in changes["unchanged"]:
            lines.append(f"- {source_file}")
    else:
        lines.append("- none")

    pinecone_audit = audit_report.get("pinecone_audit", {})
    pinecone_before = pinecone_audit.get("before", {})
    pinecone_after = pinecone_audit.get("after", {})
    pinecone_ops = pinecone_audit.get("operations", {})

    lines.append("\n=== PINECONE AUDIT ===")
    lines.append(f"Vectors before: {pinecone_before.get('total_vector_count', 0)}")
    lines.append(f"Vectors after: {pinecone_after.get('total_vector_count', 0)}")
    lines.append(f"Vector delta: {pinecone_audit.get('delta_total_vectors', 0)}")
    lines.append(f"Files deleted from index: {pinecone_ops.get('files_deleted', 0)}")
    lines.append(f"Files reindexed: {pinecone_ops.get('files_reindexed', 0)}")
    lines.append(f"Chunks upserted: {pinecone_ops.get('chunks_upserted', 0)}")

    lines.append("\nNamespaces before:")
    for item in pinecone_before.get("namespaces", []):
        lines.append(f"- {item['namespace']}: {item['vector_count']}")

    lines.append("\nNamespaces after:")
    for item in pinecone_after.get("namespaces", []):
        lines.append(f"- {item['namespace']}: {item['vector_count']}")

    lines.append("\n=== FILES USED ===")
    for source_file in audit_report["files"]["used"]:
        lines.append(f"- {source_file}")

    if audit_report["files"]["skipped_no_text"]:
        lines.append("\n=== FILES SKIPPED (NO EXTRACTABLE TEXT) ===")
        for source in audit_report["files"]["skipped_no_text"]:
            lines.append(f"- {source}")

    if audit_report["files"]["failed"]:
        lines.append("\n=== LOADER FAILURES ===")
        for item in audit_report["files"]["failed"][:10]:
            lines.append(f"- {item['source_file']} -> {item['reason']}")

    lines.append("\n=== CHUNKS PER FILE ===")
    for item in audit_report["chunks_per_file"]:
        lines.append(f"{item['chunk_count']} - {item['source_file']}")

    for line in lines:
        print(line)

    return "\n".join(lines)


def ingest():

    total_steps = 11
    stage = 1

    print_stage(stage, total_steps, "Preparando origem dos documentos")
    path = extract_zip()
    stage += 1

    print_stage(stage, total_steps, "Descobrindo arquivos PDF")
    pdf_paths = discover_pdf_paths(path)
    print(f"[DISCOVERY] {len(pdf_paths)} PDF(s) encontrado(s)")
    stage += 1

    print_stage(stage, total_steps, "Lendo manifesto anterior")
    previous_manifest = load_previous_manifest()
    print(f"[MANIFEST] {len(previous_manifest)} item(ns) no manifesto anterior")
    stage += 1

    print_stage(stage, total_steps, "Calculando manifesto atual")
    current_manifest = build_current_manifest(pdf_paths, path)
    stage += 1

    print_stage(stage, total_steps, "Identificando delta de mudanças")
    changes = detect_manifest_changes(previous_manifest, current_manifest)
    print(
        "[CHANGES] "
        f"new={len(changes['new'])}, "
        f"updated={len(changes['updated'])}, "
        f"removed={len(changes['removed'])}, "
        f"unchanged={len(changes['unchanged'])}"
    )
    stage += 1

    print_stage(stage, total_steps, "Conectando ao Pinecone")
    force_recreate = os.getenv("INGEST_FORCE_RECREATE_INDEX", "false").strip().lower() in {"1", "true", "yes"}
    index = recreate_index(INDEX_NAME) if force_recreate else get_or_create_index(INDEX_NAME)
    before_stats = index.describe_index_stats()
    stage += 1

    print_stage(stage, total_steps, "Removendo vetores de arquivos atualizados/removidos")
    files_to_delete = sorted(set(changes["updated"] + changes["removed"]))

    if files_to_delete:
        delete_vectors_for_files(index, files_to_delete)
    else:
        print("[PINECONE-DELETE] Nenhum arquivo para remover")
    stage += 1

    print_stage(stage, total_steps, "Carregando documentos alterados")
    files_to_process = sorted(set(changes["new"] + changes["updated"]))
    processing_paths = [Path(path) / source_file for source_file in files_to_process]
    print(f"[PROCESS] {len(processing_paths)} arquivo(s) para ingestão")

    documents, failed_files, loaded_files = load_documents(processing_paths, path)
    print(f"[LOAD] Páginas válidas carregadas: {len(documents)}")
    stage += 1

    print_stage(stage, total_steps, "Gerando chunks")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150
    )

    chunks = splitter.split_documents(documents)
    print(f"[CHUNKS] Total de chunks gerados: {len(chunks)}")
    stage += 1

    print_stage(stage, total_steps, "Enviando chunks para Pinecone")
    if chunks:
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-large"
        )

        PineconeVectorStore.from_documents(
            chunks,
            embeddings,
            index_name=INDEX_NAME
        )
    else:
        print("[UPSERT] Nenhum chunk para enviar")
    stage += 1

    print_stage(stage, total_steps, "Atualizando manifesto e gerando auditoria")
    next_manifest = {
        source_file: metadata
        for source_file, metadata in previous_manifest.items()
        if source_file not in changes["removed"]
    }

    for source_file in loaded_files:
        if source_file in current_manifest:
            next_manifest[source_file] = current_manifest[source_file]

    for source_file in changes["unchanged"]:
        if source_file in current_manifest:
            next_manifest[source_file] = current_manifest[source_file]

    save_manifest(next_manifest)

    after_stats = index.describe_index_stats()
    vector_count = after_stats.get("total_vector_count", 0)

    audit_report = build_ingestion_audit(
        pdf_paths=pdf_paths,
        documents=documents,
        chunks=chunks,
        failed_files=failed_files,
        vector_count=vector_count,
        extracted_folder=path,
        changes=changes,
        pinecone_before=before_stats,
        pinecone_after=after_stats,
        files_to_process=files_to_process,
        files_to_delete=files_to_delete
    )

    log_ingestion_audit(audit_report)
    summary_text = print_audit_summary(audit_report)
    text_log_path = save_text_audit_log(summary_text)

    stage += 1
    print_stage(stage, total_steps, "Finalizado")
    print("Indexação concluída")
    print("Auditoria salva em logs/ingestion_audit_latest.json e logs/ingestion_audit.jsonl")
    print(f"Resumo em texto salvo em: {text_log_path}")


if __name__ == "__main__":
    ingest()
