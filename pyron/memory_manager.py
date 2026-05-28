import json
import time
import math
import hashlib
import random
import re
from collections import Counter
from typing import Optional, Callable

TOKEN_ESTIMATE_RATIO = 4.0


def estimate_tokens(text: str) -> int:
    words = len(text.split())
    chars = len(text)
    return max(words, chars // 4)


class EmbeddingEngine:
    def __init__(self, dim: int = 256, ngram_range: tuple = (2, 4)):
        self.dim = dim
        self.ngram_range = ngram_range

    def embed(self, text: str) -> list[float]:
        text = text.lower()
        ngram_counts: Counter = Counter()
        for n in range(self.ngram_range[0], self.ngram_range[1] + 1):
            for i in range(len(text) - n + 1):
                ngram_counts[text[i:i + n]] += 1

        vector = [0.0] * self.dim
        for ngram, count in ngram_counts.items():
            h = hashlib.md5(ngram.encode()).hexdigest()
            idx = int(h[:8], 16) % self.dim
            vector[idx] += count

        magnitude = math.sqrt(sum(v * v for v in vector))
        if magnitude > 0:
            vector = [v / magnitude for v in vector]
        return vector


class VectorStore:
    def __init__(self, engine: EmbeddingEngine):
        self.engine = engine
        self.vectors: dict[str, list[float]] = {}
        self.texts: dict[str, str] = {}
        self.metadata: dict[str, dict] = {}
        self.timestamps: dict[str, float] = {}

    def add(self, text_id: str, text: str, metadata: dict | None = None):
        vec = self.engine.embed(text)
        self.vectors[text_id] = vec
        self.texts[text_id] = text
        self.metadata[text_id] = metadata or {}
        self.timestamps[text_id] = time.time()

    def remove(self, text_id: str):
        for d in (self.vectors, self.texts, self.metadata, self.timestamps):
            d.pop(text_id, None)

    def _cosine_similarity(self, v1: list[float], v2: list[float]) -> float:
        return sum(a * b for a, b in zip(v1, v2))

    def search(self, query: str, k: int = 10) -> list[dict]:
        if not self.vectors:
            return []
        query_vec = self.engine.embed(query)
        now = time.time()
        scores = []
        for tid in self.vectors:
            semantic = self._cosine_similarity(query_vec, self.vectors[tid])
            age_hours = (now - self.timestamps[tid]) / 3600
            recency = 1.0 / (1.0 + age_hours)
            importance = self.metadata[tid].get("importance", 0.5)
            score = 0.6 * semantic + 0.25 * recency + 0.15 * importance
            scores.append((score, tid))
        scores.sort(reverse=True)
        return [
            {
                "id": tid,
                "text": self.texts[tid],
                "metadata": self.metadata[tid],
                "score": score,
                "timestamp": self.timestamps[tid],
            }
            for score, tid in scores[:k]
        ]

    def count(self) -> int:
        return len(self.vectors)

    def all_items_sorted(self) -> list[tuple[str, str, dict]]:
        items = [
            (self.timestamps[tid], tid, self.texts[tid], self.metadata[tid])
            for tid in self.vectors
        ]
        items.sort(key=lambda x: x[0])
        return [(tid, text, meta) for _, tid, text, meta in items]


class KnowledgeGraph:
    def __init__(self):
        self.entities: dict[str, dict] = {}
        self.relations: list[dict] = []

    def add_entity(self, name: str, entity_type: str = "concept", attributes: dict | None = None):
        key = name.lower().strip()
        if not key:
            return
        now = time.time()
        if key not in self.entities:
            self.entities[key] = {
                "name": name.strip(),
                "type": entity_type,
                "attributes": attributes or {},
                "created": now,
                "updated": now,
                "access_count": 0,
            }
        else:
            self.entities[key]["updated"] = now
            if attributes:
                self.entities[key]["attributes"].update(attributes)

    def add_relation(self, source: str, relation: str, target: str, metadata: dict | None = None):
        sk, tk = source.lower().strip(), target.lower().strip()
        if not sk or not tk:
            return
        self.add_entity(source)
        self.add_entity(target)
        self.relations.append({
            "source": sk,
            "relation": relation.lower().strip(),
            "target": tk,
            "metadata": metadata or {},
            "timestamp": time.time(),
        })

    def get_entity(self, name: str) -> Optional[dict]:
        key = name.lower().strip()
        ent = self.entities.get(key)
        if ent:
            ent["access_count"] = ent.get("access_count", 0) + 1
        return ent

    def query_relations(self, source: str | None = None, relation: str | None = None, target: str | None = None) -> list[dict]:
        results = []
        for r in self.relations:
            if source and r["source"] != source.lower().strip():
                continue
            if relation and r["relation"] != relation.lower().strip():
                continue
            if target and r["target"] != target.lower().strip():
                continue
            results.append(r)
        return results

    def get_relevant_context(self, query: str, max_entities: int = 5) -> str:
        ql = query.lower()
        scored = []
        for key, ent in self.entities.items():
            if key in ql or any(kw in ql for kw in key.split() if len(kw) > 2):
                scored.append((ent.get("access_count", 0), key, ent))
        scored.sort(reverse=True)
        lines = []
        for _, key, ent in scored[:max_entities]:
            lines.append(f"  {ent['name']} ({ent['type']})")
            for k, v in ent.get("attributes", {}).items():
                lines.append(f"    {k}: {v}")
            for r in self.query_relations(source=key)[:3]:
                lines.append(f"    -> {r['relation']} -> {r['target']}")
            for r in self.query_relations(target=key)[:3]:
                lines.append(f"    <- {r['relation']} <- {r['source']}")
        return "\n".join(lines) if lines else ""

    def count_entities(self) -> int:
        return len(self.entities)

    def count_relations(self) -> int:
        return len(self.relations)


class HierarchicalSummary:
    def __init__(self):
        self.level1: Optional[str] = None
        self.level2: Optional[str] = None
        self.level3: Optional[str] = None

    def get_context(self, max_tokens: int = 3000) -> str:
        parts = []
        if self.level3:
            parts.append(f"[Strategic Overview]\n{self.level3}")
        if self.level2:
            parts.append(f"[Medium-term Summary]\n{self.level2}")
        if self.level1:
            parts.append(f"[Recent Context]\n{self.level1}")
        return "\n\n".join(parts) if parts else ""


class ContextCompressor:
    def __init__(self, compress_fn: Callable | None = None):
        self.threshold = 140_000
        self.target_ratio = 0.3
        self.compress_fn = compress_fn
        self.compression_count = 0

    def estimate_tokens(self, text: str) -> int:
        return estimate_tokens(text)

    def needs_compression(self, token_count: int) -> bool:
        return token_count > self.threshold

    def compress(self, text: str, target_ratio: float | None = None) -> str:
        ratio = target_ratio or self.target_ratio
        if self.compress_fn:
            self.compression_count += 1
            return self.compress_fn(text, ratio)
        return text


class ReflectionEngine:
    def __init__(self, reflect_fn: Callable | None = None):
        self.interaction_count = 0
        self.next_reflection = random.randint(8, 12)
        self.reflect_fn = reflect_fn
        self.last_reflection: Optional[str] = None

    def step(self):
        self.interaction_count += 1

    def should_reflect(self) -> bool:
        return self.interaction_count >= self.next_reflection and self.interaction_count > 0

    def reflect(self, kg: KnowledgeGraph | None = None) -> Optional[str]:
        if not self.should_reflect():
            return None
        interval = random.randint(8, 12)
        self.next_reflection = self.interaction_count + interval
        if self.reflect_fn:
            result = self.reflect_fn(kg)
            self.last_reflection = result
            return result
        self.last_reflection = "[Reflection completed: no reflection function configured]"
        return self.last_reflection


class ForgettingCurve:
    def __init__(self):
        self.decay_rate = 0.1
        self.importance_boost = 0.3
        self.access_boost = 0.1

    def compute_retention(self, age_hours: float, importance: float, access_count: int) -> float:
        base_decay = math.exp(-self.decay_rate * age_hours)
        importance_factor = 1.0 + self.importance_boost * importance
        access_factor = 1.0 + self.access_boost * math.log1p(access_count)
        return min(1.0, base_decay * importance_factor * access_factor)

    def should_forget(self, retention: float, threshold: float = 0.1) -> bool:
        return retention < threshold

    def prune(self, store: VectorStore, threshold: float = 0.1) -> int:
        now = time.time()
        to_remove = []
        for tid in list(store.vectors.keys()):
            age_hours = (now - store.timestamps.get(tid, now)) / 3600
            meta = store.metadata.get(tid, {})
            importance = meta.get("importance", 0.3)
            access = meta.get("access_count", 0)
            retention = self.compute_retention(age_hours, importance, access)
            if self.should_forget(retention, threshold):
                to_remove.append(tid)
        for tid in to_remove:
            store.remove(tid)
        return len(to_remove)


SYSTEM_MASTER_PROMPT = (
    "Voc\u00ea \u00e9 Pyron, uma IA aut\u00f4noma com mem\u00f3ria expandida para ~1 milh\u00e3o de tokens "
    "utilizando camadas hier\u00e1rquicas.\n\n"
    "Camadas dispon\u00edveis:\n"
    "- Working Memory (contexto atual)\n"
    "- Vector Memory (busca sem\u00e2ntica)\n"
    "- Hierarchical Summaries (resumos por n\u00edvel)\n"
    "- Knowledge Graph (conhecimento estruturado)\n\n"
    "Regras:\n"
    "- Comprima o contexto quando necess\u00e1rio usando a ferramenta de compress\u00e3o.\n"
    "- Priorize efici\u00eancia extrema de tokens.\n"
    "- Mantenha coer\u00eancia de longo prazo atrav\u00e9s do grafo de conhecimento.\n"
    "- Fa\u00e7a reflection peri\u00f3dica sobre objetivos e aprendizados."
)


class MemoryManager:
    def __init__(self, compress_fn: Callable | None = None, reflect_fn: Callable | None = None):
        self.embedding = EmbeddingEngine(dim=256)
        self.vector_store = VectorStore(self.embedding)
        self.summaries = HierarchicalSummary()
        self.knowledge_graph = KnowledgeGraph()
        self.compressor = ContextCompressor(compress_fn)
        self.reflection = ReflectionEngine(reflect_fn)
        self.forgetting = ForgettingCurve()
        self.working_memory: list[dict] = []
        self.working_token_count = 0
        self.max_working_tokens = 180_000
        self.interaction_id = 0

    def save_interaction(self, role: str, content: str, importance: float = 0.5,
                         tags: list | None = None, entities: list | None = None):
        if not content or not content.strip():
            return
        self.interaction_id += 1
        iid = f"int_{self.interaction_id}"
        meta = {
            "role": role,
            "importance": importance,
            "tags": tags or [],
            "entities": entities or [],
            "access_count": 0,
        }
        self.vector_store.add(iid, content, meta)
        if entities:
            for ent in entities:
                if isinstance(ent, str):
                    self.knowledge_graph.add_entity(ent)
                elif isinstance(ent, dict):
                    self.knowledge_graph.add_entity(
                        ent.get("name", ""), ent.get("type", "concept"), ent
                    )
        self._extract_entities(content)
        self.working_memory.append({"role": role, "content": content, "metadata": meta})
        self.working_token_count += estimate_tokens(content)
        self._trim_working_memory()
        self.reflection.step()

    def _extract_entities(self, text: str):
        for match in re.finditer(r'"([^"]+)"', text):
            ent = match.group(1).strip()
            if 2 < len(ent) < 50:
                self.knowledge_graph.add_entity(ent)
        for match in re.finditer(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', text):
            ent = match.group(1).strip()
            if 2 < len(ent) < 50:
                self.knowledge_graph.add_entity(ent)

    def retrieve_context(self, query: str, max_tokens: int = 6000) -> str:
        parts = []
        wm = self._working_context(max_tokens // 5)
        if wm:
            parts.append(f"[Working Memory]\n{wm}")
        vs = self.vector_store.search(query, k=5)
        if vs:
            parts.append("[Related Memories]\n" + "\n".join(
                f"- {r['text'][:250]}" for r in vs
            ))
        sc = self.summaries.get_context(max_tokens // 5)
        if sc:
            parts.append(f"[Summaries]\n{sc}")
        kg = self.knowledge_graph.get_relevant_context(query)
        if kg:
            parts.append(f"[Knowledge Graph]\n{kg}")
        if self.reflection.last_reflection:
            parts.append(f"[Last Reflection]\n{self.reflection.last_reflection}")
        return "\n\n".join(parts)

    def _working_context(self, max_tokens: int) -> str:
        tokens = 0
        lines = []
        for msg in reversed(self.working_memory):
            t = estimate_tokens(msg["content"])
            if tokens + t > max_tokens:
                break
            tokens += t
            prefix = "User: " if msg["role"] == "user" else "Assistant: "
            lines.append(prefix + msg["content"])
        return "\n".join(reversed(lines))

    def _trim_working_memory(self):
        while self.working_token_count > self.max_working_tokens and len(self.working_memory) > 1:
            removed = self.working_memory.pop(0)
            self.working_token_count -= estimate_tokens(removed["content"])

    def check_and_compress(self) -> bool:
        if self.compressor.needs_compression(self.working_token_count):
            for msg in self.working_memory:
                if msg["role"] == "assistant" and estimate_tokens(msg["content"]) > 500:
                    compressed = self.compressor.compress(msg["content"])
                    if compressed != msg["content"]:
                        old_tokens = estimate_tokens(msg["content"])
                        new_tokens = estimate_tokens(compressed)
                        self.working_token_count -= old_tokens - new_tokens
                        msg["content"] = compressed
                        msg["metadata"]["compressed"] = True
            return True
        return False

    def update_summary(self, level: int, summary_text: str):
        if level == 1:
            self.summaries.level1 = summary_text
        elif level == 2:
            self.summaries.level2 = summary_text
        elif level == 3:
            self.summaries.level3 = summary_text

    def add_relation(self, source: str, relation: str, target: str, metadata: dict | None = None):
        self.knowledge_graph.add_relation(source, relation, target, metadata)

    def add_entity(self, name: str, entity_type: str = "concept", attributes: dict | None = None):
        self.knowledge_graph.add_entity(name, entity_type, attributes)

    def apply_forgetting(self, threshold: float = 0.05) -> int:
        return self.forgetting.prune(self.vector_store, threshold)

    def get_stats(self) -> dict:
        return {
            "working_items": len(self.working_memory),
            "working_tokens": self.working_token_count,
            "vector_items": self.vector_store.count(),
            "kg_entities": self.knowledge_graph.count_entities(),
            "kg_relations": self.knowledge_graph.count_relations(),
            "compressions": self.compressor.compression_count,
            "interactions": self.reflection.interaction_count,
            "level1_summary": self.summaries.level1 is not None,
            "level2_summary": self.summaries.level2 is not None,
            "level3_summary": self.summaries.level3 is not None,
        }

    def to_dict(self) -> dict:
        vs_items = self.vector_store.all_items_sorted()
        return {
            "vector_store": [
                {"id": tid, "text": t[:200], "meta": m}
                for tid, t, m in vs_items
            ],
            "kg_entities": list(self.knowledge_graph.entities.keys()),
            "kg_relations": [
                f"{r['source']} -[{r['relation']}]-> {r['target']}"
                for r in self.knowledge_graph.relations
            ],
            "summaries": {
                "level1": bool(self.summaries.level1),
                "level2": bool(self.summaries.level2),
                "level3": bool(self.summaries.level3),
            },
            "stats": self.get_stats(),
        }
