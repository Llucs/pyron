import json
import math
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

MEMORY_DIR = Path.home() / ".pyron" / "memory"
MAX_MEMORIES = 500
PRUNE_TARGET = 300

@dataclass
class MemoryItem:
    content: str
    category: str = "general"
    importance: float = 1.0
    frequency: int = 1
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    tags: list[str] = field(default_factory=list)
    relations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "category": self.category,
            "importance": self.importance,
            "frequency": self.frequency,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "tags": self.tags,
            "relations": self.relations,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MemoryItem":
        return cls(**d)


class HybridMemory:
    def __init__(self, namespace: str = "default"):
        self.namespace = namespace
        self.items: list[MemoryItem] = []
        self._dir = MEMORY_DIR / namespace
        self._dir.mkdir(parents=True, exist_ok=True)
        self._load()

    def _path(self) -> Path:
        return self._dir / "memories.json"

    def _load(self):
        p = self._path()
        if p.exists():
            try:
                data = json.loads(p.read_text())
                self.items = [MemoryItem.from_dict(d) for d in data]
            except (json.JSONDecodeError, KeyError):
                self.items = []

    def _save(self):
        self._path().write_text(json.dumps(
            [m.to_dict() for m in self.items], indent=2, ensure_ascii=False
        ))

    def add(self, content: str, category: str = "general", importance: float = 1.0,
            tags: list[str] | None = None, relations: list[str] | None = None):
        for existing in self.items:
            if existing.content == content:
                existing.frequency += 1
                existing.last_accessed = time.time()
                existing.importance = max(existing.importance, importance)
                if tags:
                    existing.tags = list(set(existing.tags + tags))
                if relations:
                    existing.relations = list(set(existing.relations + relations))
                self._save()
                return

        item = MemoryItem(
            content=content,
            category=category,
            importance=importance,
            tags=tags or [],
            relations=relations or [],
        )
        self.items.append(item)
        self._maybe_prune()
        self._save()

    def _keyword_match(self, text: str, query: str) -> float:
        text_lower = text.lower()
        query_lower = query.lower()
        words = set(query_lower.split())
        if not words:
            return 0.0
        matches = sum(1 for w in words if w in text_lower)
        return matches / len(words)

    def _recency_score(self, item: MemoryItem) -> float:
        age = time.time() - item.last_accessed
        return math.exp(-age / 86400)

    def _frequency_score(self, item: MemoryItem) -> float:
        return min(item.frequency / 10.0, 1.0)

    def _importance_score(self, item: MemoryItem) -> float:
        return min(item.importance / 5.0, 1.0)

    def _relation_score(self, item: MemoryItem, goal_tags: list[str] | None) -> float:
        if not goal_tags or not item.tags:
            return 0.0
        shared = set(goal_tags) & set(item.tags)
        if not shared:
            return 0.0
        return len(shared) / max(len(set(goal_tags)), 1)

    def search(self, query: str, top_k: int = 10, goal_tags: list[str] | None = None) -> list[MemoryItem]:
        scored = []
        for item in self.items:
            semantic = self._keyword_match(item.content, query)
            recency = self._recency_score(item)
            frequency = self._frequency_score(item)
            importance = self._importance_score(item)
            relation = self._relation_score(item, goal_tags)

            score = (
                semantic * 0.30 +
                recency * 0.15 +
                frequency * 0.15 +
                importance * 0.20 +
                relation * 0.20
            )

            if score > 0:
                scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:top_k]]

    def _maybe_prune(self):
        if len(self.items) <= MAX_MEMORIES:
            return
        scored = []
        for item in self.items:
            score = (
                self._importance_score(item) * 0.4 +
                self._recency_score(item) * 0.3 +
                self._frequency_score(item) * 0.3
            )
            scored.append((score, item))
        scored.sort(key=lambda x: x[0])
        keep_count = PRUNE_TARGET
        keep_items = [item for _, item in scored[-keep_count:]]
        self.items = keep_items

    def get_context(self, query: str, goal_tags: list[str] | None = None, max_items: int = 5) -> str:
        results = self.search(query, top_k=max_items, goal_tags=goal_tags)
        if not results:
            return ""
        lines = ["Relevant context from memory:"]
        for i, item in enumerate(results, 1):
            tag_str = f" [{', '.join(item.tags)}]" if item.tags else ""
            lines.append(f"  {i}. {item.content}{tag_str}")
        return "\n".join(lines)

    def clear(self):
        self.items = []
        self._save()


SESSION_MEMORY: dict[str, HybridMemory] = {}

def get_memory(namespace: str = "default") -> HybridMemory:
    if namespace not in SESSION_MEMORY:
        SESSION_MEMORY[namespace] = HybridMemory(namespace)
    return SESSION_MEMORY[namespace]
