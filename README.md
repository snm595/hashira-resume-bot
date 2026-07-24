# AI Resume Screening Telegram Bot

An AI-powered Telegram bot that performs intelligent resume screening, candidate ranking, explainable evaluation, and personalized learning recommendations — entirely inside Telegram.

## Features (Phase 1 — Foundation)

- ✅ Clean Architecture folder structure
- ✅ Configuration from `.env` (Pydantic Settings — no hardcoded secrets)
- ✅ Structured logging with per-module loggers and rotating file handler
- ✅ Telegram bot with `/start`, `/help`, `/reset` commands
- ✅ FastAPI health check endpoint (`GET /api/health`)
- ✅ Single entry point (`python run.py`) runs both services concurrently

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.12 |
| Web Framework | FastAPI |
| Telegram Bot | python-telegram-bot |
| LLM Provider (Primary) | Google Gemini API (google-genai) |
| LLM Provider (Fallback) | OpenRouter (OpenAI-compatible API) |
| PDF Parsing | PyMuPDF |
| DOCX Parsing | python-docx |
| Data Validation | Pydantic v2 |
| HTTP Client | httpx |
| Configuration | python-dotenv + Pydantic Settings |

## Project Structure

```
Hashira Resume Bot/
├── app/
│   ├── __init__.py              # Root application package
│   ├── main.py                  # FastAPI app factory + lifespan
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py            # FastAPI route definitions
│   ├── bot/
│   │   ├── __init__.py
│   │   └── handlers.py          # Telegram command handlers
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py          # Pydantic Settings from .env
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py           # Core Pydantic data models
│   ├── utils/
│   │   ├── __init__.py
│   │   └── logger.py            # Centralized structured logging
│   ├── services/                # Business logic (Phase 2+)
│   ├── parser/                  # Document parsing (Phase 3)
│   ├── normalizer/              # Text normalization (Phase 3)
│   ├── extractor/               # LLM-based extraction (Phase 4)
│   ├── llm/                     # LLM client abstraction (Phase 4)
│   ├── prompts/                 # Prompt templates (Phase 4)
│   ├── scoring/                 # Deterministic scoring (Phase 5)
│   ├── recommendation/          # Course recommendations (Phase 6)
│   ├── ranking/                 # Candidate ranking (Phase 7)
│   └── formatter/               # Telegram output formatting (Phase 7)
├── uploads/                     # Temporary file storage (gitignored)
├── logs/                        # Log file output (gitignored)
├── .env                         # Environment variables (gitignored)
├── .env.example                 # Environment variable template
├── .gitignore
├── requirements.txt             # Pinned dependencies
├── run.py                       # Unified entry point
├── PRD.md                       # Product Requirements Document
└── README.md                    # This file
```

## Setup

### Prerequisites

- Python 3.12+
- A Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- A Google Gemini API Key (from [Google AI Studio](https://aistudio.google.com/apikey))
- (Optional) An OpenRouter API Key for fallback (from [OpenRouter](https://openrouter.ai/keys))

### Installation

```bash
# 1. Navigate to the project directory
cd "Hashira Resume Bot"

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env with your actual TELEGRAM_BOT_TOKEN, GEMINI_API_KEY, and optionally OPENROUTER_API_KEY
```

## How to Run

```bash
# Activate virtual environment
source venv/bin/activate

# Start both FastAPI and Telegram bot
python run.py
```

This will:
1. Start the **FastAPI server** at `http://0.0.0.0:8000`
2. Start the **Telegram bot** in polling mode
3. Both services run concurrently in a single process

### Verify it's working

```bash
# Check API health
curl http://localhost:8000/api/health

# Expected response:
# {"status":"healthy","version":"1.0.0","timestamp":"2024-..."}
```

Then open Telegram and send `/start` to your bot.

## Testing Instructions (Phase 1)

### 1. API Health Check
```bash
curl -s http://localhost:8000/api/health | python -m json.tool
```
Expected: `{"status": "healthy", "version": "1.0.0", ...}`

### 2. Telegram Bot Commands
| Command | Expected Behavior |
|---|---|
| `/start` | Welcome message with usage instructions |
| `/help` | Help text with available commands and limits |
| `/reset` | Confirmation that session was cleared |

### 3. Check Logs
```bash
cat logs/app.log
```
Expected: Startup logs, handler invocation logs.

### 4. OpenAPI Documentation
Visit `http://localhost:8000/docs` for interactive Swagger UI.

## Architecture

```
Telegram ←→ Bot Layer (handlers.py)
                  ↓
            Service Layer (future)
                  ↓
     ┌────────────┼────────────┐
     Parser   Extractor   Scorer
     ↓           ↓           ↓
  Normalizer    LLM      Ranking
                            ↓
                        Formatter → Telegram Response
```

**Key Principle**: Each layer depends only on the layer below it. The bot layer never touches the LLM directly — it goes through services.

## Design Decisions

1. **Pydantic Settings** over `os.getenv()` — type-safe, validated at startup, single source of truth.
2. **In-memory sessions** over database — ephemeral by design (PRD §7: no permanent storage).
3. **Concurrent FastAPI + Bot** — `asyncio.gather()` in single process for MVP simplicity.
4. **Per-module loggers** — independent logging per PRD §16, with rotating file handler.
5. **App factory pattern** — `create_app()` enables testing with fresh instances.
6. **Empty module skeletons** — folder structure matches PRD §9 from day one, ready for future phases.

## Phase Roadmap

| Phase | Description | Status |
|---|---|---|
| 1 | Foundation & Project Skeleton | ✅ Complete |
| 2 | Document Upload & Validation | ⬜ Pending |
| 3 | Document Parsing & Text Normalization | ⬜ Pending |
| 4 | LLM Integration & Information Extraction | ⬜ Pending |
| 5 | Skill Matching & Deterministic Scoring | ⬜ Pending |
| 6 | LLM Evaluation & Course Recommendations | ⬜ Pending |
| 7 | Ranking, Formatting & End-to-End Wiring | ⬜ Pending |
| 8 | Error Handling, Caching & Polish | ⬜ Pending |

## License

Private — Internal Use Only
