Param(
    [switch]$Build,
    [switch]$NoCache
)

$ErrorActionPreference = "Stop"

Set-Location -Path $PSScriptRoot

if ($NoCache) {
    Write-Host "[ingestion] Building api image without cache..."
    docker compose build --no-cache --pull api
} elseif ($Build) {
    Write-Host "[ingestion] Building api image..."
    docker compose build api
}

Write-Host "[ingestion] Running ingestion inside api container..."
docker compose run --rm api python ingestion/ingest_documents.py

Write-Host "[ingestion] Done."
