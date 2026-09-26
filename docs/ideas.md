##      Clinivue

### Objective

Given a visual and/or textual query, retrieve relevant visual entities and related information from multimodal data sources, reason over explicit relationships between those entities, and return an interpretable natural-language result grounded in traceable evidence.


### Example Usage

Suppose a **Medical Proffesional** uploads a chest-Xray and asks, "what findings are present,
what prior cases are visually similar, and what supporting literature or guidelines are relevant?"

The flow would be:

```
Chest X-ray + clinician question
        ↓
Vision model
        ↓
Detected findings / regions
        ↓
Visual retrieval of similar studies
        ↓
Medical entity linking
        ↓
Clinical knowledge graph
        ↓
Guideline / paper / report retrieval
        ↓
Evidence-grounded LLM synthesis
        ↓
Findings + similar cases + supporting evidence
```

### System Design

```mermaid
flowchart TD

    U[Clinician]
    UI[Web UI<br/>React / Next.js]
    API[FastAPI Backend]
    ORCH[Query Orchestrator]

    U --> UI
    UI -->|Upload chest X-ray + question| API
    API --> ORCH

    subgraph Vision["Vision Pipeline"]
        PRE[Image Preprocessing]
        BMC[BioMedCLIP]
        IMGEMB[Image Embedding]
        FINDINGS[Finding / Entity Extraction]
        LINKER[Medical Entity Linking]
    end

    ORCH --> PRE
    PRE --> BMC
    BMC --> IMGEMB
    BMC --> FINDINGS
    FINDINGS --> LINKER

    subgraph Vector["Vector Retrieval"]
        VDB[(Vector Database<br/>FAISS / Qdrant)]
        IVECS[Image Embeddings]
        DVECS[Document Embeddings]
    end

    IMGEMB --> VDB
    VDB --> IVECS
    VDB --> DVECS

    subgraph DB["Structured Storage"]
        PG[(PostgreSQL)]
        IMGMETA[Image / Study Metadata]
        DOCMETA[Document Metadata]
        PROV[Provenance / Evidence Metadata]
    end

    PG --> IMGMETA
    PG --> DOCMETA
    PG --> PROV

    VDB -->|Similar image IDs| PG

    subgraph KG["Clinical Knowledge Graph"]
        NEO[(Neo4j)]
        ENT[Medical Entities]
        REL[Clinical Relationships]
        SOURCES[Evidence Links]
    end

    LINKER --> NEO
    NEO --> ENT
    NEO --> REL
    NEO --> SOURCES

    subgraph RAG["RAG Pipeline"]
        QEXP[Query Expansion]
        TEXTENC[Biomedical Text Encoder]
        DRET[Document Retrieval]
        RERANK[Reranker]
        PASSAGES[Relevant Evidence Passages]
    end

    ORCH --> QEXP
    LINKER --> QEXP
    NEO --> QEXP

    QEXP --> TEXTENC
    TEXTENC --> VDB
    VDB --> DRET
    DRET --> PG
    DRET --> RERANK
    RERANK --> PASSAGES

    FUSION[Evidence Fusion]

    VDB -->|Similar studies| FUSION
    FINDINGS -->|Detected findings| FUSION
    NEO -->|Relevant graph paths| FUSION
    PASSAGES -->|Guidelines / papers / reports| FUSION
    PG -->|Metadata / provenance| FUSION

    PROMPT[Prompt / Context Builder]
    LLM[LLM<br/>Local or Cloud]
    RESPONSE[Grounded Response]

    FUSION --> PROMPT
    UI -->|Clinician question| PROMPT
    PROMPT --> LLM
    LLM --> RESPONSE

    RESPONSE --> API
    API --> UI

    UI --> OUT[Findings<br/>Similar Cases<br/>Evidence<br/>Reasoning Path<br/>Sources]
```

### Functional Requirements 

FR-1: Medical image ingestion

The system shall allow a user to upload a supported medical image

FR-2:

FR-3:

FR-4:

FR-5:

FR-6:

FR-7:

FR-8:

### Tools:

Python, Postgresql, FastAPI, Neo4j, pytorch, torchvision, FAISS, BioMedClip, pydantic, PyMuPDF, 


