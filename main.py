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
    """Ingest a PDF document into the RAG system.
    
    M2 Refactored:
    - Uses chunk_service to save to chunks collection
    - References document_id instead of duplicating scope info
    - Updates Document status to 'ready' after completion
    """
    # Validate event data with Pydantic
    event_data = IngestPdfEventData(**ctx.event.data)
    document_id = event_data.document_id
    
    def _load() -> RAGChunkAndSrc:
        import file_storage
        import os
        from chunk_service import update_document_status
        from models import DocumentStatus
        
        # Download PDF from S3 to temp file
        temp_path = file_storage.download_to_temp(event_data.pdf_path)
        
        try:
            # load_and_chunk_pdf extracts text chunks
            chunks = load_and_chunk_pdf(temp_path)
            
            # Validate we got content
            if not chunks:
                raise ValueError("PDF appears to be empty or unreadable")

            # Attach page info (for now assume sequential pages for each chunk)
            chunk_with_page = [
                ChunkWithPage(text=chunk, page=i + 1) for i, chunk in enumerate(chunks)
            ]
            return RAGChunkAndSrc(chunks=chunk_with_page, source_id=event_data.filename)
        except Exception as e:
            # Log error and leave status as pending for retry
            # In production, could set status to 'error' after max retries
            print(f"PDF parsing error for {event_data.filename}: {e}")
            raise
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def _embed_and_save(chunks_and_src: RAGChunkAndSrc) -> RAGUpsertResult:
        """Embed chunks and save to chunks collection using chunk_service."""
        from chunk_service import save_chunks, update_document_status
        from models import DocumentStatus
        
        chunks = chunks_and_src.chunks
        
        # Get text for embedding
        texts = [c.text for c in chunks]
        embeddings = embed_texts(texts)
        
        # Prepare chunk data for chunk_service
        chunks_data = [
            {
                "text": chunks[i].text,
                "page_number": chunks[i].page,
                "chunk_index": i
            }
            for i in range(len(chunks))
        ]
        
        # Save chunks to chunks collection
        saved_count = save_chunks(document_id, chunks_data, embeddings)
        
        # Update document status to ready
        update_document_status(document_id, DocumentStatus.READY)
        
        return RAGUpsertResult(ingested=saved_count)

    chunks_and_src = await ctx.step.run(
        "load-and-chunk", _load, output_type=RAGChunkAndSrc
    )
    ingested = await ctx.step.run(
        "embed-and-save", lambda: _embed_and_save(chunks_and_src), output_type=RAGUpsertResult
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
        from chunk_search import search_for_scope
        
        query_vec = embed_texts([event_data.question])[0]
        
        # Use new chunk_search service (M2)
        result = search_for_scope(
            query_vec, 
            scope_type=event_data.scope_type.value,
            scope_id=event_data.scope_id,
            top_k=event_data.top_k
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
from document_routes import router as document_router
app.include_router(api_router)
app.include_router(auth_router)
app.include_router(document_router)

# Inngest integration
inngest.fast_api.serve(app, inngest_client, [rag_ingest_pdf, rag_query_pdf_ai])