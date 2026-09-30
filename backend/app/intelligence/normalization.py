"""
normalization.py
Owner: Language Brain (Kavyansh)

Responsible for cleaning up messy, colloquial user complaints into a
more standard form WITHOUT destroying meaningful information (temporal
clues, severity words, etc. are preserved).

This does NOT do semantic understanding - just text cleanup.
"""

import re
import unicodedata

# Common informal contractions / slang worth expanding for better
# embedding quality. Keep this list small and intentional - don't
# over-engineer a full slang dictionary.
_EXPANSIONS = {
    r"\bbatt\b": "battery",
    r"\bphn\b": "phone",
    r"\brn\b": "right now",
    r"\bur\b": "your",
    r"\bu\b": "you",
    r"\bpls\b": "please",
    r"\bplz\b": "please",
    r"\bdont\b": "do not",
    r"\bcant\b": "cannot",
    r"\bwont\b": "will not",
}

_MULTI_PUNCT_RE = re.compile(r"([!?.]){2,}")
_MULTI_SPACE_RE = re.compile(r"\s{2,}")
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002700-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "]+",
    flags=re.UNICODE,
)


def normalize_query(raw_query: str) -> str:
    """
    Clean a raw user complaint into a normalized string suitable for
    embedding and LLM input.

    Example:
        "battery's trash rn!!!"  ->  "battery is trash right now"

    This intentionally does NOT:
      - remove domain-relevant words
      - strip temporal phrases ("since yesterday", "after the update")
      - strip severity words ("insanely", "barely")
    because those carry meaning the retrieval/LLM layers need.
    """
    if not raw_query or not raw_query.strip():
        return ""

    text = raw_query.strip()

    # Normalize unicode (handles smart quotes, accented chars, etc.)
    text = unicodedata.normalize("NFKC", text)

    # Lowercase for consistent matching (embeddings are case-insensitive
    # in effect for most sentence-transformer models, but this keeps
    # things deterministic for caching/logging too).
    text = text.lower()

    # Strip emojis - they add noise to embeddings for this use case.
    text = _EMOJI_RE.sub("", text)

    # Collapse repeated punctuation: "!!!" -> "!", "???" -> "?"
    text = _MULTI_PUNCT_RE.sub(r"\1", text)

    # Expand common contractions/slang (word-boundary safe)
    for pattern, replacement in _EXPANSIONS.items():
        text = re.sub(pattern, replacement, text)

    # Fix possessive contractions like "battery's" -> "battery is"
    # (only for common patterns, not full grammar correction)
    text = re.sub(r"\bbattery's\b", "battery is", text)
    text = re.sub(r"\bphone's\b", "phone is", text)

    # Collapse multiple spaces
    text = _MULTI_SPACE_RE.sub(" ", text).strip()

    return text


def generate_cache_key_text(normalized_query: str) -> str:
    """
    Produce a canonical text form used ONLY as a fallback/logging key,
    not as the actual semantic cache key (semantic cache uses embedding
    similarity, per architecture rules - see semantic_cache.py).
    """
    # Remove punctuation entirely for a loose canonical form
    text = re.sub(r"[^\w\s]", "", normalized_query)
    text = _MULTI_SPACE_RE.sub(" ", text).strip()
    return text


if __name__ == "__main__":
    # Quick manual sanity check
    tests = [
        "battery's trash rn!!!",
        "My phone gets extremely hot and then the battery drops????",
        "Screen navigation gestures are misbehaving after an app download.",
        "   ",
        "PHONE IS SO SLOW SINCE THE UPDATE 😡😡😡",
    ]
    for t in tests:
        print(f"{t!r:70} -> {normalize_query(t)!r}")
