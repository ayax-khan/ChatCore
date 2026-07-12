# ChatCore — AI Customer Support Chatbot Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)](https://docker.com)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-EKS-326CE5)](https://aws.amazon.com/eks)

**ChatCore** is a multi-tenant SaaS platform that lets businesses embed an AI-powered customer support chatbot on their websites. It crawls website content, indexes it using RAG (Retrieval-Augmented Generation), and answers visitor questions in real time.

---

## Features

- **AI Chatbot** — Real-time streaming responses via WebSocket with source citations
- **Website Crawler** — Auto-crawl with sitemap, robots.txt, Playwright for JS sites, incremental updates
- **Multi-Model LLM** — Automatic fallback chain: GPT-4o → GPT-4o-mini → GPT-3.5 → Gemini → Claude → OpenRouter
- **RAG Pipeline** — Hybrid search (dense + sparse) with re-ranking
- **Document Upload** — PDF, DOCX, CSV, Excel parsing
- **Multi-Tenant** — Team management with RBAC (admin, editor, viewer)
- **Analytics** — DAU, top questions, cost breakdown, daily metrics
- **Billing** — Stripe integration with plan-based feature enforcement
- **Security** — JWT with refresh rotation, OAuth (Google/GitHub), rate limiting, GDPR compliance, audit logs
- **Chat Widget** — Floating button, real-time streaming, typing indicator, feedback, lead capture
- **Background Jobs** — Celery for crawling, embedding, email, daily summaries
- **Monitoring** — Prometheus metrics, Sentry error tracking, JSON logging

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 14 (App Router), TypeScript, Tailwind CSS, Recharts |
| **Backend** | Python 3.12, FastAPI, SQLAlchemy (async), Alembic |
| **Database** | PostgreSQL 16 |
| **Vector DB** | Qdrant |
| **Cache / Queue** | Redis 7 |
| **AI Models** | OpenAI GPT-4o, Gemini 2.0 Flash, Claude 3 Sonnet, OpenRouter |
| **Background Jobs** | Celery + Redis |
| **Infrastructure** | Docker Compose, Kubernetes (EKS), Terraform, Helm |
| **CI/CD** | GitHub Actions (test + deploy to EKS) |
| **Monitoring** | Prometheus, Grafana, Loki, Sentry |
| **Automation** | n8n workflows |

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Frontend   │────▶│   Backend    │────▶│  PostgreSQL  │
│  (Next.js)  │     │  (FastAPI)   │     │              │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │                    ▲
                           ▼                    │
                    ┌──────────────┐     ┌─────────────┐
                    │    Redis     │     │   Qdrant    │
                    │ (Cache/Queue)│     │  (Vector DB) │
                    └──────────────┘     └─────────────┘
                           │
                    ┌──────┴───────┐
                    │   Celery     │
                    │  (Workers)   │
                    └──────────────┘
```

## Quick Start

```bash
# Start all services
docker-compose up -d

# Run database migrations
cd backend
alembic upgrade head

# Seed plans
psql -h localhost -U postgres -d chatcore -f ../database/seeds/seed_plans.sql
```

## Project Structure

```
ChatCore/
├── backend/                  # FastAPI backend
│   ├── app/
│   │   ├── api/v1/          # API endpoints (auth, sites, chat, analytics, etc.)
│   │   ├── models/          # SQLAlchemy models (16 tables)
│   │   ├── services/        # Business logic (RAG, crawler, LLM, chunker, etc.)
│   │   ├── core/            # Config, security
│   │   ├── auth/            # JWT dependencies
│   │   ├── utils/           # Logger, rate limiter, sanitizer
│   │   └── tests/           # Unit, integration, E2E, load tests
│   └── alembic/             # Database migrations
├── frontend/                # Next.js 14 frontend
│   ├── app/                 # App Router pages (dashboard, auth, etc.)
│   ├── components/          # ChatWidget, UI components
│   ├── lib/                 # API client
│   ├── context/             # Auth context
│   └── hooks/               # Custom hooks
├── infrastructure/          # K8s manifests, Terraform, Helm, nginx, monitoring
├── n8n/                     # n8n workflow templates
├── database/                # SQL migrations, seed data
├── scripts/                 # Utility scripts
├── docs/                    # API reference, user manual, Postman collection
└── .github/                 # CI/CD workflows

## API Endpoints

| Group | Endpoints |
|-------|-----------|
| **Auth** | `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh` |
| **Sites** | CRUD, crawl, re-crawl, history |
| **Chat** | `POST /chat/`, `WS /ws/chat` (streaming with sources) |
| **Users** | List, invite, update role, remove |
| **Analytics** | Usage, errors, top questions, cost breakdown, daily |
| **Feedback** | Rating, lead capture, suggested questions |
| **API Keys** | Create, list, delete |
| **Billing** | Subscription, plans, upgrade, invoices |
| **Security** | OAuth, change password, GDPR export/delete, audit logs |

## Database Schema

16 tables: `businesses`, `users`, `plans`, `websites`, `website_pages`, `document_chunks`, `chat_sessions`, `messages`, `feedback`, `leads`, `api_keys`, `audit_logs`, `sources`, `subscriptions`, `invoices`, `analytics_events`

## API Documentation

- **Swagger UI**: `https://api.chatcore.dev/api/docs`
- **ReDoc**: `https://api.chatcore.dev/api/redoc`
- **OpenAPI Spec**: `docs/openapi.json`
- **Postman Collection**: `docs/postman_collection.json`
- **API Reference**: `docs/api_reference.md`
- **User Manual**: `docs/user_manual.md`

## Deployment

### Docker Compose (Local)
```bash
docker-compose up -d
```

### Kubernetes (EKS)
```bash
kubectl apply -f infrastructure/k8s/
```

### Helm
```bash
helm install chatcore ./infrastructure/helm/chatcore
```

### Terraform
```bash
cd infrastructure/terraform
terraform init
terraform apply
```

## Testing

```bash
# Backend tests
cd backend
pytest app/tests/ -v

# Frontend tests
cd frontend
npm test
```

## License

[MIT](LICENSE)

---

<p align="center">Powered by <strong>Ayax-Khan</strong> — Co-Founder of <a href="https://devssdo.com">Devssdo.com</a></p>

