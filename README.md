# November Q&A Service

FastAPI application that answers natural-language questions by paging through the November `/messages` API, filtering likely candidates, and asking an OpenAI validator loop to confirm the answer. The service exposes `POST /ask` with body `{"question": "..."}` and responds with the answer plus the supporting message.

## Running Locally

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...
PYTHONPATH=src uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

## Alternative Approaches Considered

1. **Vector database indexing**  
   Periodically ingest all `/messages` data into a vector store (e.g., Pinecone, Qdrant) and run semantic search to retrieve the top-K messages per question before sending them to the validator. This would avoid repeated full pagination but requires a separate ingestion job, storage costs, and index freshness management.

2. **LLM-first multi-hop retrieval**  
   Use the LLM to propose search directives (e.g., “find Layla’s future trips”) and call the API with query parameters or keyword filters multiple times instead of scanning every page. This reduces network usage but depends on the remote API supporting richer server-side filtering and adds complexity in constructing and validating LLM-generated queries.

3. **Rule-based answer extraction**  
   Build deterministic regex/keyword pipelines per question type (“When is…”, “How many cars…”) that parse candidate messages directly without an LLM validator. This would be cheaper and deterministic but brittle—adding new question styles would require manual rules, and nuanced language would be missed.

4. **Streaming plus summarization**  
   Stream messages page by page into a summarization buffer (e.g., running window of 500 messages) and let the LLM maintain state about possible answers. This keeps token usage bounded but introduces complex prompt engineering and state management, and still suffers when the API rate-limits deep pagination.

Given time constraints and the need for precise answers grounded in actual messages, the current hybrid—heuristic pre-filtering plus an LLM validator loop that short-circuits when a valid answer is confirmed—offered the best balance of reliability, cost, and implementation speed.
