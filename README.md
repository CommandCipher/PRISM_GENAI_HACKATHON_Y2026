# PRISM_GENAI_HACKATHON_Y2026

## Samsung PRISM GenAI Hackathon 2026 — Theme 2
### Smart Guided Troubleshooting Engine

**Team CommandCipher — Thapar Institute of Engineering & Technology**

---

## 🔗 Submission Links

- **GitHub Repository:** https://github.com/CommandCipher/PRISM_GENAI_HACKATHON_Y2026
- **Demo Video:** https://drive.google.com/file/d/1F3vYDexn1fQXMn3HBA-1nloOzQaRz0Rl/view?usp=sharing
- **Presentation:** https://docs.google.com/presentation/d/1XrVwm8o0SCj7ucRrVKBcosnQ9MBAkl8j/edit?usp=sharing&ouid=100540235193673154263&rtpof=true&sd=true
- **AI Disclosure:** https://docs.google.com/document/d/1zhMqxx-Jsflw02vgvSCtCJq2uUgHRImv/edit?usp=sharing&ouid=100540235193673154263&rtpof=true&sd=true

---

## 1. Problem Statement

Users often describe device problems using vague natural-language complaints such as:

> "My touchscreen is not responding"

Traditional troubleshooting systems often rely on static FAQs or keyword matching, making it difficult to identify the correct troubleshooting path and navigate to relevant device settings.

The goal is to convert a vague user complaint into a **structured, validated troubleshooting workflow** with actionable Settings deeplinks wherever available.

---

## 2. Solution

Our system uses a two-brain architecture:

```text
User Query
    ↓
Language Brain
    ↓
Scenario Retrieval
    ↓
Device Brain
    ↓
Validation + Deeplink Mapping
    ↓
Structured JSON Response
    ↓
Frontend
```

### Language Brain
- Query normalization
- Semantic retrieval
- Embeddings
- Ranking
- LLM-based candidate selection
- Semantic caching

### Device Brain
- Troubleshooting extraction
- Structured action generation
- Deeplink mapping
- Schema validation
- Action sequencing
- Validation guard

The LLM does not freely generate Settings deeplinks. Deeplinks are mapped from the supplied validated catalog.

---

## 3. Architecture

```text
                    USER QUERY
                        │
                        ▼
              ┌──────────────────┐
              │  Language Brain  │
              │                  │
              │ Normalization    │
              │ Embeddings       │
              │ Retrieval        │
              │ Ranking / LLM    │
              │ Semantic Cache   │
              └────────┬─────────┘
                       │
                       ▼
              Candidate Scenario
                       │
                       ▼
              ┌──────────────────┐
              │   Device Brain   │
              │                  │
              │ Extraction       │
              │ Validation       │
              │ Deeplinks        │
              │ Sequencing       │
              └────────┬─────────┘
                       │
                       ▼
                 FastAPI REST API
                       │
                       ▼
                 React Frontend
```

---

## 4. Key Features

- Natural-language troubleshooting
- Semantic scenario retrieval
- Structured step-by-step guidance
- Validated Settings deeplinks
- Action categorization
- Semantic / exact-query caching
- LLM-call avoidance for cached responses
- Validation guard against invalid outputs
- Safe failure when no validated path exists
- REST API with structured JSON response

---

## 5. Tech Stack

**Backend**
- Python
- FastAPI
- Pydantic
- Uvicorn

**AI / Retrieval**
- Sentence Transformers
- FAISS
- Embeddings
- Ollama / Qwen 2.5
- Semantic Cache

**Frontend**
- React
- Vite
- JavaScript

**Testing**
- Pytest
- Swagger / OpenAPI

---

## 6. Project Structure

```text
PRISM_GENAI_HACKATHON_Y2026/
├── backend/
├── frontend/
├── data/
├── docs/
│   ├── architecture/
│   ├── api/
│   ├── presentation/
│   └── AI_DISCLOSURE.md
├── requirements.txt
└── README.md
```

---

## 7. Installation & Setup

Clone the repository:

```bash
git clone https://github.com/CommandCipher/PRISM_GENAI_HACKATHON_Y2026.git
cd PRISM_GENAI_HACKATHON_Y2026
```

Create a virtual environment:

```bash
python -m venv .venv
```

### Windows

```bash
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## 8. Run Backend

From the repository root:

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

API:

```text
http://127.0.0.1:8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

---

## 9. Run Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend:

```text
http://localhost:5173
```

---

## 10. API

### Endpoint

```http
POST /api/v1/troubleshoot
```

### Request

```json
{
  "query": "My touchscreen is not responding"
}
```

### Response

```json
{
  "contexts": [
    {
      "goal": "Follow these steps to perform this Touchscreen Issues Troubleshooting",
      "title": "Touchscreen Issues",
      "actions": [
        {
          "actionName": "Factors Affecting Touchscreen Performance",
          "stepGroups": [
            {
              "steps": [
                "Follow the troubleshooting step..."
              ],
              "validationDeeplink": null,
              "actionableDeeplink": null
            }
          ],
          "category": "manual"
        }
      ],
      "score": 0.471
    }
  ]
}
```

If no validated troubleshooting path is available, the system returns a safe failure response instead of inventing one.

---

## 11. Testing

Run from the repository root:

```bash
pytest -q backend/tests
```

Current test suite:

```text
17 passed
```

---

## 12. Team

### CommandCipher

| Member | Role |
|---|---|
| Angad Singh | Device Brain & Core Backend |
| Kavyansh Wadhwa | Language Brain & AI/ML |
| Ananya Singh | Frontend |
| Devam Aggarwal | Presentation / Integration |

---

## Submission

**Theme:** Theme 2 — Smart Guided Troubleshooting Engine

**Final GitHub Tag:**

```text
PRISM_GENAI_HACKATHON_Y2026
```

**APK / SDK:** Not applicable — web frontend + REST API based solution.
