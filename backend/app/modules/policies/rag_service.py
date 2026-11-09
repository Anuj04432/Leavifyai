import math
import re
from typing import Any, Dict, List, Optional
import uuid
import httpx
import numpy as np
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.knowledge import KnowledgeChunk

settings = get_settings()


class HybridOKFRAGService:
    """Hybrid Open Knowledge Format (OKF) & Retrieval-Augmented Generation (RAG) Service.

    Combines deterministic OKF policy rules with deep semantic search across multi-page
    company handbooks and documents using dedicated OpenRouter embeddings and resilient
    vector ranking.
    """

    def __init__(self):
        self.embedding_api_key = (
            settings.OPENROUTER_EMBEDDING_API_KEY or settings.OPENROUTER_API_KEY or ""
        ).strip()
        self.embedding_base_url = (
            settings.OPENROUTER_EMBEDDING_BASE_URL
            or settings.OPENROUTER_BASE_URL
            or "https://openrouter.ai/api/v1"
        ).rstrip("/")
        self.embedding_model = settings.OPENROUTER_EMBEDDING_MODEL or "text-embedding-3-small"

    def _is_valid_key(self, key: str) -> bool:
        if not key:
            return False
        clean = key.strip().lower()
        return bool(clean) and not clean.startswith("your-") and not clean.startswith("sk-placeholder")

    async def get_embedding(self, text: str) -> List[float]:
        """Generates embedding vector via OpenRouter embedding endpoint or falls back to local vectorizer."""
        clean_text = text.strip()[:4000]
        if not clean_text:
            return [0.0] * 64

        # 1. Use dedicated OpenRouter Embeddings API if configured
        if self._is_valid_key(self.embedding_api_key):
            try:
                url = f"{self.embedding_base_url}/embeddings"
                headers = {
                    "Authorization": f"Bearer {self.embedding_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://workforceai.io",
                    "X-Title": "WorkforceAI-RAG",
                }
                payload = {
                    "model": self.embedding_model,
                    "input": clean_text,
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        if "data" in data and len(data["data"]) > 0:
                            emb = data["data"][0].get("embedding", [])
                            if emb:
                                return emb
            except Exception:
                pass  # Fall back to resilient local vectorizer

        # 2. Resilient deterministic vectorizer fallback (hashed character-ngram TF-IDF dense vector)
        return self._local_vectorize(clean_text)

    def _local_vectorize(self, text: str, dim: int = 128) -> List[float]:
        """Lightweight high-speed semantic dense vector representation using deterministic crc32 hashing."""
        import zlib
        vec = np.zeros(dim, dtype=np.float32)
        words = re.findall(r"\b\w{3,}\b", text.lower())
        if not words:
            return vec.tolist()

        for w in words:
            h = zlib.crc32(w.encode("utf-8")) % dim
            vec[h] += 1.0

        # Also hash bigrams for sequence awareness
        for i in range(len(words) - 1):
            bigram = f"{words[i]}_{words[i+1]}"
            h2 = zlib.crc32(bigram.encode("utf-8")) % dim
            vec[h2] += 1.5

        # L2 Normalize
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def chunk_markdown(
        self,
        markdown_text: str,
        chunk_size: int = 700,
        chunk_overlap: int = 100,
    ) -> List[Dict[str, Any]]:
        """Splits multi-page Markdown documents into section-aware semantic chunks."""
        lines = markdown_text.strip().splitlines()
        chunks = []
        current_section = "General Overview"
        current_buffer = []
        current_len = 0

        header_re = re.compile(r"^(#{1,4})\s+(.+)$")

        for line in lines:
            h_match = header_re.match(line)
            if h_match:
                # Flush previous buffer if it has content
                if current_buffer and current_len > 100:
                    text_chunk = "\n".join(current_buffer).strip()
                    chunks.append({
                        "section_header": current_section,
                        "content": text_chunk,
                    })
                    # Keep overlap from the end of the previous buffer
                    overlap_lines = current_buffer[-2:] if len(current_buffer) >= 2 else []
                    current_buffer = list(overlap_lines)
                    current_len = sum(len(l) for l in current_buffer)

                current_section = h_match.group(2).strip()

            current_buffer.append(line)
            current_len += len(line)

            if current_len >= chunk_size:
                text_chunk = "\n".join(current_buffer).strip()
                chunks.append({
                    "section_header": current_section,
                    "content": text_chunk,
                })
                # Retain overlap lines for context continuity
                overlap_lines = current_buffer[-3:] if len(current_buffer) >= 3 else []
                current_buffer = list(overlap_lines)
                current_len = sum(len(l) for l in current_buffer)

        # Flush final remaining buffer
        if current_buffer:
            final_text = "\n".join(current_buffer).strip()
            if final_text and (not chunks or final_text != chunks[-1]["content"]):
                chunks.append({
                    "section_header": current_section,
                    "content": final_text,
                })

        return chunks

    async def index_document(
        self,
        db: AsyncSession,
        company_id: uuid.UUID,
        policy_code: str,
        document_title: str,
        markdown_content: str,
        meta_info: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Chunks, embeds, and stores semantic knowledge segments in database."""
        # 1. Purge older chunks for this document code within this company
        clean_code = (policy_code or "POL-GEN").upper().strip()
        await db.execute(
            delete(KnowledgeChunk).where(
                KnowledgeChunk.company_id == company_id,
                KnowledgeChunk.policy_code == clean_code,
            )
        )

        # 2. Section-aware chunking
        raw_chunks = self.chunk_markdown(markdown_content)
        if not raw_chunks:
            raw_chunks = [{
                "section_header": "Overview",
                "content": markdown_content.strip()[:1000],
            }]

        # 3. Embed and persist
        created_count = 0
        for idx, item in enumerate(raw_chunks):
            emb = await self.get_embedding(item["content"])
            chunk_rec = KnowledgeChunk(
                company_id=company_id,
                policy_code=clean_code,
                document_title=document_title.strip(),
                section_header=item["section_header"],
                chunk_index=idx,
                content=item["content"],
                meta_info=meta_info or {},
                embedding=emb,
            )
            db.add(chunk_rec)
            created_count += 1

        await db.commit()
        return created_count

    async def search_knowledge(
        self,
        db: AsyncSession,
        company_id: uuid.UUID,
        query: str,
        top_k: int = 4,
    ) -> List[Dict[str, Any]]:
        """Performs semantic vector similarity search across all company documents."""
        clean_query = query.strip()
        if not clean_query:
            return []

        # 1. Embed query
        query_vec = np.array(await self.get_embedding(clean_query), dtype=np.float32)
        q_norm = np.linalg.norm(query_vec)
        if q_norm > 0:
            query_vec = query_vec / q_norm

        # 2. Fetch all chunks for company
        stmt = select(KnowledgeChunk).where(KnowledgeChunk.company_id == company_id)
        result = await db.execute(stmt)
        chunks = result.scalars().all()

        if not chunks:
            return []

        # 3. Calculate cosine similarity and keyword boosts
        query_lower = clean_query.lower()
        scored_chunks = []

        for ch in chunks:
            if not ch.embedding:
                continue

            c_vec = np.array(ch.embedding, dtype=np.float32)
            c_norm = np.linalg.norm(c_vec)
            if c_norm > 0:
                c_vec = c_vec / c_norm

            # Match dimension if models differ
            if c_vec.shape == query_vec.shape:
                score = float(np.dot(query_vec, c_vec))
            else:
                score = 0.2

            # Boost if query mentions policy code or section title
            if ch.policy_code and ch.policy_code.lower() in query_lower:
                score += 0.35
            if ch.section_header and any(w in ch.section_header.lower() for w in query_lower.split() if len(w) > 3):
                score += 0.20
            if ch.document_title and any(w in ch.document_title.lower() for w in query_lower.split() if len(w) > 3):
                score += 0.15

            scored_chunks.append({
                "id": str(ch.id),
                "policy_code": ch.policy_code,
                "document_title": ch.document_title,
                "section_header": ch.section_header,
                "content": ch.content,
                "score": round(score, 4),
            })

        # 4. Sort by relevance score descending
        scored_chunks.sort(key=lambda x: x["score"], reverse=True)
        return scored_chunks[:top_k]

    def format_rag_grounding_context(self, chunks: List[Dict[str, Any]]) -> str:
        """Formats retrieved chunks into clean grounding reference text for the LLM."""
        if not chunks:
            return ""

        lines = ["=== RELEVANT OFFICIAL COMPANY POLICY & HANDBOOK EXCERPTS ==="]
        for idx, c in enumerate(chunks, 1):
            sec = f" > {c['section_header']}" if c.get("section_header") else ""
            lines.append(
                f"\n[Source {idx}: {c['document_title']}{sec} (Code: {c.get('policy_code', 'GEN')})]"
            )
            # Clip chunk to 500 chars to save prompt tokens
            lines.append(c["content"][:650].strip())

        lines.append("============================================================")
        return "\n".join(lines)


rag_service = HybridOKFRAGService()
