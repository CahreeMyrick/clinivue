#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RIS_DIR="$ROOT_DIR/research-intelligence-system"
DIST_DIR="$ROOT_DIR/clarivue_qa/dist"

CONFIG_FILE="$RIS_DIR/ingestion/clinivue_config.yaml"
GRAPH_FILE="$RIS_DIR/indexer/knowledge-infusion/demo_graph.json"

PYTHON="$RIS_DIR/.venv/bin/python"


echo "=== Starting Clarivue ==="


# ---------------------------------------------------------------------------
# PostgreSQL
# ---------------------------------------------------------------------------

echo "--> Checking PostgreSQL container..."

if ! docker ps \
    --format '{{.Names}}' \
    | grep -q '^clinivue-postgres$'
then
    echo "    Starting clinivue-postgres..."
    docker start clinivue-postgres >/dev/null
fi


if ! docker ps \
    --format '{{.Names}}' \
    | grep -q '^clinivue-postgres$'
then
    echo "Error: PostgreSQL container failed to start."
    exit 1
fi

echo "    PostgreSQL is running."


# ---------------------------------------------------------------------------
# Ollama
# ---------------------------------------------------------------------------

echo "--> Checking Ollama..."

if ! curl \
    --silent \
    --fail \
    http://127.0.0.1:11434/api/tags \
    >/dev/null 2>&1
then

    echo "    Starting Ollama service..."

    brew services start ollama \
        >/dev/null 2>&1 \
        || true

    for _ in {1..10}; do

        if curl \
            --silent \
            --fail \
            http://127.0.0.1:11434/api/tags \
            >/dev/null 2>&1
        then
            break
        fi

        sleep 1

    done
fi


if ! curl \
    --silent \
    --fail \
    http://127.0.0.1:11434/api/tags \
    >/dev/null 2>&1
then

    echo "    Starting ollama serve..."

    ollama serve \
        >/dev/null 2>&1 &

    sleep 3
fi


if ! curl \
    --silent \
    --fail \
    http://127.0.0.1:11434/api/tags \
    >/dev/null 2>&1
then
    echo "Error: Ollama failed to start."
    exit 1
fi

echo "    Ollama is running."


# ---------------------------------------------------------------------------
# Python environment
# ---------------------------------------------------------------------------

echo "--> Checking Python environment..."

if [ ! -f "$PYTHON" ]; then
    echo "Error: Python environment not found:"
    echo "    $RIS_DIR/.venv"
    exit 1
fi

echo "    Python environment found."


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------

if ! "$PYTHON" -c \
    "import fastapi, uvicorn" \
    >/dev/null 2>&1
then
    echo "Error: FastAPI or Uvicorn is not installed."
    echo ""
    echo "Run:"
    echo "    cd $RIS_DIR"
    echo "    uv add fastapi uvicorn"
    exit 1
fi


# ---------------------------------------------------------------------------
# Frontend build
# ---------------------------------------------------------------------------

echo "--> Checking Clarivue frontend..."

if [ ! -d "$DIST_DIR" ]; then
    echo "Error: frontend dist directory not found:"
    echo "    $DIST_DIR"
    echo ""
    echo "Build the frontend before starting Clarivue."
    exit 1
fi


if [ ! -f "$DIST_DIR/index.html" ]; then
    echo "Error: frontend index.html not found:"
    echo "    $DIST_DIR/index.html"
    exit 1
fi

echo "    Frontend build found."


# ---------------------------------------------------------------------------
# RIS configuration
# ---------------------------------------------------------------------------

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: RIS configuration not found:"
    echo "    $CONFIG_FILE"
    exit 1
fi


export RIS_CONFIG="$CONFIG_FILE"

export CLARIVUE_HOST="127.0.0.1"
export CLARIVUE_PORT="8002"

export OLLAMA_HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"

export PGPASSWORD="${PGPASSWORD:-K7W6yDpnYw7lFUev75eIJ3AJoI8LAQYI9ZvTUz3A95c}"


# ---------------------------------------------------------------------------
# Knowledge graph
# ---------------------------------------------------------------------------

if [ -f "$GRAPH_FILE" ]; then
    export RIS_KNOWLEDGE_GRAPH="$GRAPH_FILE"

    echo "--> Knowledge graph enabled:"
    echo "    $GRAPH_FILE"
else
    unset RIS_KNOWLEDGE_GRAPH || true

    echo "--> Knowledge graph disabled."
fi


# ---------------------------------------------------------------------------
# Start FastAPI
# ---------------------------------------------------------------------------

echo ""
echo "=== Clarivue Ready ==="
echo ""
echo "Application: http://127.0.0.1:8002"
echo "API docs:   http://127.0.0.1:8002/docs"
echo "Health:     http://127.0.0.1:8002/health"
echo "QA API:     http://127.0.0.1:8002/api/qa"
echo ""
echo "Press Ctrl+C to stop."
echo ""


cd "$RIS_DIR"

exec "$PYTHON" \
    -m uvicorn \
    indexer.app:app \
    --host 127.0.0.1 \
    --port 8002 \
    "$@"
