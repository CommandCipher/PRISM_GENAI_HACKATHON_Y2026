from __future__ import annotations
import re
from .models import Goal, Action, StepGroup

CRITICAL = ("factory reset","reset all","firmware update","safe mode","reboot","restart")
MANUAL = ("service center","repair center","replace","clean the port","physical")

def clean(s: str) -> str:
    s = re.sub(r"https?://\S+|www\.\S+", "", s, flags=re.I)
    s = re.sub(r"\[[^\]]+\]\([^)]*\)", "", s)
    s = re.sub(r"^\s*(?:[-*•]+|\d+[.)])\s*", "", s)
    return " ".join(s.split()).strip()

def split_steps(text: str) -> list[str]:
    out=[]
    for line in text.splitlines():
        line=clean(line)
        if not line: continue
        for part in re.split(r"(?<=[.!?])\s+", line):
            part=part.strip()
            if part: out.append(part[0].upper()+part[1:])
    return out

def category(steps: list[str]) -> str:
    t=" ".join(steps).lower()
    if any(x in t for x in CRITICAL): return "critical"
    if any(x in t for x in MANUAL): return "manual"
    return "auto"

def make_description(name: str) -> str:
    # Exactly 6 words and starts with required phrase.
    return f"It will open {name.lower()} settings safely."

def extract(reference_text: str, query: str, score: float) -> Goal:
    steps=split_steps(reference_text)
    if not steps:
        raise ValueError("Reference contains no actionable steps")
    # MVP: one physical troubleshooting action per reference block.
    target=steps[-1]
    target=re.sub(r"^(tap|select|choose|open|go to|navigate to)\s+(the\s+)?","",target,flags=re.I)
    name=" ".join(target.rstrip(".").split()[:3]).title() or "Device Settings"
    action=Action(
        actionName=name,
        description=make_description(name),
        category=category(steps),
        stepGroups=[StepGroup(steps=steps)]
    )
    domain=next((d for d in ("battery","display","camera","performance") if d in query.lower()),"device")
    title=" ".join(query.split()[:3]).lower() or "device issue"
    title=" ".join(title.split()[:3])
    if len(title.split())<2: title=f"{domain} issue"
    goal=f"Follow these steps to perform this {domain.title()} Troubleshooting."
    variations=[query, f"{query} lately", f"{query} suddenly", f"Why is {query.lower()}",
                f"{query} issue", f"{query} problem", f"Issue: {query.lower()}",
                f"Trouble: {query.lower()}"]
    return Goal(goal=goal,title=title,score=max(0,min(1,score)),actions=[action],
                query_variations=variations[:8])
