# WorkforceAI — Technology Stack Decisions

## Executive Summary

This document evaluates each technology considered for WorkforceAI and provides final recommendations. Technologies are accepted, modified, or rejected based on actual project needs, hackathon timeline (~9 days), and complexity trade-offs.

---

## 1. Frontend

### Recommended: React + TypeScript + Vite + Tailwind CSS + shadcn/ui

| Technology | Decision | Reasoning |
|-----------|----------|-----------|
| **React** | ✅ Accept | Industry standard, vast ecosystem, component-based architecture ideal for dashboards |
| **TypeScript** | ✅ Accept | Type safety reduces bugs, better IDE support, essential for a multi-developer project |
| **Vite** | ✅ Accept | Fastest React dev server, instant HMR, superior DX over CRA/Webpack |
| **Tailwind CSS** | ✅ Accept | Utility-first CSS, rapid prototyping, no context-switching to CSS files |
| **shadcn/ui** | ✅ Add (not in original list) | Pre-built accessible components (tables, forms, dialogs, cards) that dramatically speed up dashboard development. Uses Radix UI primitives + Tailwind. Copy-paste components, not a dependency |

### Alternatives Considered

- **Next.js**: Adds SSR complexity unnecessary for a dashboard SPA. Vite + React is simpler.
- **Vue/Svelte**: React has larger ecosystem and more team familiarity.
- **Material UI / Ant Design**: Heavier than shadcn/ui, harder to customize, larger bundle size.
- **Plain CSS / CSS Modules**: Too slow for hackathon prototyping.

### Frontend Architecture

- **State Management**: Zustand (simpler than Redux, sufficient for this scale) + TanStack Query for server state
- **Routing**: React Router v6
- **Forms**: React Hook Form + Zod validation
- **HTTP Client**: Axios with interceptors for auth
- **Charts**: Recharts (lightweight, React-native charting)

> [!NOTE]
> **Complexity:** Low-Medium
> **Dependencies:** Backend API must be defined first (OpenAPI spec)

---

## 2. Backend

### Recommended: Python + FastAPI + Pydantic v2

| Technology | Decision | Reasoning |
|-----------|----------|-----------|
| **Python** | ✅ Accept | Best ecosystem for AI/ML integration, LangGraph/LangChain compatibility |
| **FastAPI** | ✅ Accept | Async-first, auto-generated OpenAPI docs, Pydantic integration, excellent performance |
| **Pydantic v2** | ✅ Accept | Data validation, settings management, structured LLM outputs, serialization |

### Alternatives Considered

- **Django + DRF**: More batteries-included but heavier, ORM is opinionated, worse async story
- **Flask**: Less structured, no built-in validation, no auto-docs
- **Node.js/Express**: Would work but splits the team across two languages (Python still needed for AI)

### Backend Architecture

- Modular structure with domain-driven packages
- Each module (employees, leave, payroll, etc.) as a separate Python package
- Dependency injection via FastAPI's `Depends()`
- Async handlers for I/O-bound operations
- Synchronous handlers for CPU-bound payroll calculations

> [!NOTE]
> **Complexity:** Medium
> **Dependencies:** Database schema must be defined

---

## 3. Database

### Recommended: PostgreSQL + SQLAlchemy 2.0 + Alembic + pgvector

| Technology | Decision | Reasoning |
|-----------|----------|-----------|
| **PostgreSQL** | ✅ Accept | ACID compliance essential for payroll, JSON support, mature, extensible |
| **SQLAlchemy 2.0** | ✅ Accept | Best Python ORM, 2.0 has modern async support, type-safe queries |
| **Alembic** | ✅ Accept | Database migration tool, essential for schema evolution |
| **pgvector** | ✅ Accept (conditional) | Only if RAG for policy documents is implemented; adds vector similarity search to PostgreSQL without a separate service |

### Alternatives Considered

- **MySQL/MariaDB**: Weaker JSON support, less extensible, no pgvector equivalent
- **MongoDB**: No ACID guarantees for financial data, wrong fit for relational HR data
- **Pinecone/Weaviate/Qdrant**: Overkill for <1000 policy document chunks; adds infrastructure complexity
- **SQLite**: Not suitable for concurrent multi-user access

### Decision on pgvector

- Policy documents will have at most hundreds of text chunks
- pgvector eliminates the need for a separate vector database container
- Keeps infrastructure minimal (single PostgreSQL instance)
- If RAG is deferred to post-MVP, pgvector extension simply isn't activated

> [!NOTE]
> **Complexity:** Low-Medium
> **Dependencies:** Docker for PostgreSQL container

---

## 4. AI / Agent Orchestration

### Recommended: LangGraph + Gemini 2.5 Flash + pgvector (for RAG)

| Technology | Decision | Reasoning |
|-----------|----------|-----------|
| **LangGraph** | ✅ Accept | Best human-in-the-loop support, graph-based workflows map to HR processes, persistent state |
| **Gemini 2.5 Flash** | ✅ Accept (primary LLM) | Cost-effective, large context window, good structured output, free tier for prototyping |
| **OpenAI GPT-4o-mini** | ✅ Accept (fallback) | Strong tool calling, use as fallback if Gemini has issues |
| **Google ADK** | ❌ Reject | Too new (2025), less community support, fewer production case studies, risky for a hackathon |
| **Custom Python orchestration** | ❌ Reject | Would require building state persistence, checkpointing, human-in-the-loop from scratch — too much for 9 days |

### LangGraph Architecture Decision

**Pattern: Supervisor Agent with Specialized Tool Nodes** (NOT separate autonomous agents)

Instead of 8 separate agents, use a single LangGraph supervisor with specialized tools:

```
Supervisor Agent (LangGraph)
├── Communication Tools (parse emails, Slack messages, WhatsApp)
├── Employee Tools (lookup employee, check balance, get history)
├── Policy Tools (search policies, check eligibility, get rules)
├── Leave Tools (create request, calculate impact, check conflicts)
├── Payroll Tools (calculate salary, compute deductions, generate payslip)
├── Payment Tools (prepare payout, check status, reconcile)
└── Notification Tools (send email, send Slack, send WhatsApp)
```

> [!IMPORTANT]
> **Why NOT separate agents:**
> - 8 autonomous agents adds massive complexity for a hackathon
> - Inter-agent communication overhead
> - Harder to debug and demonstrate
> - A single supervisor with tools achieves the same functionality with clearer control flow

### Human-in-the-Loop

- LangGraph's `interrupt()` function pauses the workflow at the HR approval step
- Workflow state is persisted to PostgreSQL via LangGraph's checkpoint system
- When HR makes a decision in the UI, the workflow resumes

### RAG Decision

**Hybrid Approach:**

1. **Structured policies** (leave types, balances, rules) → PostgreSQL tables with direct queries
2. **Unstructured policy documents** (PDF handbooks, Word docs) → chunked, embedded, stored in pgvector
3. AI queries structured data first (fast, deterministic), then RAG for supporting context

> [!TIP]
> **For hackathon MVP:** Start with structured policies only (database tables). Add RAG for uploaded documents as a stretch goal.

### LLM Abstraction

- Abstract LLM calls behind a provider interface
- Switch between Gemini and OpenAI via environment variable
- Use Pydantic models for structured outputs regardless of provider

> [!WARNING]
> **Complexity:** High (LangGraph learning curve)
> **Dependencies:** LLM API keys, PostgreSQL for state persistence

---

## 5. Integrations

### Communication Channels

| Integration | Decision | Priority | Reasoning |
|------------|----------|----------|-----------|
| **In-App Chat** | ✅ Accept | P0 (MVP) | Core feature, no external dependencies |
| **Gmail API** | ✅ Accept | P1 (if time) | Strong demo value, Google OAuth needed |
| **Slack API** | ✅ Accept | P2 (stretch) | Slash commands + webhooks, moderate setup |
| **WhatsApp Business Cloud API** | ⚠️ Defer | P3 (post-hackathon) | Requires Meta Business verification, complex setup, not feasible in 9 days |

### Payment Integration

| Integration | Decision | Priority | Reasoning |
|------------|----------|----------|-----------|
| **PayPal Sandbox (Payouts API)** | ✅ Accept | P0 (MVP) | Required for hackathon, works fully in sandbox |
| **PayPal Production** | ❌ Not feasible | N/A | Domestic INR payouts not supported by PayPal in India |
| **Razorpay / Cashfree** | ⚠️ Architecture only | Post-hackathon | Production Indian payroll; design the abstraction layer now |

### PayPal Integration Details

- Use PayPal REST API v1 Payouts (`/v1/payments/payouts`)
- OAuth 2.0 for authentication
- Sandbox credentials from developer.paypal.com
- Webhooks for payment status tracking
- Idempotency keys to prevent duplicate payments
- Also explore PayPal Agent Toolkit (`@paypal/agent-toolkit`) for agentic commerce angle (hackathon special prize: "Best Use of Agentic Commerce")

> [!NOTE]
> **Complexity:** Medium (PayPal), High (Gmail OAuth), Medium (Slack)
> **Dependencies:** API credentials, OAuth configuration

---

## 6. Infrastructure

### Recommended: Docker + Docker Compose + Redis

| Technology | Decision | Reasoning |
|-----------|----------|-----------|
| **Docker** | ✅ Accept | Consistent environments, required for PostgreSQL, easy deployment |
| **Docker Compose** | ✅ Accept | Multi-container orchestration (API, DB, Redis, frontend) |
| **Redis** | ✅ Accept | Session management, caching, Celery broker (if needed), rate limiting |
| **Celery** | ⚠️ Conditional | Only if async task processing (email polling, batch payroll) can't be handled by FastAPI BackgroundTasks |

### Decision on Celery

- **FastAPI BackgroundTasks** can handle simple async operations (sending notifications, webhook processing)
- **Celery is needed if**: scheduled email polling, batch payroll processing, or long-running payment reconciliation requires dedicated worker processes
- **Recommendation**: Start with FastAPI BackgroundTasks; add Celery only if we hit limitations
- If Celery is added, Redis serves as the message broker

### Docker Compose Services

```yaml
services:
  api:       # FastAPI backend
  frontend:  # React dev server (or Nginx for prod)
  db:        # PostgreSQL + pgvector
  redis:     # Cache + session store + optional Celery broker
  # worker:  # Celery worker (only if needed)
```

> [!NOTE]
> **Complexity:** Low-Medium
> **Dependencies:** Docker Desktop installed

---

## 7. Testing

### Recommended: Pytest + HTTPX + Vitest

| Technology | Decision | Reasoning |
|-----------|----------|-----------|
| **Pytest** | ✅ Accept | Python testing standard, fixtures, parametrize, excellent FastAPI integration |
| **HTTPX** | ✅ Accept | Async HTTP client for testing FastAPI endpoints |
| **Vitest** | ✅ Accept (over Jest) | Native Vite integration, faster than Jest, TypeScript support |
| **React Testing Library** | ✅ Accept | Component testing with user-centric approach |
| **Playwright** | ⚠️ Defer | E2E testing, only if time permits |

### Testing Strategy for Hackathon

- **Must have**: API endpoint tests for critical flows (leave request, payroll, payment)
- **Must have**: Payroll calculation unit tests (deterministic, testable)
- **Nice to have**: Frontend component tests
- **Defer**: E2E tests, load tests

> [!NOTE]
> **Complexity:** Low
> **Dependencies:** None

---

## 8. Final Recommended Stack Summary

```
┌─────────────────────────────────────────────────────┐
│                    FRONTEND                          │
│  React + TypeScript + Vite + Tailwind + shadcn/ui   │
│  Zustand + TanStack Query + React Router + Recharts │
├─────────────────────────────────────────────────────┤
│                    BACKEND                           │
│  Python 3.12 + FastAPI + Pydantic v2 + SQLAlchemy 2 │
│  LangGraph + Gemini 2.5 Flash + Alembic            │
├─────────────────────────────────────────────────────┤
│                  DATA LAYER                          │
│  PostgreSQL 16 + pgvector + Redis                   │
├─────────────────────────────────────────────────────┤
│                INTEGRATIONS                          │
│  PayPal Sandbox API + Gmail API + Slack API          │
├─────────────────────────────────────────────────────┤
│               INFRASTRUCTURE                         │
│  Docker + Docker Compose                             │
├─────────────────────────────────────────────────────┤
│                  TESTING                             │
│  Pytest + HTTPX + Vitest + React Testing Library     │
└─────────────────────────────────────────────────────┘
```

---

## 9. Technologies Explicitly Rejected

| Technology | Reason for Rejection |
|-----------|---------------------|
| Google ADK | Too new, risky for hackathon timeline |
| Custom agent orchestration | Too much boilerplate for 9-day timeline |
| MongoDB | Wrong fit for financial/relational data |
| Pinecone/Weaviate/Qdrant | Overkill for policy document scale |
| Next.js | SSR unnecessary for dashboard SPA |
| Django | Heavier than needed, worse async support |
| WhatsApp (for MVP) | Meta Business verification too complex for timeline |
| Celery (initially) | Start with FastAPI BackgroundTasks, add if needed |
| Playwright (for MVP) | E2E testing deferred to post-hackathon |
