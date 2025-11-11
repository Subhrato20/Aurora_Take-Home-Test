# Aurora QA

Question-answering microservice built for the Aurora take-home. The FastAPI app downloads concierge messages from the public November7 API, indexes them with TF–IDF, and answers natural-language prompts via a simple `/ask` endpoint.

## Local development

1. Create a virtual environment and install the dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Start the API:
   ```bash
   uvicorn app.main:app --reload
   ```
3. Ask a question:
   ```bash
   curl -s -X POST \
     -H "Content-Type: application/json" \
     -d '{"question": "When is Layla planning her trip to London?"}' \
     http://127.0.0.1:8000/ask
   ```
   Response format:
   ```json
   { "answer": "Layla Kawaguchi mentioned on 2025-08-29: We need a suite for five nights at Claridge's in London starting Monday." }
   ```

### Configuration

All settings can be tweaked with environment variables (see `app/config.py`):

- `AURORA_QA_MESSAGE_API_BASE_URL` — override the upstream API location.
- `AURORA_QA_MESSAGE_PAGE_SIZE` — change pagination batch size if the API changes its limits.
- `AURORA_QA_MIN_SIMILARITY` — raise/lower the similarity threshold before the system admits defeat.

Create a `.env` file or export the variables before launching `uvicorn`.

## Deployment

A Dockerfile is included for quick deployments to any container-friendly host (Render, Fly.io, Google Cloud Run, etc.). Example workflow:

```bash
docker build -t aurora-qa:latest .
docker run -it --rm -p 8080:8080 aurora-qa:latest
```

When deploying to a managed service, point traffic to `/ask` on port `8080` and ensure the container can reach `https://november7-730026606190.europe-west1.run.app`.

## API surface

`POST /ask`
- Request body: `{ "question": "natural-language text" }`
- Response body: `{ "answer": "string" }`
- If the system cannot find a confident match, it replies with `"I could not find that information in the member messages."`

## Design notes (Bonus #1)

1. **Current approach – lexical TF–IDF retrieval.** Simple, deterministic, inexpensive, and deployable anywhere. Filtering by detected member names keeps the search space small and boosts precision.
2. **Embedding-based semantic search.** A next step would be to compute sentence embeddings (e.g., with Instructor or MiniLM) and serve them from a vector store such as Qdrant. This would better capture paraphrases but requires GPU/a heavier dependency stack and an embedding refresh workflow.
3. **Structured profile extraction.** Another option is to pre-process messages into per-member fact tables (preferences, assets, upcoming trips) and answer questions by querying those structured records. That path provides crisp answers for known schema fields but requires building/maintaining robust NLP extraction pipelines.

## Data insights (Bonus #2)

- **Only 10 members generate all 3,349 messages.** The dataset is extremely imbalanced (top talkers such as Lily O'Sullivan and Thiago Monteiro each exceed 350 messages), so recall for long-tail members is not testable.
- **Duplicate passport numbers across different people.** Layla Kawaguchi and Lily O'Sullivan both share `123456789`, while Sophia Al-Farsi and Vikram Desai share `987654321`. This suggests either synthetic data leakage or identity collisions.
- **PII is scattered through free text.** Numerous entries include passport numbers, credit-card details (“update my account with card ending 9012”), and visa data. Any production pipeline should scrub or tokenize these before ingesting them into a search index.
- **Requests are future-dated through late 2025.** Many timestamps (e.g., Santorini villa requests in December 2025) sit well beyond "today," so consumers should not assume the corpus only reflects historical events.

## Next steps

- Add automated tests around the message loader and ranking heuristics.
- Persist the downloaded corpus locally (or memoize in Redis) to avoid hitting the upstream API on every cold start.
- Add tracing/metrics so we can monitor unanswered queries and tune the similarity threshold.
