# Clinivue / Clarivue: Windows setup and ChatGPT handoff

Prepared September 27, 2026 from repository commit `71ebf4b`.

This guide runs the **local Clarivue research question-answering web app** on a Windows computer after cloning the Clinivue repository. It covers Python, Docker, PostgreSQL/pgvector, Ollama, document indexing, startup, verification, and troubleshooting.

The commands were checked against the repository code, but have not been executed on Windows. If the repository changes, compare the configuration and entry points with the files listed at the end of this guide.

## 1. Give this document to ChatGPT

Upload this Markdown file to ChatGPT and paste the following message:

> Help me get this repository running on my Windows computer using the attached setup guide. I have already cloned the repo. Walk me through one stage at a time using native Windows PowerShell commands. First ask where I cloned the repo, what version of Windows I have, and whether Docker Desktop, Ollama, and uv are installed. Check each stage's output before proceeding. The target is the local Clarivue research QA web app, served by indexer.app:app on port 8002. Use the Python environment inside research-intelligence-system, PostgreSQL/pgvector on host port 5433, and the medical corpus. Do not confuse the root image experiments with this app. Do not assume my friend's Docker volume, Python environment, model cache, or custom Ollama model came through Git. Do not ask me to paste passwords. Do not delete database volumes or change dependency versions just to try something. If a command fails, explain the error and request the smallest relevant diagnostic output. If you need repository files that are not in this document, ask me for those files instead of guessing their contents. This guide was inspected against code but not tested on Windows.

If setup fails, send ChatGPT:

- The stage number and exact command that failed.
- The complete error text, with passwords and tokens removed.
- Your current folder from `Get-Location`.
- The relevant diagnostics from section 12.

ChatGPT cannot inspect your local files just because you uploaded this guide. You may need to upload individual code/config files or the repository separately.

## 2. What runs where

| Component | Runs in | Purpose | Address |
|---|---|---|---|
| PostgreSQL 17 with pgvector | Docker container | Stores documents, chunks, embeddings, and citations | `localhost:5433` from Windows |
| Ollama | Windows | Generates answers and supports graph query parsing | `http://127.0.0.1:11434` |
| Python / FastAPI backend | Windows virtual environment | Retrieval, model calls, API, and frontend serving | `http://127.0.0.1:8002` |
| SentenceTransformers embedding model | Backend Python process | Embeds corpus text and search queries | Downloads from Hugging Face on first use |
| Frontend | Browser; files served by FastAPI | Question form and evidence display | Same port, `8002` |

Request flow:

```text
Browser -> FastAPI -> embed question -> PostgreSQL retrieval
                  -> optional graph enrichment / Ollama
                  -> Ollama answer generation -> Browser
```

There is one required database for this setup: `clinivue`. pgvector is an extension inside PostgreSQL, not a separate server. Qdrant is not required for this app.

### What Git includes and excludes

The inspected checkout includes the built frontend, Docker Compose definition, database schema SQL, configuration, demo knowledge graph, and 32 parsed medical documents in `ingestion/medical_corpus/parsed`.

Git does **not** transfer the original developer's running containers, Docker database volume, Python virtual environments, passwords, downloaded Ollama models, or Hugging Face cache. Those must be recreated locally.

The root `pyproject.toml` is for separate image/model experiments. The web app uses `research-intelligence-system/pyproject.toml`. The ChEX checkpoint and BioMedCLIP experiments are not required here.

## 3. Conventions and prerequisites

Use **native Windows PowerShell** throughout. Do not mix these commands with WSL, Command Prompt, or Git Bash. Docker can use its WSL 2 backend while Python and Ollama run on Windows.

Replace `C:\path\to\clinivue` with your real clone path. Quote paths containing spaces. Run commands in order and stop at errors.

You need internet access for dependencies, the Docker image, and model downloads. Allow several GB of disk space for these plus the database. CPU execution is supported by the embedding provider; indexing and generation can be slow without suitable acceleration. No manual CUDA setup is required by this guide.

### Install Docker Desktop

Use the official Windows installation instructions:

https://docs.docker.com/desktop/setup/install/windows-install/

Use the WSL 2 backend and complete any Windows feature, virtualization, or restart steps requested by the installer. Open Docker Desktop and wait until its engine is running. Use Linux containers for the PostgreSQL image.

### Install Ollama

Download and install Ollama for Windows:

https://ollama.com/download/windows

Open Ollama so its local server is available.

### Install uv

Official instructions:

https://docs.astral.sh/uv/getting-started/installation/

The official PowerShell installer command is:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Open a new PowerShell window after installation so PATH changes take effect.

### Verify installations

```powershell
git --version
docker info
docker compose version
uv --version
ollama --version
```

Expected: each command runs, and `docker info` can reach the server. If Docker reports a daemon/engine connection error, fix Docker Desktop before continuing.

## 4. Open the repository and choose a database password

```powershell
cd "C:\path\to\clinivue"
git pull
Get-Location
Test-Path .\docker-compose.yml
Test-Path .\clarivue_qa\dist\index.html
Test-Path .\research-intelligence-system\pyproject.toml
```

All three `Test-Path` results should be `True`. If Git reports local changes or conflicts, inspect them; do not discard them blindly.

Set a password of your choosing in this PowerShell session:

```powershell
$env:POSTGRES_PASSWORD = 'replace-with-your-own-local-password'
$env:PGPASSWORD = $env:POSTGRES_PASSWORD
```

Use the same chosen password on future runs. Single-quoted PowerShell strings keep characters such as `$` literal; a literal single quote inside the password must be doubled.

| Variable | Used by | Meaning |
|---|---|---|
| `POSTGRES_PASSWORD` | Docker Compose / PostgreSQL image | Sets the database password when the data volume is first initialized |
| `PGPASSWORD` | Python PostgreSQL client | Supplies the password when the app or indexer connects |

These variables are local to this terminal session. A new terminal does not inherit variables set in an already-open terminal.

Do not copy a password from `run_app.sh`. That script contains a developer-specific fallback and is not the Windows setup entry point.

## 5. Start and initialize PostgreSQL

From the repository root:

```powershell
docker compose up -d
docker compose ps
docker exec clinivue-postgres pg_isready -U clinivue -d clinivue
```

Repeat the readiness command after a short wait if startup is still in progress. Expected: `accepting connections`.

The checked-in Compose configuration uses:

| Setting | Value |
|---|---|
| Image | `pgvector/pgvector:0.8.6-pg17-bookworm` |
| Container | `clinivue-postgres` |
| Database | `clinivue` |
| User | `clinivue` |
| Host binding | `127.0.0.1:5433` |
| PostgreSQL port inside container | `5432` |
| Compose volume key | `clinivue_postgres_data` |

Compose may prefix the actual volume name with the project name. The volume persists across container stops and ordinary `docker compose down`.

Enable pgvector **before** running Python indexing:

```powershell
docker exec clinivue-postgres psql -U clinivue -d clinivue -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

Expected: `CREATE EXTENSION`, or a notice that it already exists.

This order is important: `DatabaseManager.get_connection()` registers the vector type as soon as Python connects. On a fresh database, that can fail before the indexer's schema creation gets a chance to enable the extension.

No separate Windows PostgreSQL installation is needed.

## 6. Create the backend Python environment

From the repository root:

```powershell
uv python install 3.13
cd .\research-intelligence-system
uv sync --python 3.13 --extra ingestion --extra graph
```

This creates `research-intelligence-system\.venv`. `ingestion` installs PDF ingestion support; `graph` installs graph support needed by the enabled demo graph.

Verify:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -c "import fastapi, uvicorn, psycopg, pgvector, sentence_transformers, networkx, ingest; print('Backend imports OK')"
```

Using the explicit executable avoids virtual-environment activation and PowerShell activation-policy issues. Do not use `.venv/bin/python`: that is the Unix path.

If `uv sync` fails, preserve the full error. A missing package version, unavailable Windows wheel, network error, and unsupported Python version are different problems. Do not silently remove dependencies or regenerate the lockfile to hide the failure.

## 7. Configure Ollama and a local app configuration

The committed configuration selects `qwen3:4b-docmind`. No definition for that custom model was found in the inspected repo. A clone will not create it in Ollama.

For an initial working setup, use the public `qwen3:4b` model:

```powershell
ollama pull qwen3:4b
ollama list
Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

Official model page: https://ollama.com/library/qwen3%3A4b

Expected: the model appears in the list and the HTTP request succeeds. If the server is unavailable, open Ollama. Alternatively, run `ollama serve` in a second PowerShell window and leave it running. If that says the address is already in use, another server may already be running; check `/api/tags` before starting more processes.

Create a local config copy from inside `research-intelligence-system`:

```powershell
Copy-Item .\ingestion\clinivue_config.yaml .\ingestion\clinivue_config.windows.yaml
notepad .\ingestion\clinivue_config.windows.yaml
```

Only do the copy when initially creating the local config; repeating it overwrites your local changes.

Change this line and save:

```yaml
llm_model: qwen3:4b
```

Keep all other fields from the original file, including:

```yaml
database_url: postgresql://clinivue@localhost:5433/clinivue
embedding_model: BAAI/bge-base-en-v1.5
embedding_dimensions: 768
```

Do not replace the entire YAML file with this excerpt. `IndexerConfig` requires the other fields too. Do not put the password into the YAML; use `PGPASSWORD`.

The embedding model is separate from Ollama's answer model. SentenceTransformers downloads `BAAI/bge-base-en-v1.5` from Hugging Face when needed. Do not substitute a different embedding model or dimension against an existing index without planning to regenerate its embeddings.

The public Qwen model may behave differently from the original developer's custom model. To reproduce the original exactly, obtain its Modelfile and any required custom weights from the developer. Renaming a public model to the custom name does not reproduce customization.

The `.windows.yaml` file is a local setup file created by these instructions, not an existing repository feature. Keep it out of unrelated commits.

## 8. Build the database index

The repository includes parsed medical documents, but the new Docker database does not contain their index yet.

Confirm the corpus from `research-intelligence-system`:

```powershell
(Get-ChildItem .\ingestion\medical_corpus\parsed\*.json).Count
```

The inspected commit includes 32 files. A later commit may contain a different number. A missing folder or zero files means you must obtain the corpus before continuing.

Confirm that this terminal still has the password without printing it:

```powershell
if ($env:PGPASSWORD) { 'Database password is set' } else { 'Set PGPASSWORD before continuing' }
```

Paste this entire block into PowerShell, including the opening `@'` and closing `'@` lines:

```powershell
@'
from indexer.config import IndexerConfig
from indexer.pipeline.indexer import CorpusIndexer

config = IndexerConfig.from_yaml("ingestion/clinivue_config.windows.yaml")
summary = CorpusIndexer(config=config).index_corpus("ingestion/medical_corpus")
print(summary.format_report())
raise SystemExit(1 if summary.failed else 0)
'@ | .\.venv\Scripts\python.exe -
```

This loads the correct medical configuration, initializes tables, reads parsed documents, creates chunks and embeddings, resolves citations, and writes the index to PostgreSQL. First use may download the embedding model. Allow indexing to finish; on CPU it may take time.

Expected on a clean database: all available documents are successfully indexed and `Failed: 0`. Subsequent runs can report documents skipped because they are already up to date.

We use the Python API because `indexer.cli.commands` currently hardcodes `indexer/config.yaml`, a different configuration. Do not assume that CLI accepts `--config` or honors `RIS_CONFIG`.

Verify stored data:

```powershell
docker exec clinivue-postgres psql -U clinivue -d clinivue -c "SELECT COUNT(*) AS documents FROM documents; SELECT COUNT(*) AS chunks FROM chunks; SELECT COUNT(*) AS embeddings FROM embeddings;"
```

All counts should be greater than zero. The clean inspected corpus should produce 32 documents; exact chunk/embedding counts are not specified here.

The included parsed JSON is sufficient for this step. You do not need to reparse the original PDFs or manually copy the original developer's database volume.

## 9. Start the web app

Remain inside `research-intelligence-system`, in the terminal containing `PGPASSWORD`:

```powershell
$env:RIS_CONFIG = (Resolve-Path .\ingestion\clinivue_config.windows.yaml).Path
$env:OLLAMA_HOST = 'http://127.0.0.1:11434'
$env:RIS_KNOWLEDGE_GRAPH = (Resolve-Path .\indexer\knowledge-infusion\demo_graph.json).Path

.\.venv\Scripts\python.exe -m uvicorn indexer.app:app --host 127.0.0.1 --port 8002
```

Leave this terminal running. Open:

- App: http://127.0.0.1:8002
- API documentation: http://127.0.0.1:8002/docs
- Process health: http://127.0.0.1:8002/health

The frontend files in `clarivue_qa/dist` are committed and served by FastAPI. No Node installation, npm build, hosted deployment, proxy process, or ChEX checkpoint is needed for this route.

The demo graph is unverified demonstration data used to enrich retrieval. It is not another database or a substitute for the indexed papers. To disable graph enrichment for troubleshooting, stop the server with Ctrl+C, set `$env:RIS_KNOWLEDGE_GRAPH = ''`, and restart it. Removing the variable entirely can restore the app's default demo graph.

### Verify the complete system

Submit this question in the browser:

> Which approaches to automated chest X-ray report generation are described in this corpus?

Expected: a generated answer with retrieved passages/source cards. The first request may be slower while models load.

Alternatively, use a second PowerShell terminal:

```powershell
$body = @{ question = 'Which approaches to automated chest X-ray report generation are described in this corpus?' } | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:8002/api/qa -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 600
```

`/health` only reports process liveness. It does not prove database authentication, schema readiness, indexed evidence, embedding downloads, or Ollama generation work. A successful QA request with returned sources is the end-to-end check.

## 10. Start it again on another day

Open Docker Desktop and Ollama. Open PowerShell and run:

```powershell
cd "C:\path\to\clinivue"
$env:POSTGRES_PASSWORD = 'the-password-you-originally-chose'
$env:PGPASSWORD = $env:POSTGRES_PASSWORD
docker compose up -d

cd .\research-intelligence-system
$env:RIS_CONFIG = (Resolve-Path .\ingestion\clinivue_config.windows.yaml).Path
$env:OLLAMA_HOST = 'http://127.0.0.1:11434'
$env:RIS_KNOWLEDGE_GRAPH = (Resolve-Path .\indexer\knowledge-infusion\demo_graph.json).Path

.\.venv\Scripts\python.exe -m uvicorn indexer.app:app --host 127.0.0.1 --port 8002
```

Open http://127.0.0.1:8002. You do not need to re-download models or rebuild an unchanged index each day. After dependency changes from a later pull, rerun the `uv sync` command from section 6.

### Stop it

Press Ctrl+C in the app terminal. To stop PostgreSQL while preserving its data:

```powershell
cd "C:\path\to\clinivue"
docker compose stop
```

Ordinary `docker compose down` also preserves the named volume. **`docker compose down -v` deletes the database volume and its indexed data.** It is not a routine troubleshooting step.

## 11. Environment variable reference

| Name | Value / role |
|---|---|
| `POSTGRES_PASSWORD` | Password used when initializing a new PostgreSQL volume |
| `PGPASSWORD` | Same password, used by the Python database client |
| `RIS_CONFIG` | Absolute path to `ingestion/clinivue_config.windows.yaml` |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` |
| `RIS_KNOWLEDGE_GRAPH` | Absolute demo graph path; empty string disables graph enrichment in `indexer.app` |
| `RIS_LLM_TIMEOUT` | Optional per-generation timeout in seconds; the app defaults to `300` |

For a slow model, stop the server, set `$env:RIS_LLM_TIMEOUT = '600'`, and restart. This changes the backend's per-call timeout, not a guarantee about total request duration.

The direct Uvicorn command supplies host and port explicitly, so `CLARIVUE_HOST` and `CLARIVUE_PORT` are not needed here. Those variables are used by other startup paths.

Docker Compose can read a root `.env` file for interpolation, but this Python app does not automatically load that file into its environment. An entry for `POSTGRES_PASSWORD` in `.env` does not automatically set `PGPASSWORD` in PowerShell. This guide uses explicit terminal variables to avoid that mismatch.

Changing `POSTGRES_PASSWORD` after a database volume has been initialized does **not** change the existing database user's password. Use the original password or perform an intentional password change; do not delete the volume merely because authentication failed.

## 12. Troubleshooting and diagnostics

### Common failures

| Symptom | What to check / do |
|---|---|
| `uv`, `ollama`, or `docker` is not recognized | Reopen PowerShell after installation; check PATH and installation success. |
| Docker daemon/engine connection error | Open Docker Desktop and resolve its WSL 2/virtualization requirements. |
| Docker image pull fails | Check the exact registry/network/tag error. Do not substitute a different PostgreSQL major version against an existing volume. |
| Container name already exists | Inspect `docker ps -a`; an existing `clinivue-postgres` container may belong to another setup. Do not delete it without checking its data. |
| Port 5433 is already allocated | Identify what owns the port. If choosing a different host port, change both Compose's host mapping and the local YAML database URL. |
| Database connection refused | Confirm container readiness and use host port 5433, not container port 5432. |
| Password authentication failed / no password supplied | Set `PGPASSWORD` in the terminal starting Python and use the original volume's password. |
| Vector type not found | Run the explicit `CREATE EXTENSION` command from section 5. |
| Relation/table does not exist | Finish indexing against the same database/config used by the app. |
| `No module named ...` | Use `research-intelligence-system\.venv\Scripts\python.exe`; rerun the correct `uv sync` command if needed. |
| Ollama model not found | Ensure `ollama list` contains `qwen3:4b` and the selected local YAML uses that exact model name. |
| Ollama connection refused | Open Ollama and check `/api/tags`; confirm the app's `OLLAMA_HOST`. |
| Hugging Face download error | Check internet access, proxy/certificate restrictions, and the exact download error. Retry once the underlying issue is resolved. |
| Frontend build not found | Confirm `clarivue_qa/dist/index.html` exists in the clone and that the sibling folder layout is intact. |
| Port 8002 already in use | Stop the previous app process or launch Uvicorn with `--port 8003` and open that port instead. |
| `/health` works but QA returns 502 | Inspect the API error and server terminal: services are initialized lazily, so health can succeed while dependencies fail. |
| No evidence returned | Check document/chunk/embedding counts, the selected config, and whether the question matches the medical corpus. |
| Request is slow or times out | Test Ollama independently, allow first model load/download to finish, and consider the timeout setting in section 11. |
| Graph dependency error | Install the `graph` extra; optionally disable the graph to isolate basic retrieval. |

### Collect diagnostics without printing passwords

Run these from the repository root:

```powershell
Get-Location
git rev-parse --short HEAD
git status --short
uv --version
docker compose version
docker compose ps
docker logs --tail 60 clinivue-postgres
docker exec clinivue-postgres pg_isready -U clinivue -d clinivue
ollama list
Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

Then:

```powershell
cd .\research-intelligence-system
.\.venv\Scripts\python.exe --version
Test-Path .\ingestion\clinivue_config.windows.yaml
(Get-ChildItem .\ingestion\medical_corpus\parsed\*.json).Count
if ($env:PGPASSWORD) { 'PGPASSWORD is set' } else { 'PGPASSWORD is missing' }
$env:RIS_CONFIG
$env:OLLAMA_HOST
$env:RIS_KNOWLEDGE_GRAPH
```

If the app is running, use another terminal for HTTP diagnostics. Inspect output before sharing it; remove passwords, tokens, and private paths as needed. Avoid dumping every environment variable or sharing `docker inspect` output indiscriminately, since those can expose credentials.

## 13. Completion checklist

- [ ] Docker Desktop is running and PostgreSQL accepts connections.
- [ ] The `vector` extension is enabled in `clinivue`.
- [ ] The backend Python environment imports its dependencies.
- [ ] Ollama lists the model named in the local YAML.
- [ ] The medical corpus indexes with zero failures.
- [ ] Documents, chunks, and embeddings have nonzero database counts.
- [ ] The browser opens the app on port 8002.
- [ ] A question returns an answer and retrieved sources.
- [ ] The next-day startup procedure works without rebuilding the database.

## 14. Repository references for further help

| File | Why it matters |
|---|---|
| `docker-compose.yml` | PostgreSQL image, credentials, port mapping, persistent storage |
| `research-intelligence-system/pyproject.toml` | Backend dependencies and extras |
| `research-intelligence-system/uv.lock` | Resolved dependency versions |
| `research-intelligence-system/ingestion/clinivue_config.yaml` | Original medical app configuration |
| `research-intelligence-system/indexer/config.py` | Required YAML fields |
| `research-intelligence-system/indexer/app.py` | FastAPI entry point, frontend serving, environment variables |
| `research-intelligence-system/indexer/database/connection.py` | Database connections and vector registration |
| `research-intelligence-system/indexer/database/migrations/init_schema.sql` | Tables, indexes, vector extension |
| `research-intelligence-system/indexer/pipeline/indexer.py` | Corpus indexing and schema initialization |
| `research-intelligence-system/indexer/cli/commands.py` | Existing CLI and its hardcoded config path |
| `research-intelligence-system/indexer/qa/ollama.py` | Ollama generation API client |
| `research-intelligence-system/indexer/embeddings/sentence_transformers.py` | Local embedding model loading |
| `research-intelligence-system/indexer/knowledge-infusion/demo_graph.json` | Included demonstration graph |
| `research-intelligence-system/WEB_APP.md` | Alternative historical startup paths; this guide uses direct FastAPI |
| `clarivue_qa/dist/index.html` | Committed frontend entry point |

For this guide, use **`indexer.app:app` on port 8002**. Other documentation describes a proxy/backend arrangement on additional ports; mixing the two startup arrangements is unnecessary.
