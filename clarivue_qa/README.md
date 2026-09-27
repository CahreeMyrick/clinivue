# Clarivue QA

The UI now sends every submitted question to the research backend. The backend
retrieves indexed passages, optionally enriches retrieval with a supplied graph,
and generates a cited answer using Ollama. Source cards are built from the actual
response, including document and chunk identifiers.

From this checkout, start the complete local app:

```sh
cd ../research-intelligence-system
.venv/bin/python -m indexer.web_app
```

Open http://127.0.0.1:8002. To use the existing unverified demonstration graph:

```sh
.venv/bin/python -m indexer.web_app --knowledge-graph indexer/knowledge-infusion/demo_graph.json
```

See [the integration guide](../research-intelligence-system/WEB_APP.md) for
requirements, port overrides, graph configuration, and regression checks.

The hosted Worker uses the same response contract and forwards questions to the
HTTPS endpoint configured in `CLARIVUE_RAG_URL`, with optional server-side
`CLARIVUE_RAG_TOKEN`. It cannot reach a backend running on your laptop's localhost.
No remote endpoint means an explicit configuration error; there is no canned
answer fallback. Hosted code changes must be published separately.

Examples fill the question box; submitting them runs the real pipeline. Citation
buttons open their returned passages. Changing view modes preserves the evidence.
Resetting or selecting another example cancels the current browser request and
prevents late results from replacing the new question.
