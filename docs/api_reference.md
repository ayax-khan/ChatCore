# ChatCore API Reference

## Base URL
`https://api.chatcore.dev/api/v1`

## Authentication
Most endpoints require a Bearer token in the Authorization header.

## Endpoints

### Auth

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register new user/business |
| POST | `/auth/login` | Login, returns JWT |
| POST | `/auth/refresh` | Refresh access token |

### Sites (Knowledge Bases)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/sites/` | List all sites |
| POST | `/sites/` | Add new website |
| GET | `/sites/{id}` | Get site details |
| PATCH | `/sites/{id}` | Update site config |
| DELETE | `/sites/{id}` | Delete site |
| POST | `/sites/{id}/crawl` | Trigger crawl |
| POST | `/sites/{id}/re-crawl` | Full re-crawl |
| GET | `/sites/{id}/history` | Crawl history |

### Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat/` | Send question, get answer |
| WS | `/ws/chat` | WebSocket streaming chat |

### Users & Team

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/users/` | List team members |
| POST | `/users/` | Invite user |
| PATCH | `/users/{id}` | Update user role/status |
| DELETE | `/users/{id}` | Remove user |

### Analytics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/analytics/usage` | Usage metrics (sessions, messages, DAU) |
| GET | `/analytics/errors` | Error logs |
| GET | `/analytics/top-questions` | Frequently asked questions |
| GET | `/analytics/cost-breakdown` | AI cost by model |
| GET | `/analytics/daily` | Daily metrics |

### Feedback & Leads

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/feedback/` | Submit rating |
| POST | `/feedback/lead` | Capture lead |
| GET | `/feedback/suggested-questions` | Get suggested Qs |

### API Keys

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api-keys/` | List API keys |
| POST | `/api-keys/` | Create API key |
| DELETE | `/api-keys/{id}` | Delete API key |

### Billing

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/billing/subscription` | Current subscription |
| GET | `/billing/plans` | All available plans |
| POST | `/billing/upgrade` | Upgrade plan |
| POST | `/billing/payment-method` | Add payment method |

### Security

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/security/oauth/login` | OAuth login |
| POST | `/security/change-password` | Change password |
| POST | `/security/logout` | Logout |
| GET | `/security/sessions` | Active sessions |
| GET | `/security/gdpr/export` | Export personal data |
| POST | `/security/gdpr/delete` | Delete personal data |
| GET | `/security/audit-logs` | Audit trail |

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/healthz` | Health check |
| GET | `/metrics` | Prometheus metrics |
| GET | `/config/theme` | Theme configuration |

## Rate Limiting
- Free: 60 requests/minute
- Starter: 300 requests/minute
- Professional: 1000 requests/minute
- Enterprise: Custom

## WebSocket Chat Protocol

### Connection
`wss://api.chatcore.dev/ws/chat?token={jwt}&session_id={session}&site_id={site_id}`

### Client Messages
```json
{"type": "message", "content": "What is your return policy?"}
{"type": "ping"}
{"type": "close"}
```

### Server Messages
```json
{"type": "token", "content": "Our return policy"}
{"type": "sources", "sources": [{"url": "...", "snippet": "..."}]}
{"type": "confidence", "confidence": 0.95}
{"type": "typing", "content": true}
{"type": "done", "answer": "Full answer..."}
{"type": "error", "content": "Error message"}
{"type": "pong"}
```
