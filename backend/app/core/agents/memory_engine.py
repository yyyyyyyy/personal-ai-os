"""Memory Engine — extracts, stores, and retrieves user memories.

Memories are NOT raw data. They are refined insights from Events and conversations.
All writes to the `memories` projection go through the Kernel (MemoryDerived/Updated/Deleted).
ChromaDB is a derived search index maintained by the Kernel after projection.
"""

import uuid

from app.core.runtime.claim_authority import can_present
from app.core.runtime.kernel_instance import kernel


class MemoryEngine:
    """Manages the complete lifecycle of user memories."""

    def store_memory(
        self,
        content: str,
        category: str = "fact",
        source: str | None = None,
        actor: str = "user",
        confidence: float = 0.5,
    ) -> str:
        """Store a memory via Kernel event; Chroma index syncs in Kernel Space."""
        memory_id = str(uuid.uuid4())

        kernel.emit_event(
            type="MemoryDerived",
            aggregate_type="memory",
            aggregate_id=memory_id,
            payload={
                "category": category,
                "content": content,
                "source": source or "",
                "confidence": confidence,
            },
            actor=actor,
        )
        return memory_id

    def search_relevant_memories(self, query: str, n_results: int = 5) -> list[dict]:
        """Semantic search for memories relevant to the current context."""
        return kernel.recall_memory(query, k=n_results)

    def _enrich_recall_hits(self, hits: list[dict]) -> list[dict]:
        """Join Chroma recall hits with governed projection fields (origin, confidence)."""
        enriched: list[dict] = []
        for hit in hits:
            memory_id = hit.get("id")
            if not memory_id:
                continue
            rows = kernel.query_state("memories", id=memory_id)
            if not rows:
                continue
            row = rows[0]
            enriched.append({
                "id": memory_id,
                "content": row.get("content") or hit.get("content", ""),
                "confidence": float(row.get("confidence") or 0.5),
                "origin": row.get("origin") or "claim",
                "claim_status": row.get("claim_status"),
            })
        return enriched

    @staticmethod
    def _claim_status_label(claim_status: str | None) -> str:
        labels = {
            "proposed": "待你确认",
            "contested": "争议中",
            "ratified": "已署名",
        }
        if claim_status in labels:
            return f"[{labels[claim_status]}] "
        return ""

    def format_memory_context(self, memories: list[dict]) -> str:
        """Render memories with Meaning Boundary G2 + G1 authorship/authority framing."""
        if not memories:
            return ""

        presentable = [m for m in memories if can_present(m)]
        self_reports = [m for m in presentable if m.get("origin") == "self_report"]
        claims = [m for m in presentable if m.get("origin") != "self_report"]

        lines: list[str] = []
        if self_reports:
            lines.append("## 你告诉过我的（你的自述）")
            for i, mem in enumerate(self_reports, 1):
                lines.append(f"{i}. {mem['content']}")

        if claims:
            lines.append("## 系统推测（假设，非定论）")
            for i, mem in enumerate(claims, 1):
                conf = mem.get("confidence", 0.5)
                status_tag = self._claim_status_label(mem.get("claim_status"))
                lines.append(
                    f"{i}. {status_tag}[推测，置信度 {conf:.2f}] "
                    f"系统认为可能：{mem['content']}"
                )

        return "\n".join(lines)

    def retrieve_context_string(self, query: str, max_memories: int = 3) -> str:
        """Build a context string from relevant memories for injection into the LLM prompt."""
        hits = self.search_relevant_memories(query, n_results=max_memories)
        enriched = self._enrich_recall_hits(hits)
        return self.format_memory_context(enriched)

    def list_memories(self, category: str | None = None, limit: int = 50) -> list[dict]:
        """List stored memories via Kernel read ABI."""
        filters: dict = {"limit": limit}
        if category:
            filters["category"] = category
        return kernel.query_state("memories", **filters)

    def delete_memory(self, memory_id: str, actor: str = "user") -> None:
        """Delete a memory via Kernel event; Chroma index syncs in Kernel Space."""
        kernel.emit_event(
            type="MemoryDeleted",
            aggregate_type="memory",
            aggregate_id=memory_id,
            actor=actor,
        )

    def update_memory(
        self,
        memory_id: str,
        content: str,
        category: str | None = None,
        actor: str = "user",
    ) -> None:
        """Update an existing memory via Kernel event; Chroma index syncs in Kernel Space."""
        payload: dict = {"content": content}
        if category is not None:
            payload["category"] = category
        kernel.emit_event(
            type="MemoryUpdated",
            aggregate_type="memory",
            aggregate_id=memory_id,
            payload=payload,
            actor=actor,
        )


memory_engine = MemoryEngine()
