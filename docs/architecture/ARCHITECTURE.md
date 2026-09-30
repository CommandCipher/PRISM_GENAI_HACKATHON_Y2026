# Smart Guided Troubleshooting Engine
## Samsung PRISM GenAI Hackathon 2026 — Theme 2

## 1. Core Objective

Convert a vague device complaint into a validated, minimal and actionable
troubleshooting plan with exact Settings deeplinks.

## 2. Core Features

1. Complaint DNA + Semantic Cache
2. Two-Brain Architecture
3. Deeplink Guardian
4. Hallucination Honeypot
5. Minimum-Fix Mode
6. Adaptive Decision Loop
7. Confidence + Clarification Gate

## 3. High-Level Pipeline

User Complaint
        ↓
Complaint DNA
        ↓
Confidence / Clarification Gate
        ↓
Semantic Cache
        ↓
Two-Brain Architecture
        ↓
Adaptive Decision Loop
        ↓
Minimum-Fix Mode
        ↓
Deeplink Guardian
        ↓
Hallucination Validation
        ↓
Structured JSON
        ↓
REST API

## 4. Language Brain

Responsibilities:

- Understand natural-language complaints
- Normalize colloquial language
- Extract intent, domain and symptoms
- Generate candidate troubleshooting actions
- Estimate confidence

The Language Brain must NOT invent Settings deeplinks.

## 5. Device Brain

Responsibilities:

- Retrieve valid actions from the supplied catalog
- Maintain action relationships
- Determine valid troubleshooting sequences
- Resolve exact deeplinks
- Validate generated plans
- Reject unsupported actions

## 6. Complaint DNA

Convert different user phrasings into a canonical representation.

Example:

"My battery dies crazy fast"
"Battery drains very quickly"
"Phone loses 20% in 30 minutes"

→ BATTERY + FAST_DRAIN

## 7. Semantic Cache

- Match semantically similar complaints
- Return previously validated troubleshooting plans
- Support the fast-path requirement
- Avoid invoking the LLM for known scenarios

## 8. Confidence / Clarification Gate

If confidence is high:
→ proceed with troubleshooting.

If confidence is low:
→ ask the smallest useful clarification question.

## 9. Adaptive Decision Loop

The troubleshooting plan is stateful.

UNTRIED
   ↓
ATTEMPTED
   ↓
SUCCESS / FAILURE / UNKNOWN

The next action depends on the observed result.

Previously attempted actions should not be unnecessarily repeated.

## 10. Minimum-Fix Mode

Optimize for:

- Fewer steps
- Lower user effort
- Lower unnecessary intervention
- Valid troubleshooting sequence

## 11. Deeplink Guardian

Every action must be validated against the supplied catalog.

Checks include:

- Action exists
- Action and deeplink correspond
- Correct hierarchy
- Exact catalog deeplink
- No generated or modified URL

## 12. Hallucination Honeypot

Use adversarial/non-existent requests to test whether the system invents:

- Settings
- Actions
- Deeplinks
- Unsupported troubleshooting procedures

Invalid actions must be rejected.

## 13. Output

The backend returns structured JSON containing:

- Goal
- Title
- Score
- Actions
- Steps
- Descriptions
- Categories
- Associated deeplinks

## 14. Engineering Principle

LLM understands the user.

Deterministic systems control the available device actions.

The LLM should never be the source of truth for deeplinks.