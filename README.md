# ChatCore — AI Customer Support Chatbot Platform

ChatCore is a multi-tenant SaaS platform that crawls websites, indexes content via RAG, and provides an AI chatbot that answers visitor questions using only your website's data.

---

## Features

- **AI Chatbot** — Real-time streaming via WebSocket with source citations. Chat page in dashboard + embeddable widget for external sites.
- **Website Crawler** — Auto-crawl sitemaps/robots.txt/links. Extracts & chunks content for indexing. Fixes: crawler no longer crashes on malformed HTML, task list bug resolved.
- **Multi-Model LLM** — Fallback chain: GPT-4o → Gemini → Claude → OpenRouter (no single API key required).
- **RAG Pipeline** — Hybrid search (dense vector in Qdrant + sparse keyword search in SQL). Chunks saved to SQL so keyword search works even without embedding API keys.
- **Multi-Tenant** — Team management with RBAC (admin, viewer, owner).
- **Analytics** — Sessions, messages, active users, top questions, cost breakdown.
- **Chat Widget** — Floating chat bubble with streaming, markdown rendering, typing indicator, feedback buttons, suggested questions.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 14 (App Router), TypeScript, Tailwind CSS, Recharts |
| **Backend** | Python 3.12, FastAPI, SQLAlchemy (async), Alembic |
| **Database** | PostgreSQL 16 |
| **Vector DB** | Qdrant |
| **Cache / Queue** | Redis 7 |
| **AI Models** | OpenAI GPT-4o, Gemini 2.0 Flash, Claude 3 Sonnet, OpenRouter |
| **Infrastructure** | Docker Compose |

## Quick Start

```bash
# Start all services
docker compose up -d

# Run database migrations
docker compose exec backend sh -c "cd /app && PYTHONPATH=/app alembic upgrade head"

# Access
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/api/docs
```

## Project Structure

```
ChatCore/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # auth, sites, chat, ws, analytics, users, feedback, billing, api_keys, security
│   │   ├── models/          # 16 SQLAlchemy models
│   │   ├── services/        # RAG, crawler, LLM, chunker, vector_store, chat_service, stream_manager, crawl_progress
│   │   ├── core/            # Config, security (JWT)
│   │   ├── auth/            # JWT dependencies, OAuth
│   │   └── utils/           # Logger, rate limiter
│   └── alembic/versions/    # 004 migrations
├── frontend/
│   ├── app/
│   │   ├── auth/            # login, register
│   │   └── dashboard/       # sites, chat, analytics, billing, settings, users, chat-sessions, knowledge, logs
│   └── components/chat/     # ChatWidget (embeddable floating widget)
├── docker-compose.yml
└── infrastructure/          # nginx config
```

## API Endpoints

| Group | Key Endpoints |
|-------|---------------|
| **Auth** | `POST /api/v1/auth/register`, `POST /api/v1/auth/login` |
| **Sites** | `GET/POST /api/v1/sites`, `DELETE /api/v1/sites/{id}`, `GET /api/v1/sites/{id}/progress` |
| **Chat** | `POST /api/v1/chat/`, `WS /api/ws/chat` (streaming) |
| **Analytics** | `GET /api/v1/analytics/usage` |
| **Feedback** | `POST /api/v1/feedback/`, `GET /api/v1/feedback/suggested-questions` |

## Environment Variables

Key env vars in `docker-compose.yml`:

| Variable | Default | Purpose |
|----------|---------|---------|
| `OPENAI_API_KEY` | (optional) | GPT embedding + chat |
| `GEMINI_API_KEY` | (optional) | Gemini fallback |
| `ANTHROPIC_API_KEY` | (optional) | Claude fallback |
| `OPENROUTER_API_KEY` | (optional) | OpenRouter fallback |

All services work with zero API keys — embedding returns zero vectors, LLM falls through to available providers.

## Bug Fixes Applied

| Issue | Fix |
|-------|-----|
| Crawler crashes on `tag.get("class")` when `tag.attrs` is None | Added try/except around class/id checks |
| Crawler `asyncio.wait()` reassigns `tasks` to `set`, breaking `tasks.append()` | Renamed pending set to `pending` |
| Qdrant point ID negative (signed hash) | `abs(hash(...)) % 2^63` |
| Chunks not saved to SQL (sparse search had no data) | Save `DocumentChunk` rows during crawl |
| `remark-gfm` npm package missing | Removed import from chat page |
| WebSocket route `/ws/chat` didn't match frontend `/api/ws/chat` | Added `prefix="/api"` to ws router |
| Column name mismatch: DB `metadata` vs model `meta_data` | Migration 003 renames column |
| `chunk_id NOT NULL` on sources table (sparse search has no chunk_id) | Migration 004 makes it nullable |
| Token expiry causes silent 500 on all API calls | Added error handling in frontend |
| Chat sessions page showed fake data | Rewrote with real analytics |

## Chat Interface

Two UIs available:

1. **Dashboard Chat** (`/dashboard/chat`) — Full-page chat with site selector sidebar, WebSocket streaming, source citations
2. **Embeddable Widget** (`frontend/components/chat/ChatWidget.tsx`) — Floating bubble widget for external websites (requires widget build step for production)

## Deployment

### Docker Compose (Local)
```bash
docker compose up -d
```

After first start:
```bash
docker compose exec backend sh -c "cd /app && PYTHONPATH=/app alembic upgrade head"
```

---

<p align="center">Powered by <strong>Ayax-Khan</strong> — Co-Founder of <a href="https://devssdo.com">Devssdo.com</a></p>

