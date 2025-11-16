**Demo Video** -- https://youtube.com/shorts/XHDzgOzeqvI?feature=share

# November Q&A Service

FastAPI application that answers natural-language questions by paging through the November `/messages` API, filtering likely candidates, and asking an OpenAI validator loop to confirm the answer. The service exposes `POST /ask` with body `{"question": "..."}` and responds with the answer plus the supporting message.

## Approach

This implementation uses a **hybrid heuristic + LLM validation approach** that balances efficiency, accuracy, and cost-effectiveness. Here's how it works:

### Architecture Overview

The system consists of:
- **Backend**: FastAPI service with modular components for parsing, fetching, caching, and validation
- **Frontend**: React-based chat interface with a modern UI for interacting with the Q&A service
- **Caching**: Local JSON-based cache to persist messages between runs and reduce API calls

### Processing Pipeline

1. **Question Parsing** (`parser.py`)
   - Extracts member names using regex patterns (capitalized words)
   - Identifies relevant keywords by filtering out stop words and short tokens
   - Uses heuristics to distinguish person names from location names (e.g., "to Paris" vs "Layla")

2. **Message Retrieval** (`fetcher.py` + `cache.py`)
   - First checks local cache for previously fetched messages
   - Pages through November API starting from the first uncached message
   - Implements rate limiting (5-second delay between pages) to respect API constraints
   - Persists all fetched messages to local JSON cache for subsequent queries

3. **Name Resolution** (`validators.py` - `LLMNameResolver`)
   - For each page, extracts all unique user names
   - Uses OpenAI function calling to intelligently match question context to member names
   - Handles variations and implicit references (e.g., "her" referring to a previously mentioned person)
   - Falls back to heuristic matching if LLM resolution fails

4. **Candidate Filtering** (`qa_service.py`)
   - Filters messages by resolved member names (if any)
   - Filters by keyword presence in message text
   - Only processes messages that match both name and keyword criteria
   - Reduces the number of messages sent to the expensive LLM validator

5. **LLM Validation** (`validators.py` - `LLMValidator`)
   - Sends filtered candidates to OpenAI with structured prompts
   - Uses function calling to enforce structured output (answer text + source index)
   - Validates that answers are grounded in actual message content
   - Returns "NO_ANSWER" if no candidate contains a valid answer

6. **Answer Selection** (`qa_service.py`)
   - Scores candidates by keyword match count and message recency
   - Tracks the best answer found across all pages
   - Short-circuits early if a high-confidence answer is found
   - Returns the best answer with its source message, or a fallback if none found

### Key Design Decisions

- **Hybrid Filtering**: Heuristic pre-filtering reduces LLM token usage while LLM validation ensures accuracy
- **Progressive Search**: Searches cached messages first, then fetches new ones incrementally
- **Early Termination**: Can return answers as soon as a valid one is found, without scanning all pages
- **Graceful Degradation**: Falls back to heuristic name matching if LLM name resolution fails
- **Local Caching**: Reduces API calls and improves response time for repeated queries
- **Error Handling**: Continues processing even if individual pages fail, returning best answer found so far

### Frontend Features

- Modern chat interface with message history
- Real-time loading states and error handling
- Responsive design with gradient backgrounds
- User-friendly prompt input with send functionality

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
