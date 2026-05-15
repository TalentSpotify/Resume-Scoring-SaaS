# Resume Scoring Application

Automated resume scoring and ranking system that evaluates candidates against job descriptions using a hybrid LLM + ATS approach.

## Architecture

```
┌─────────────┐     ┌──────────────────────┐     ┌──────────┐
│  Next.js UI  │────▶│  FastAPI Backend      │────▶│  S3      │
│  (Port 3000) │     │  (Port 8000)          │     │  Bucket  │
└─────────────┘     │                        │     └──────────┘
                    │  ┌─────────┐ ┌───────┐ │     ┌──────────┐
                    │  │ Parser  │ │ ATS   │ │────▶│  Bedrock │
                    │  │ PyMuPDF │ │ spaCy │ │     │  Claude  │
                    │  │ docx    │ │ Fuzz  │ │     └──────────┘
                    │  └─────────┘ └───────┘ │
                    └──────────────────────────┘
```

## Scoring Methodology

**Hybrid scoring** with configurable weights:
- **LLM Score (65%)** — Bedrock Claude evaluates overall fit, coverage, relevance
- **ATS Keyword (12%)** — spaCy token overlap between JD and resume
- **Skill Fit (10%)** — RapidFuzz matching of required/preferred skills
- **Experience Fit (8%)** — Regex-based YOE extraction and comparison
- **Domain Fit (5%)** — Industry/domain keyword matching

**Auto-filter thresholds:**
- `< 60` → Reject
- `60–80` → Shortlist
- `> 80` → Strong Match

**Fairness:** Scoring ignores name, gender, age, college tier, and photos. Location is considered when the JD specifies a preference.

## Prerequisites

- **AWS credentials** with access to:
  - S3 bucket: `resume-scoring-app-bucket` (ap-south-1)
  - Bedrock model: `anthropic.claude-opus-4-20250514` (ap-south-1)
- Docker & Docker Compose (for containerized run)
- OR Python 3.12+ and Node.js 20+ (for local dev)

## Quick Start (Docker)

```bash
# Clone and start both services
docker-compose up --build

# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
# API docs: http://localhost:8000/docs
```

AWS credentials are mounted from `~/.aws`. Set env vars in `docker-compose.yml` for custom config.

## Local Development

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Run
uvicorn app.main:app --reload --port 8000

# Tests
pytest tests/ -v
```

### Frontend

```bash
cd frontend
npm install

# Run (proxies /api/* to backend on port 8000)
npm run dev

# Build
npm run build
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/upload/presigned-url` | Get S3 presigned upload URL |
| POST | `/api/upload/resumes` | Direct resume upload (fallback) |
| POST | `/api/upload/jd` | Direct JD PDF upload |
| POST | `/api/process` | Score & rank all resumes against JD |
| GET | `/api/runs/{run_id}` | Retrieve full run result |
| GET | `/api/runs/{run_id}/results` | Candidates + summary only |
| GET | `/api/runs/{run_id}/candidate/{id}` | Single candidate detail |

### Process Request

```json
{
  "resume_s3_keys": ["uploads/abc123_resume.pdf"],
  "jd_text": "Senior Software Engineer...",
  "jd_s3_key": null
}
```

### Process Response

```json
{
  "run_id": "a1b2c3d4e5f6",
  "candidates": [
    {
      "candidate_name": "John Doe",
      "rank": 1,
      "overall_score": 82.5,
      "filter_decision": "strong_match",
      "subscores": { ... },
      "matched_requirements": [...],
      "missing_requirements": [...],
      "llm_explanation": "..."
    }
  ],
  "summary_stats": {
    "total_candidates": 5,
    "strong_match_count": 1,
    "shortlist_count": 3,
    "reject_count": 1
  },
  "s3_result_key": "results/a1b2c3d4e5f6/result.json"
}
```

## Configuration

All config is via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_REGION` | `ap-south-1` | AWS region |
| `S3_BUCKET` | `resume-scoring-app-bucket` | S3 bucket name |
| `BEDROCK_MODEL_ID` | `anthropic.claude-opus-4-20250514` | Bedrock model |
| `WEIGHT_LLM` | `0.65` | LLM score weight |
| `WEIGHT_ATS_KEYWORD` | `0.12` | ATS keyword weight |
| `WEIGHT_SKILL_FIT` | `0.10` | Skill fit weight |
| `WEIGHT_EXPERIENCE_FIT` | `0.08` | Experience fit weight |
| `WEIGHT_DOMAIN_FIT` | `0.05` | Domain fit weight |
| `THRESHOLD_REJECT` | `60` | Score below = reject |
| `THRESHOLD_SHORTLIST` | `80` | Score above = strong match |
| `LLM_MAX_RETRIES` | `2` | LLM retry attempts |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed CORS origins |
| `BACKEND_URL` | `http://localhost:8000` | Backend URL (for frontend proxy) |

## Project Structure

```
resume-scoring-app/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI bootstrap
│   │   ├── config.py        # Environment-driven config
│   │   ├── schemas.py       # All Pydantic models
│   │   ├── parser.py        # PDF/DOCX extraction, section detection
│   │   ├── llm.py           # Bedrock Claude via LangChain
│   │   ├── scoring.py       # ATS: keyword, skill, experience, domain
│   │   ├── storage.py       # S3 operations
│   │   ├── pipeline.py      # End-to-end orchestration
│   │   ├── utils.py         # Logging, helpers
│   │   └── api.py           # API routes
│   ├── tests/               # pytest test suite
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── app/                  # Next.js App Router pages
│   ├── components/           # React components
│   ├── lib/                  # Types, API client, utilities
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
└── README.md
```
