"""
telemetry.py
Owner: Language Brain (Kavyansh)

Lightweight in-memory metrics tracking - no external dependencies.
Useful for demo numbers ("here's our cache hit rate", "here's our
average latency") without needing a real observability stack.
"""

import time
from dataclasses import dataclass, field


@dataclass
class Metrics:
    cache_hits: int = 0
    cache_misses: int = 0
    llm_failures: int = 0
    total_llm_calls: int = 0
    total_tokens: int = 0

    cache_lookup_latencies_ms: list = field(default_factory=list)
    retrieval_latencies_ms: list = field(default_factory=list)
    llm_latencies_ms: list = field(default_factory=list)

    @property
    def cache_hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total else 0.0

    @property
    def avg_retrieval_latency_ms(self) -> float:
        return _avg(self.retrieval_latencies_ms)

    @property
    def avg_llm_latency_ms(self) -> float:
        return _avg(self.llm_latencies_ms)

    @property
    def llm_failure_rate(self) -> float:
        return self.llm_failures / self.total_llm_calls if self.total_llm_calls else 0.0


def _avg(values: list) -> float:
    return sum(values) / len(values) if values else 0.0


_metrics = Metrics()


def record_cache_hit(lookup_ms: int) -> None:
    _metrics.cache_hits += 1
    _metrics.cache_lookup_latencies_ms.append(lookup_ms)


def record_cache_miss(retrieval_ms: int, llm_ms: int, tokens: int = 0, llm_failed: bool = False) -> None:
    _metrics.cache_misses += 1
    _metrics.retrieval_latencies_ms.append(retrieval_ms)
    if llm_ms:
        _metrics.total_llm_calls += 1
        _metrics.llm_latencies_ms.append(llm_ms)
        _metrics.total_tokens += tokens
        if llm_failed:
            _metrics.llm_failures += 1


def get_metrics() -> Metrics:
    return _metrics


def reset_metrics() -> None:
    global _metrics
    _metrics = Metrics()


def print_summary() -> None:
    m = _metrics
    print("=== Telemetry Summary ===")
    print(f"Cache hit rate:        {m.cache_hit_rate:.1%} ({m.cache_hits} hits / {m.cache_misses} misses)")
    print(f"Avg retrieval latency: {m.avg_retrieval_latency_ms:.1f} ms")
    print(f"Avg LLM latency:       {m.avg_llm_latency_ms:.1f} ms")
    print(f"Total LLM calls:       {m.total_llm_calls}")
    print(f"LLM failure rate:      {m.llm_failure_rate:.1%}")
    print(f"Total tokens used:     {m.total_tokens}")
