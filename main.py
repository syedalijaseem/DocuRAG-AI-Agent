import logging 
from fastapi import FastAPI
import inngest.fast_api
from inngest.experimental import ai
from dotenv import load_dotenv
import uuid
import os
import datetime
from data_loader import load_and_chunk_pdf, embed_texts
from vector_db import MongoDBStorage
from models import (
    IngestPdfEventData,
    QueryPdfEventData,
    RAGChunkAndSrc,
    RAGUpsertResult,
    SearchResult,
    QueryResult,
    ChunkWithPage,
)

load_dotenv()

# Validate required environment variables at startup
def _validate_env():
    required = ["MONGODB_URI"]
    missing = [var for var in required if not os.getenv(var)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

_validate_env()

inngest_client = inngest.Inngest(
    app_id="rag-app",
    logger=logging.getLogger("uvicorn"),
    is_production=False,
    serializer=inngest.PydanticSerializer()
)

@inngest_client.create_function(
    fn_id="RAG: Ingest PDF",
    trigger=inngest.TriggerEvent(event="rag/ingest_pdf"),
    throttle=inngest.Throttle(
        limit=1, count=2, period=datetime.timedelta(minutes=1)
    ),
    rate_limit=inngest.RateLimit(
        limit=1,
        period=datetime.timedelta(hours=4),
        key="event.data.pdf_path",
    ),
)
async def rag_ingest_pdf(ctx: inngest.Context):
    # Validate event data with Pydantic
    event_data = IngestPdfEventData(**ctx.event.data)
    
    def _load() -> RAGChunkAndSrc:
        import file_storage
        import os
        
        # Download PDF from S3 to temp file
        temp_path = file_storage.download_to_temp(event_data.pdf_path)
        
        try:
            # load_and_chunk_pdf should ideally also return page numbers
            chunks = load_and_chunk_pdf(temp_path)

            # Attach page info (for now assume sequential pages for each chunk)
            chunk_with_page = [
                ChunkWithPage(text=chunk, page=i + 1) for i, chunk in enumerate(chunks)
            ]
            return RAGChunkAndSrc(chunks=chunk_with_page, source_id=event_data.filename)
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def _upsert(chunks_and_src: RAGChunkAndSrc) -> RAGUpsertResult:
        source_id = chunks_and_src.source_id
        chunks = chunks_and_src.chunks

        texts = [c.text for c in chunks]
        vecs = embed_texts(texts)

        ids = [str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_id}:{i}")) for i in range(len(chunks))]
        payloads = [
            {"source": source_id, "text": chunks[i].text, "page": chunks[i].page}
            for i in range(len(chunks))
        ]

        MongoDBStorage().upsert(
            ids, vecs, payloads, 
            scope_type=event_data.scope_type,
            scope_id=event_data.scope_id
        )
        return RAGUpsertResult(ingested=len(chunks))

    chunks_and_src = await ctx.step.run(
        "load-and-chunk", _load, output_type=RAGChunkAndSrc
    )
    ingested = await ctx.step.run(
        "embed-and-upsert", lambda: _upsert(chunks_and_src), output_type=RAGUpsertResult
    )
    return ingested.model_dump()

@inngest_client.create_function(
    fn_id="RAG: Query PDF",
    trigger=inngest.TriggerEvent(event="rag/query_pdf_ai")
)
async def rag_query_pdf_ai(ctx: inngest.Context):
    # Validate event data with Pydantic
    event_data = QueryPdfEventData(**ctx.event.data)
    
    def _search() -> SearchResult:
        query_vec = embed_texts([event_data.question])[0]
        store = MongoDBStorage()
        # Use pre-filtering by scope for isolated lookup
        result = store.search(
            query_vec, 
            top_k=event_data.top_k, 
            scope_type=event_data.scope_type,
            scope_id=event_data.scope_id
        )
        
        contexts = []
        for i, text in enumerate(result["contexts"]):
            source = result["sources"][i] if i < len(result["sources"]) else ""
            contexts.append(f"{text} [source: {source}]")
        
        return SearchResult(
            contexts=contexts,
            sources=result["sources"],
            scores=result.get("scores", [])
        )

    # Support chat reset
    if event_data.question.lower() in ("reset", "clear", "new chat"):
        return QueryResult(
            answer="🔄 Chat history cleared.",
            sources=[],
            num_contexts=0,
            history=[]
        ).model_dump()

    result = await ctx.step.run(
        "embed-and-search", 
        _search,
        output_type=SearchResult
    )
    
    contexts = result.contexts
    sources = result.sources
    scores = result.scores

    context_block = "\n\n".join(f"- {c}" for c in contexts)
    user_content = (
        "Use the following context to answer the question.\n\n"
        f"Context:\n{context_block}\n\n"
        f"Question: {event_data.question}\n"
        "Answer in detail using the context above. Cite sources inline when relevant."
    )

    adapter = ai.openai.Adapter(
        auth_key=os.getenv("DEEPSEEK_API_KEY"),
        model="deepseek-chat",
        base_url="https://api.deepseek.com/v1"
    )

    messages = [{"role": "system", "content": "You answer using only the provided context."}]
    messages.extend(event_data.history)
    messages.append({"role": "user", "content": user_content})

    res = await ctx.step.ai.infer(
        "llm-answer",
        adapter=adapter,
        body={
            "max_tokens": 2056,
            "temperature": 0.2,
            "messages": messages
        }
    )

    answer = res["choices"][0]["message"]["content"].strip()

    # Update history
    history = list(event_data.history)
    history.append({"role": "user", "content": event_data.question})
    history.append({"role": "assistant", "content": answer})

    # Compute analytics
    avg_conf = round(sum(scores)/len(scores), 3) if scores else 0.0

    return QueryResult(
        answer=answer,
        sources=sources,
        num_contexts=len(contexts),
        history=history,
        avg_confidence=avg_conf
    ).model_dump()


app = FastAPI(title="DocuRAG API")

# CORS for React frontend (allow all origins in dev)
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include API routes
from api_routes import router as api_router
from auth_routes import router as auth_router
app.include_router(api_router)
app.include_router(auth_router)

# Inngest integration
inngest.fast_api.serve(app, inngest_client, [rag_ingest_pdf, rag_query_pdf_ai])