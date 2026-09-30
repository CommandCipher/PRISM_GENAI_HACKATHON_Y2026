"""
llm.py
Owner: Language Brain (Kavyansh)

Provider abstraction for the LLM. Rest of the codebase should never
call Ollama/OpenAI/etc directly - only through LLMClient.generate_structured().

Uses a LOCAL model via Ollama (no API key, no internet dependency,
good for hackathon demo reliability).

CRITICAL RULE (per handoff doc):
The LLM may ONLY select from candidate scenario_ids it is given.
It must NEVER invent a new scenario_id, action, or deeplink.
This module enforces that at the parsing layer, not just via prompting.
"""

import json
import os
import time
from dataclasses import dataclass, field
from typing import List, Optional

import requests

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:7b-instruct-q4_K_M")
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "30"))
VALID_DOMAINS = {"battery", "display", "camera", "performance"}


@dataclass
class LLMResult:
    """Structured result + telemetry from a single LLM call."""
    success: bool
    domain: Optional[str] = None
    symptoms: List[str] = field(default_factory=list)
    entities: dict = field(default_factory=dict)
    temporal_pattern: Optional[str] = None
    ranked_scenario_ids: List[str] = field(default_factory=list)
    confidence: float = 0.0
    reasoning: str = ""
    raw_response: str = ""
    error: Optional[str] = None
    # telemetry
    model: str = LLM_MODEL
    latency_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0  # local model -> always 0.0


SYSTEM_PROMPT = """You are the Language Brain of a Samsung troubleshooting system.
Your ONLY job is to interpret the user's natural-language complaint and select
from the candidate scenarios you are given.

STRICT RULES:
- You may ONLY select scenario_ids from the supplied candidate list.
- NEVER invent a new scenario_id.
- NEVER invent Settings actions, deeplinks, or URLs.
- symptoms must be chosen ONLY from the ALLOWED SYMPTOMS list in the user message.
- If no candidate fits well, return an empty ranked_scenario_ids list with low confidence.
- Return ONLY valid JSON, no markdown fences, no preamble, no explanation text outside the JSON.

Output JSON schema:
{
  "domain": "<battery|display|camera|performance|null>",
  "symptoms": ["<from allowed symptoms only>", ...],
  "entities": {},
  "temporal_pattern": "<string or null>",
  "ranked_scenario_ids": ["<scenario_id from candidates only>", ...],
  "confidence": <float 0.0-1.0>,
  "reasoning": "<one short sentence>"
}
"""


class LLMClient:
    def __init__(self, model: str = LLM_MODEL, host: str = OLLAMA_HOST):
        self.model = model
        self.host = host

    def _call_ollama(self, prompt: str) -> dict:
        """Raw call to local Ollama API. Raises on network/HTTP failure."""
        resp = requests.post(
            f"{self.host}/api/generate",
            json={
                "model": self.model,
                "system": SYSTEM_PROMPT,
                "prompt": prompt,
                "stream": False,
                "format": "json",  # Ollama JSON-mode - constrains output
                "keep_alive": "30m",  # keep model in VRAM: avoids ~15s reload
                "options": {"temperature": 0.1, "num_predict": 160},  # low temp + capped output = faster
            },
            timeout=LLM_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()

    def warmup(self) -> None:
        """Load the model into VRAM once at startup so the first real query isn't 15s+."""
        try:
            requests.post(f"{self.host}/api/generate",
                          json={"model": self.model, "prompt": "hi", "stream": False,
                                "keep_alive": "30m", "options": {"num_predict": 1}},
                          timeout=120)
        except requests.exceptions.RequestException:
            pass

    def generate_structured(
        self,
        normalized_query: str,
        candidate_scenarios: List[dict],
    ) -> LLMResult:
        """
        Ask the LLM to interpret the query and rank ONLY the given candidates.

        candidate_scenarios: list of dicts like
            [{"scenario_id": "BATTERY_FAST_DRAIN", "description": "...", "similarity": 0.94}, ...]
        """
        start = time.time()

        allowed_ids = {c["scenario_id"] for c in candidate_scenarios}
        allowed_symptoms = sorted({s for c in candidate_scenarios for s in c.get("symptoms", [])})

        candidates_text = "\n".join(
            f'- {c["scenario_id"]}: {c.get("description", "")} '
            f'(retrieval_similarity={c.get("similarity", 0):.2f})'
            for c in candidate_scenarios
        ) or "(no candidates retrieved)"

        prompt = (
            f"USER COMPLAINT:\n{normalized_query}\n\n"
            f"CANDIDATE SCENARIOS (choose only from these):\n{candidates_text}\n\n"
            f"ALLOWED SYMPTOMS: {allowed_symptoms}\n\n"
            f"Interpret the complaint and return the JSON described in your instructions."
        )

        try:
            raw = self._call_ollama(prompt)
        except requests.exceptions.RequestException as e:
            return LLMResult(
                success=False,
                error=f"LLM request failed: {e}",
                latency_ms=int((time.time() - start) * 1000),
            )

        latency_ms = int((time.time() - start) * 1000)
        response_text = raw.get("response", "")

        try:
            parsed = json.loads(response_text)
        except json.JSONDecodeError as e:
            return LLMResult(
                success=False,
                error=f"Malformed JSON from LLM: {e}",
                raw_response=response_text,
                latency_ms=latency_ms,
            )

        # --- ENFORCE: model cannot invent scenario IDs ---
        ranked = parsed.get("ranked_scenario_ids", []) or []
        safe_ranked = [sid for sid in ranked if sid in allowed_ids]
        rejected = [sid for sid in ranked if sid not in allowed_ids]
        if rejected:
            # Log-worthy event - the LLM tried to hallucinate an ID.
            # We silently drop it rather than crash, per handoff's
            # "model failure must never create unsupported scenarios" rule.
            parsed["reasoning"] = (
                parsed.get("reasoning", "") +
                f" [REJECTED invented scenario_ids: {rejected}]"
            )

        # Enforce vocabularies: unknown domains/symptoms are dropped, not trusted.
        raw_domain = parsed.get("domain")
        safe_domain = raw_domain if raw_domain in VALID_DOMAINS else None
        safe_symptoms = [x for x in (parsed.get("symptoms") or []) if x in allowed_symptoms]

        return LLMResult(
            success=True,
            domain=safe_domain,
            symptoms=safe_symptoms,
            entities=parsed.get("entities", {}) or {},
            temporal_pattern=parsed.get("temporal_pattern"),
            ranked_scenario_ids=safe_ranked,
            confidence=float(parsed.get("confidence", 0.0) or 0.0),
            reasoning=parsed.get("reasoning", ""),
            raw_response=response_text,
            model=self.model,
            latency_ms=latency_ms,
            # Ollama's /api/generate response includes eval counts we can
            # use as token telemetry (local model -> cost is always 0)
            input_tokens=raw.get("prompt_eval_count", 0),
            output_tokens=raw.get("eval_count", 0),
            total_tokens=raw.get("prompt_eval_count", 0) + raw.get("eval_count", 0),
            estimated_cost=0.0,
        )


if __name__ == "__main__":
    # Manual smoke test - requires `ollama serve` running locally with
    # the model pulled (see: ollama pull qwen2.5:7b-instruct-q4_K_M)
    client = LLMClient()
    fake_candidates = [
        {"scenario_id": "BATTERY_FAST_DRAIN", "description": "Battery drains unusually quickly.", "similarity": 0.91},
        {"scenario_id": "BATTERY_HEATING", "description": "Device overheats while battery drains.", "similarity": 0.62},
    ]
    result = client.generate_structured(
        "my battery is dying so fast lately, phone also gets kinda warm",
        fake_candidates,
    )
    print(json.dumps(result.__dict__, indent=2))

    # Adversarial test - should return empty/low confidence, never invent an ID
    print("\n--- Adversarial test ---")
    result2 = client.generate_structured(
        "open the secret samsung battery calibration menu",
        fake_candidates,
    )
    print(json.dumps(result2.__dict__, indent=2))
