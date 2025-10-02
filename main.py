import logging 
from fastapi import FastAPI
import inngest.fast_api
from inngest.experimental import ai
from dotenv import load_dotenv
import uuid
import os
import datetime
from data_loader import load_and_chunk_pdf, embed_texts
from vector_db import QdrantStorage
from custom_types import RAGQueryResult, RAGSearchResult, RAGUpsertResult, RAGChunkAndSrc


load_dotenv()

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
        key="event.data.source_id",
    ),
)
async def rag_ingest_pdf(ctx: inngest.Context):
    def _load(ctx: inngest.Context) -> RAGChunkAndSrc:
        pdf_path = ctx.event.data["pdf_path"]
        source_id = ctx.event.data.get("source_id", pdf_path)

        # load_and_chunk_pdf should ideally also return page numbers
        chunks = load_and_chunk_pdf(pdf_path)

        # Attach page info (for now assume sequential pages for each chunk)
        chunk_with_page = [
            {"text": chunk, "page": i + 1} for i, chunk in enumerate(chunks)
        ]
        return RAGChunkAndSrc(chunks=chunk_with_page, source_id=source_id)

    def _upsert(chunks_and_src: RAGChunkAndSrc) -> RAGUpsertResult:
        source_id = chunks_and_src.source_id
        chunks = chunks_and_src.chunks

        texts = [c["text"] for c in chunks]
        vecs = embed_texts(texts)

        ids = [str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_id}:{i}")) for i in range(len(chunks))]
        payloads = [
            {"source": source_id, "text": chunks[i]["text"], "page": chunks[i]["page"]}
            for i in range(len(chunks))
        ]

        QdrantStorage().upsert(ids, vecs, payloads)
        return RAGUpsertResult(ingested=len(chunks))

    chunks_and_src = await ctx.step.run(
        "load-and-chunk", lambda: _load(ctx), output_type=RAGChunkAndSrc
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
    def _search(question: str, top_k: int = 5) -> dict:
        query_vec = embed_texts([question])[0]
        store = QdrantStorage()
        results = store.client.search(
            collection_name=store.collection,
            query_vector=query_vec,
            with_payload=True,
            limit=top_k
        )
        contexts, sources, scores = [], [], []
        for r in results:
            payload = getattr(r, "payload", {}) or {}
            text = payload.get("text", "")
            source = payload.get("source", "")
            page = payload.get("page", "?")
            if text:
                contexts.append(f"{text} [source: {source}, page {page}]")
                sources.append(f"{source}, page {page}")
                scores.append(r.score)
        return {
            "contexts": contexts,
            "sources": sources,
            "scores": scores
        }

    question = ctx.event.data["question"]
    top_k = int(ctx.event.data.get("top_k", 5))

    # Support chat reset
    history = ctx.event.data.get("history", [])
    if question.strip().lower() in ("reset", "clear", "new chat"):
        return {"answer": "🔄 Chat history cleared.", "sources": [], "num_contexts": 0, "history": []}

    result = await ctx.step.run(
        "embed-and-search", 
        lambda: _search(question, top_k)
    )
    
    contexts = result["contexts"]
    sources = result["sources"]
    scores = result["scores"]

    context_block = "\n\n".join(f"- {c}" for c in contexts)
    user_content = (
        "Use the following context to answer the question.\n\n"
        f"Context:\n{context_block}\n\n"
        f"Question: {question}\n"
        "Answer in detail using the context above. Cite sources inline when relevant."
    )

    adapter = ai.openai.Adapter(
        auth_key=os.getenv("DEEPSEEK_API_KEY"),
        model="deepseek-chat",
        base_url="https://api.deepseek.com/v1"
    )

    messages = [{"role": "system", "content": "You answer using only the provided context."}]
    messages.extend(history)
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
    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": answer})

    # Compute analytics
    avg_conf = round(sum(scores)/len(scores), 3) if scores else 0.0

    return RAGQueryResult(
        answer=answer,
        sources=sources,
        num_contexts=len(contexts)
    ).model_dump() | {
        "history": history,
        "avg_confidence": avg_conf
    }


app = FastAPI()

inngest.fast_api.serve(app, inngest_client, [rag_ingest_pdf, rag_query_pdf_ai])