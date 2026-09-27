"""FastAPI application for Clarivue and the Research Intelligence System."""

from __future__ import annotations

import os
import re
import threading
from importlib import import_module
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from indexer.config import IndexerConfig
from indexer.database.connection import DatabaseManager
from indexer.embeddings.ollama import OllamaEmbeddingProvider
from indexer.embeddings.sentence_transformers import SentenceTransformersProvider
from indexer.qa.ollama import OllamaQwenProvider
from indexer.qa.service import QuestionAnsweringService
from indexer.retrieval.repository import RetrievalRepository
from indexer.retrieval.service import RetrievalService


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

RIS_ROOT = Path(__file__).resolve().parents[1]
CLARIVUE_ROOT = RIS_ROOT.parent / "clarivue_qa"
DIST_DIR = CLARIVUE_ROOT / "dist"

DEFAULT_CONFIG_PATH = RIS_ROOT / "ingestion" / "clinivue_config.yaml"

DEFAULT_GRAPH_PATH = (
    Path(__file__).resolve().parent
    / "knowledge-infusion"
    / "demo_graph.json"
)


CONFIG_PATH = Path(
    os.environ.get(
        "RIS_CONFIG",
        str(DEFAULT_CONFIG_PATH),
    )
)

GRAPH_PATH = os.environ.get(
    "RIS_KNOWLEDGE_GRAPH",
    str(DEFAULT_GRAPH_PATH) if DEFAULT_GRAPH_PATH.exists() else "",
).strip()

HOST = os.environ.get(
    "CLARIVUE_HOST",
    "127.0.0.1",
)

PORT = int(
    os.environ.get(
        "CLARIVUE_PORT",
        "8002",
    )
)


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Clarivue",
    version="1.0.0",
    description=(
        "Explainable research QA using hybrid retrieval, "
        "knowledge graphs, and language models."
    ),
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class QARequest(BaseModel):
    question: str


# ---------------------------------------------------------------------------
# Global services
# ---------------------------------------------------------------------------

SERVICE: RetrievalService | None = None
CONFIG: IndexerConfig | None = None
QA: QuestionAnsweringService | None = None

SERVICE_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# Service construction
# ---------------------------------------------------------------------------

def build_retrieval_service() -> tuple[RetrievalService, IndexerConfig]:
    config = IndexerConfig.from_yaml(CONFIG_PATH)

    database = DatabaseManager(
        config.database_url
    )

    if ":" in config.embedding_model:
        embedding_provider = OllamaEmbeddingProvider(
            model=config.embedding_model,
            model_version=config.embedding_model_version,
            expected_dimensions=config.embedding_dimensions,
        )
    else:
        embedding_provider = SentenceTransformersProvider(
            model_name=config.embedding_model,
            model_version=config.embedding_model_version,
            expected_dimensions=config.embedding_dimensions,
        )

    repository = RetrievalRepository(
        db_manager=database,
        embedding_provider=embedding_provider,
    )

    service = RetrievalService(
        repository=repository,
    )

    return service, config


def ensure_services() -> None:
    global SERVICE
    global CONFIG
    global QA

    if QA is not None:
        return

    with SERVICE_LOCK:
        if QA is not None:
            return

        service, config = build_retrieval_service()

        llm = OllamaQwenProvider(
            model=config.llm_model,
            timeout_seconds=float(
                os.environ.get(
                    "RIS_LLM_TIMEOUT",
                    "300",
                )
            ),
            max_tokens=1024,
            base_url=os.environ.get(
                "OLLAMA_HOST",
                "http://127.0.0.1:11434",
            ),
        )

        if GRAPH_PATH:
            graph_file = Path(GRAPH_PATH)

            if not graph_file.exists():
                raise FileNotFoundError(
                    f"Knowledge graph not found: {graph_file}"
                )

            knowledge = import_module(
                "indexer.knowledge-infusion"
            )

            service = knowledge.KnowledgeInfusedRetrievalService(
                service,
                knowledge.LLMQueryParser(llm),
                knowledge.load_graph(str(graph_file)),
            )

        SERVICE = service
        CONFIG = config
        QA = QuestionAnsweringService(
            service,
            llm,
        )


# ---------------------------------------------------------------------------
# QA pipeline
# ---------------------------------------------------------------------------

def evidence_response(question: str) -> dict:
    ensure_services()

    assert SERVICE is not None
    assert CONFIG is not None
    assert QA is not None

    context = SERVICE.retrieve(
        question,
        top_k=CONFIG.top_k,
        candidate_k=CONFIG.candidate_k,
    )

    answer = QA.answer_from_evidence(
        question,
        context,
    )

    graph = getattr(
        context,
        "graph_context",
        None,
    )

    entities = []

    if graph is not None:
        entities = [
            {
                "name": entity.mention,
                "type": entity.type,
                "negated": entity.negated,
                "kg_id": entity.kg_id,
            }
            for entity in graph.normalized.linked.entities
        ]

    paths = []

    if graph is not None:
        paths = [
            {
                **path.model_dump(),
                "relationships": [
                    edge.relation
                    for edge in path.edges
                ],
            }
            for path in graph.paths
        ]

    sources = []

    for item in context.items:
        sources.append(
            {
                "id": item.evidence_id,
                "title": (
                    item.document_title
                    or item.document_id
                ),
                "publisher": (
                    "Research Intelligence System"
                ),
                "kind": (
                    "Indexed research evidence"
                ),
                "summary": item.source_text,
                "passage": item.source_text,
                "detail": (
                    f"{item.section_title}; "
                    f"chunk {item.chunk_id}"
                ),
                "date": str(
                    item.publication_year
                    or "Unknown publication year"
                ),
                "url": None,
                "document_id": item.document_id,
                "chunk_id": item.chunk_id,
                "retrieval_score": (
                    item.relevance_score
                ),
                "retrieved": True,
            }
        )

    graph_metadata = {}

    if graph is not None:
        service_graph = getattr(
            SERVICE,
            "graph",
            None,
        )

        if service_graph is not None:
            graph_metadata = dict(
                service_graph.graph
            )

    return {
        "question": question,

        "headline": (
            "Answer grounded in indexed research"
            if sources
            else "Insufficient indexed evidence"
        ),

        "answer": answer.answer,

        "paragraphs": [
            paragraph
            for paragraph in answer.answer.split("\n\n")
            if paragraph.strip()
        ],

        "citations": [
            citation.model_dump()
            for citation in answer.citations
        ],

        "entities": entities,

        "graph_paths": paths,

        "knowledge_graph": {
            "enabled": graph is not None,
            "metadata": graph_metadata,
        },

        "source_ids": [
            source["id"]
            for source in sources
        ],

        "sources": sources,

        "retrieval": {
            "mode": (
                "knowledge_infused_hybrid"
                if graph is not None
                else "research_intelligence_system_hybrid"
            ),
            "source_count": len(sources),
            "configuration": CONFIG_PATH.name,
            "embedding_model": CONFIG.embedding_model,
            "embedding_dimensions": CONFIG.embedding_dimensions,
            "embedding_model_version": (
                CONFIG.embedding_model_version
            ),
            "retrieved_count": len(sources),
            "llm_model": CONFIG.llm_model,
        },

        "missing_context": [
            "Clinical context must be supplied separately"
        ],

        "uncertainty": (
            "Retrieved research evidence is not a diagnosis "
            "and may not directly apply to an individual."
        ),

        "safety": (
            "For urgent symptoms, seek appropriate medical "
            "care rather than relying on this research "
            "retrieval service."
        ),

        "disclaimer": (
            "Evidence retrieved from the existing Research "
            "Intelligence System; not clinical advice."
        ),
    }


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "service": "clarivue",
        "retrieval": "hybrid",
        "configuration": CONFIG_PATH.name,
        "knowledge_graph": bool(GRAPH_PATH),
    }


@app.get("/api/evidence")
def evidence() -> dict:
    return {
        "sources": [],
        "message": (
            "Submit a question to retrieve evidence."
        ),
    }


@app.post("/api/qa")
def qa(request: QARequest) -> dict:
    question = re.sub(
        r"\s+",
        " ",
        request.question.strip(),
    )

    if not question:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_request",
                "message": "question is required",
            },
        )

    if len(question) > 1500:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_request",
                "message": (
                    "question must be "
                    "1,500 characters or fewer"
                ),
            },
        )

    try:
        return evidence_response(
            question
        )

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "retrieval_failed",
                "message": str(exc),
            },
        ) from exc


# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------

if not DIST_DIR.exists():
    raise RuntimeError(
        f"Clarivue frontend build not found: {DIST_DIR}"
    )


ASSETS_DIR = DIST_DIR / "assets"

if ASSETS_DIR.exists():
    app.mount(
        "/assets",
        StaticFiles(
            directory=str(ASSETS_DIR)
        ),
        name="assets",
    )


@app.get("/")
def index():
    return FileResponse(
        DIST_DIR / "index.html"
    )


@app.get("/{path:path}")
def frontend(path: str):
    """
    Serve built frontend files and support SPA routing.

    API routes above are matched before this catch-all route.
    """

    requested = (
        DIST_DIR / path
    ).resolve()

    dist_resolved = DIST_DIR.resolve()

    # Prevent path traversal outside dist/.
    if (
        requested.is_file()
        and dist_resolved in requested.parents
    ):
        return FileResponse(
            requested
        )

    # SPA fallback.
    index_file = DIST_DIR / "index.html"

    if index_file.exists():
        return FileResponse(
            index_file
        )

    raise HTTPException(
        status_code=404,
        detail={
            "error": "not_found",
            "message": (
                "The requested Clarivue route "
                "does not exist."
            ),
        },
    )


# ---------------------------------------------------------------------------
# Direct execution
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(
        f"Clarivue: http://{HOST}:{PORT}"
    )

    print(
        f"FastAPI docs: http://{HOST}:{PORT}/docs"
    )

    print(
        f"Configuration: {CONFIG_PATH}"
    )

    print(
        f"Frontend: {DIST_DIR}"
    )

    print(
        f"Knowledge graph: {GRAPH_PATH or 'disabled'}"
    )

    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
    )
