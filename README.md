# ChatCore - AI Website Knowledge Chatbot Platform

Multi-tenant SaaS platform that enables businesses to embed an AI-driven chatbot on their websites. Uses RAG (Retrieval-Augmented Generation) to answer user queries based on website content.

## Architecture

- **Frontend**: Next.js 14 (TypeScript, Tailwind CSS)
- **Backend**: FastAPI (Python 3.12)
- **Database**: PostgreSQL 16
- **Vector DB**: Qdrant
- **Cache/Queue**: Redis
- **Automation**: n8n
- **Infrastructure**: Docker, Kubernetes, AWS

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
├── backend/          # FastAPI backend
├── frontend/         # Next.js frontend
├── n8n/              # n8n workflow templates
├── infrastructure/   # K8s manifests, Terraform
├── database/         # SQL migrations, seeds
├── scripts/          # Utility scripts
├── tests/            # E2E and performance tests
└── .github/          # CI/CD workflows
