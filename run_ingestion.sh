#!/usr/bin/env bash
set -euo pipefail

BUILD=false
NOCACHE=false

for arg in "$@"; do
  case "$arg" in
    --build)
      BUILD=true
      ;;
    --no-cache)
      NOCACHE=true
      ;;
    *)
      echo "Unknown option: $arg"
      echo "Usage: ./run_ingestion.sh [--build] [--no-cache]"
      exit 1
      ;;
  esac
done

cd "$(dirname "$0")"

if [ "$NOCACHE" = true ]; then
  echo "[ingestion] Building api image without cache..."
  docker compose build --no-cache --pull api
elif [ "$BUILD" = true ]; then
  echo "[ingestion] Building api image..."
  docker compose build api
fi

echo "[ingestion] Running ingestion inside api container..."
docker compose run --rm api python ingestion/ingest_documents.py

echo "[ingestion] Done."
