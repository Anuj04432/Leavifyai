# WorkforceAI – System Architecture

## 1. Architecture Overview

WorkforceAI is architected as a **Modular Monolith** with clean domain-driven boundaries, an asynchronous event/intake pipeline, and an agentic AI supervisor orchestration layer.

### Architectural Philosophy
1. **Separation of Concerns**: Business domain logic (leave, payroll, HR records) is kept decoupled from external interfaces (channels, payment gateways).
2. **Deterministic Financial & Approval Core**: All leave balance reductions, payroll calculations, authorization gates, and payment executions are 100% deterministic code governed by strict RBAC and database transactions.
3. **AI as Advisor & Orchestrator**: The AI agents parse unstructured communication, evaluate policy constraints, generate transparent recommendations with source citations, and prepare payloads for human authorization. The AI never possesses direct write privileges for financial transfers or auto-approvals.
4. **Provider-Agnostic Design**: Payment and communication interfaces use abstract strategy patterns, allowing seamless swapping between PayPal Sandbox (hackathon) and domestic payout rails (production India: RazorpayX/Cashfree).

---

## 2. High-Level Architecture Diagram

```mermaid
flowchart TB
    subgraph Clients["Client Layer"]
        EmployeeWeb["Employee Web Portal (React + Vite)"]
        HRWeb["HR & Admin Operations Console (React + Vite)"]
        Gmail["Gmail (Inbound/Outbound)"]
        Slack["Slack Bot / Slash Commands"]
        WhatsApp["WhatsApp Cloud API (Planned)"]
    end

    subgraph Gateway["API & Ingestion Layer (FastAPI)"]
        API["FastAPI REST & WebSocket Gateway"]
        AuthMiddleware["JWT Authentication & RBAC Engine"]
        WebhookReceiver["External Webhook Ingestion Engine"]
        RateLimiter["Rate Limiter & Input Sanitizer"]
    end

    subgraph CoreEngine["Modular Application Core"]
        EmpModule["Employee & Org Module"]
        LeaveModule["Leave Management Module"]
        PolicyModule["Policy & Rules Engine"]
        PayrollModule["Deterministic Payroll Engine"]
        PaymentModule["Payment Orchestration Abstraction"]
        CommModule["Multi-Channel Communication Normalizer"]
        AuditModule["Immutable Audit Logger"]
    end

    subgraph AIAgent["Agentic AI Orchestration (LangGraph + Gemini 2.5 Flash)"]
        Supervisor["Supervisor Orchestration Agent"]
        ParserNode["Message Parser & Identity Resolver"]
        PolicyRAGNode["Policy Citation & Evaluation Node"]
        RecommendationNode["Leave & Action Recommender"]
        HITLGate["Human-In-The-Loop Checkpoint Gate"]
    end

    subgraph DataStorage["Data & State Persistence Layer"]
        Postgres[("PostgreSQL 16 (ACID Relational Core)")]
        PgVector[("pgvector (Policy Document Embeddings)")]
        RedisDB[("Redis 7 (Session Cache, Token Blacklist, Task Queue)")]
        DocStore["Encrypted Object/Document Storage"]
    end

    subgraph Integrations["External Service Integrations"]
        GeminiAPI["Google Gemini 2.5 Flash API"]
        PayPalAPI["PayPal Sandbox (Payouts & OAuth REST API)"]
        GoogleAPI["Google Workspace / Gmail API"]
        SlackAPI["Slack Bolt / Web API"]
    end

    Clients --> Gateway
    Gateway --> AuthMiddleware
    AuthMiddleware --> CoreEngine
    CoreEngine <--> AIAgent
    AIAgent --> GeminiAPI
    CoreEngine --> DataStorage
    AIAgent --> PgVector
    PaymentModule --> PayPalAPI
    CommModule --> GoogleAPI
    CommModule --> SlackAPI
```

---

## 3. Frontend Architecture

### 3.1 Technology Stack & Organization
- **Framework**: React 18+ with TypeScript
- **Bundler & Tooling**: Vite (lightning HMR, minimal config)
- **Styling**: Tailwind CSS + shadcn/ui (Radix UI primitives)
- **State Management**:
  - Server state: TanStack Query (React Query v5) for automatic caching, revalidation, and optimistic mutations.
  - Client state: Zustand for lightweight UI state (sidebar toggles, active modals, notification drawers).
- **Routing**: React Router v6 with layout routes, role-based route guards (`AdminRoute`, `HRRoute`, `EmployeeRoute`).
- **Data Visualization**: Recharts for payroll trends, leave utilization, and channel analytics.

### 3.2 Portal Segregation

```mermaid
flowchart TD
    App["WorkforceAI Single Page Application"]
    App --> AuthGate{"Role Gate (JWT)"}
    
    AuthGate -->|Role: Employee| EmpPortal["Employee Portal View"]
    AuthGate -->|Role: HR / Manager| HRConsole["HR Operations Console"]
    AuthGate -->|Role: System Admin| AdminConsole["Admin Settings & Audit Console"]

    subgraph EmpPortalViews["Employee Portal Features"]
        EmpProfile["Profile & Employment Info"]
        EmpLeaves["Leave Balances & History"]
        EmpRequest["Interactive Leave Application Modal"]
        EmpChat["Embedded HR AI Assistant Widget"]
        EmpPayslips["Payslips & Payment History Explorer"]
    end

    subgraph HRConsoleViews["HR Management Features"]
        HRRoster["Employee Directory & Roster Management"]
        HRImport["CSV/Excel Bulk Import Engine"]
        HRApprovals["Unified Request Approval Queue (AI Insights)"]
        HRPolicyConfig["Company Leave Policy Configuration"]
        HRPayroll["Payroll Period Runner & Adjustment Review"]
        HRPayout["Batch Payout Trigger (PayPal Sandbox)"]
    end

    subgraph AdminConsoleViews["Admin Features"]
        AdminUsers["User Role Assignment & Security"]
        AdminIntegrations["API Keys & Channel Config"]
        AdminAudit["Audit Trail & System Health Telemetry"]
    end

    EmpPortal --> EmpPortalViews
    HRConsole --> HRConsoleViews
    AdminConsole --> AdminConsoleViews
```

---

## 4. Backend Modular Architecture

The FastAPI application follows a strictly modular package layout structured around domain boundaries:

```
backend/
├── app/
│   ├── main.py                  # Application factory, lifespan, CORS, middleware
│   ├── config.py                # Pydantic BaseSettings (validated environment variables)
│   ├── database.py              # SQLAlchemy 2.0 AsyncEngine & sessionmaker
│   ├── dependencies.py          # Shared FastAPI dependency injections
│   ├── common/
│   │   ├── exceptions.py        # Centralized HTTP & business error hierarchy
│   │   ├── security.py          # Password hashing (Argon2/Bcrypt) & JWT creation/verification
│   │   └── pagination.py        # Standardized cursor & offset paginators
│   ├── modules/
│   │   ├── auth/                # Sign-in, token refresh, password recovery
│   │   ├── employees/           # Profile CRUD, CSV/Excel ingestion, manager hierarchy
│   │   ├── leave/               # Leave request lifecycle, balance calculations, calendars
│   │   ├── policies/            # Leave rule definitions, eligibility conditions, document indexing
│   │   ├── payroll/             # Deterministic salary calculation, period batches, deductions
│   │   ├── payments/            # Payout provider abstraction layer & PayPal adapter
│   │   ├── communication/       # Inbound multi-channel normalizer & outbound dispatchers
│   │   ├── agents/              # LangGraph workflow graphs, node logic, tools, LLM prompts
│   │   ├── notifications/       # Multi-channel notification delivery service
│   │   └── analytics/           # High-speed aggregated metrics queries
│   └── models/                  # Declarative SQLAlchemy models
└── alembic/                     # Database schema migrations
```

---

## 5. Agent Orchestration Architecture

### 5.1 Architecture Decision: Central Supervisor with Specialized Tools
Instead of multiple uncoordinated autonomous agents (which create high latency, race conditions, and debugging nightmares), WorkforceAI uses a **Hierarchical Supervisor Agent Workflow** modeled in **LangGraph**.

```mermaid
stateDiagram-v2
    [*] --> InboundIntake
    InboundIntake --> IdentityResolution: Normalized Message Payload
    
    IdentityResolution --> IntentClassifier: Employee Verified
    IdentityResolution --> UnknownSenderRejection: Verification Failed
    
    state IntentClassifier {
        [*] --> Classify
        Classify --> LeaveRequestFlow: Intent = Leave Request
        Classify --> PolicyInquiryFlow: Intent = Policy Question
        Classify --> PayrollInquiryFlow: Intent = Salary/Payslip Query
        Classify --> GeneralHRFlow: Intent = General Query
    }

    state LeaveRequestFlow {
        [*] --> EntityExtraction: Extract Dates, Type, Reason
        EntityExtraction --> BalanceCheckTool: Query Remaining Days
        BalanceCheckTool --> PolicyEvaluationTool: Check Tenure, Overlap, Max Days
        PolicyEvaluationTool --> RecommendationSynthesis: Format Reasoned Suggestion
        RecommendationSynthesis --> CreateDraftRequest: Insert DB Record (status=pending)
    }

    CreateDraftRequest --> HumanInTheLoopInterrupt: Pause Graph Execution

    state HumanInTheLoopInterrupt {
        [*] --> AwaitingHRDecision: Present to HR with AI Context & Citations
        AwaitingHRDecision --> HRApproved: HR Clicks 'Approve'
        AwaitingHRDecision --> HRRejected: HR Clicks 'Reject'
        AwaitingHRDecision --> HRClarification: HR Clicks 'Request Info'
    }

    HRApproved --> StateResume: Resume Graph
    HRRejected --> StateResume: Resume Graph
    HRClarification --> StateResume: Resume Graph

    StateResume --> PostDecisionDispatcher: Update Balance & Notify
    PostDecisionDispatcher --> DispatchResponse: Route to Source Channel (Email/Slack/App)
    DispatchResponse --> [*]
```

### 5.2 Key Design Principles for AI
1. **Pydantic Structured Output Enforcement**: All LLM entity extractions (start date, end date, leave category, reason) use strict JSON schema validation. If extraction fails validation, the agent triggers a clarification prompt instead of guessing.
2. **Deterministic Rules Validation Prior to AI Recommendation**:
   - The balance check is performed by a SQL query: `available = total_allocated + carried_forward - used - pending`.
   - The AI receives this exact number as context; it does not compute math itself.
3. **Transparent Policy Citation**: Every recommendation includes:
   - Recommended Action (`APPROVE`, `REJECT`, `REFER_TO_MANAGER`).
   - Confidence Score (`0.00` to `1.00`).
   - Specific Policy Clause Reference (e.g., *"Section 3.2: Casual leave requires 24h advance notice"*).
   - Expected Salary Impact (e.g., *"0 INR deduction; covered under paid balance"*).

---

## 6. Multi-Channel Communication Architecture

The communication module guarantees that employees can interact via their preferred tool, while HR manages everything from a single cockpit.

```mermaid
sequenceDiagram
    autonumber
    actor Employee
    participant Channel as Communication Channel (Gmail / Slack)
    participant Normalizer as Channel Inbound Adapter
    participant CommEvent as communication_events Table
    participant Agent as LangGraph Orchestrator
    participant CoreDB as PostgreSQL Database
    actor HR as HR Manager
    participant Outbound as Outbound Dispatcher

    Employee->>Channel: "Need 2 days leave this Thursday and Friday for family wedding"
    Channel->>Normalizer: Webhook Event / Polling Ingestion
    Normalizer->>CommEvent: Record raw payload (status='received')
    Normalizer->>Normalizer: Match sender identifier against employee records
    Normalizer->>Agent: Pass normalized message context
    Agent->>CoreDB: Verify leave balance & policy rules
    Agent->>CoreDB: Create leave_requests record (status='pending', source_channel='email')
    Agent->>CommEvent: Update event (status='processed', ai_extracted_data)
    CoreDB-->>HR: Real-time WebSocket event pushes to HR Approval Queue
    
    Note over HR: HR reviews AI recommendation & policy citation
    HR->>CoreDB: Authorize approval with comment: "Approved. Enjoy!"
    
    CoreDB->>Outbound: Trigger decision notification
    Outbound->>Channel: Send formatted message response to original thread
    Channel->>Employee: "Your leave for Nov 6 - Nov 7 has been approved by HR."
```

---

## 7. Policy Document Processing and RAG Architecture

```mermaid
flowchart LR
    subgraph DocumentIngestion["Policy Document Ingestion"]
        Upload["HR Uploads PDF / DOCX / TXT"] --> Parser["Document Parser & Text Extractor"]
        Parser --> Chunker["Semantic Chunker (500 tokens, 10% overlap)"]
        Chunker --> Embedder["Gemini Text-Embedding-004"]
        Embedder --> VectorStore[("PostgreSQL pgvector Table")]
    end

    subgraph QueryExecution["Policy Query & Validation"]
        UserQuery["Employee Message or Leave Query"] --> QueryEmbedding["Embed Query"]
        QueryEmbedding --> SimilaritySearch["Cosine Similarity Search (HNSW index)"]
        VectorStore --> SimilaritySearch
        SimilaritySearch --> ContextRerank["Top 3 Policy Snippets"]
        ContextRerank --> LLMEval["LLM Policy Evaluation Node"]
    end
```

### Hybrid Policy Lookup Strategy
- **Structured Policy Engine**: Exact numeric rules (e.g., max consecutive days, notice period, annual allocation) are stored as typed columns in `leave_policies` and evaluated using deterministic code logic.
- **pgvector Semantic Search**: Nuanced exceptions, definitions, and handbook rules (e.g., bereavement eligibility, bereavement degrees of relationship, maternity benefits prerequisites) are queried via vector similarity search.
- **Result**: 100% precision on numeric validation + flexible natural language understanding for unstructured clauses.

---

## 8. Deterministic Payroll Calculation Architecture

Financial calculations must **never** be delegated to generative AI models.

```mermaid
flowchart TD
    StartPayroll["HR Initiates Monthly Payroll Run (e.g., Nov 2026)"] --> FetchEmployees["Query Active Employees & Base Salaries"]
    FetchEmployees --> FetchApprovedLeaves["Query Approved Leaves in Period"]
    
    subgraph CalculationLoop["Deterministic Per-Employee Calculation Engine"]
        CalcGross["Gross Salary = Base Salary + Fixed Allowances"]
        CountLeaves["Count Approved Paid Days vs Unpaid Days"]
        CalcUnpaidDeduction["Unpaid Deduction = (Base Salary / Total Working Days) * Unpaid Days"]
        CalcAdjustments["Apply Approved Adjustments (Bonuses, Overtime, Arrears)"]
        CalcStatutory["Calculate Statutory Deductions (TDS, PF, ESI if configured)"]
        CalcNet["Net Salary = Gross - Unpaid Deduction - Statutory - Other Deductions"]
    end

    CalculationLoop --> ValidateTotals{"Integrity Check: Net > 0?"}
    ValidateTotals -->|Yes| InsertBatchItem["Create payroll_items Record (status='calculated')"]
    ValidateTotals -->|No / Anomaly| FlagForReview["Flag Item with WARNING in Batch"]

    InsertBatchItem --> CreateBatchRecord["Update payroll_batches (status='calculated')"]
    FlagForReview --> CreateBatchRecord

    CreateBatchRecord --> HRReview["HR Reviews Batch Breakdown & Variance Diff"]
    HRReview --> HRApprovalAction{"HR Approval?"}
    HRApprovalAction -->|Approved| LockBatch["Lock Batch & Transition status='approved'"]
    HRApprovalAction -->|Adjust Needed| EditAdjustment["HR Adds Manual Adjustment & Recalculates"]
    EditAdjustment --> CalculationLoop
```

---

## 9. Payment Gateway Abstraction & PayPal Architecture

### 9.1 Provider Strategy Pattern
To support both the **PayPal Sandbox Hackathon Demonstration** and **Production Domestic Indian Payroll (RazorpayX / Cashfree)**, all payments are managed via an abstract interface:

```python
# Interface specification
class BasePaymentProvider(ABC):
    @abstractmethod
    async def create_payout_batch(self, batch_id: UUID, payouts: list[PayoutRecipient]) -> PayoutBatchResponse:
        pass

    @abstractmethod
    async def get_payout_status(self, provider_batch_id: str) -> PayoutBatchStatus:
        pass

    @abstractmethod
    async def verify_webhook_signature(self, headers: dict, raw_body: bytes) -> bool:
        pass
```

### 9.2 PayPal Sandbox Implementation Flow

```mermaid
sequenceDiagram
    autonumber
    actor HR as Authorized HR / Admin
    participant App as Payroll Service
    participant Adapter as PayPalPayoutsAdapter
    participant PayPal as PayPal Sandbox REST API
    participant WebhookEndpoint as FastAPI Webhook Handler
    participant DB as PostgreSQL DB

    HR->>App: Click 'Execute Batch Payout'
    App->>DB: Lock payroll batch (status='processing')
    App->>Adapter: Dispatch approved payroll items
    Adapter->>Adapter: Generate deterministic UUID idempotency keys
    Adapter->>PayPal: POST /v1/oauth2/token (Retrieve Bearer Token)
    Adapter->>PayPal: POST /v1/payments/payouts (Batch of items)
    PayPal-->>Adapter: 201 Created (batch_status='PENDING', payout_batch_id)
    Adapter->>DB: Insert payments records (status='processing', idempotency_key)
    
    Note over PayPal: PayPal processes asynchronous transactions in Sandbox
    
    PayPal->>WebhookEndpoint: POST Webhook (PAYMENT.PAYOUTS-ITEM.SUCCEEDED)
    WebhookEndpoint->>PayPal: POST /v1/notifications/verify-webhook-signature
    PayPal-->>WebhookEndpoint: 200 OK (verification_status='SUCCESS')
    WebhookEndpoint->>DB: Update payments item (status='success', paid_at=NOW())
    WebhookEndpoint->>DB: Check if all batch items complete -> Update payroll_batches (status='paid')
    DB-->>HR: Push real-time completion banner via WebSocket
```

---

## 10. Container & Deployment Architecture

```mermaid
flowchart TD
    subgraph DockerComposeHost["Docker Compose Environment"]
        subgraph FrontendContainer["frontend (Container)"]
            Nginx["Nginx / Vite Web Server (Port 3000)"]
        end

        subgraph BackendContainer["api (Container)"]
            Uvicorn["Uvicorn Async Worker Server (Port 8000)"]
            FastAPIApp["FastAPI Application Core"]
            Uvicorn --> FastAPIApp
        end

        subgraph DBContainer["db (Container)"]
            PG16["PostgreSQL 16 Engine"]
            PGVectorExt["pgvector Extension Active"]
            PG16 --- PGVectorExt
        end

        subgraph CacheContainer["redis (Container)"]
            RedisEngine["Redis 7 In-Memory Store (Port 6379)"]
        end

        subgraph StorageVol["Named Volumes"]
            PGData[("pgdata Volume")]
            UploadsData[("uploads Volume")]
        end
    end

    Nginx -->|Reverse Proxy /api| Uvicorn
    FastAPIApp -->|asyncpg / SQLAlchemy| PG16
    FastAPIApp -->|redis-py| RedisEngine
    FastAPIApp -->|File I/O| UploadsData
    PG16 --- PGData
```

---

## 11. Architectural Summary & Non-Functional Attributes

| Attribute | Architectural Guarantee | Mechanism |
|-----------|-------------------------|-----------|
| **Data Integrity** | Strict ACID Compliance | PostgreSQL 16 relational engine with foreign keys and check constraints |
| **Financial Accuracy** | Zero floating-point rounding errors | Arbitrary-precision `DECIMAL(12, 2)` throughout DB and Python `Decimal` |
| **Payment Idempotency** | No duplicate payouts under any failure mode | Unique `idempotency_key` constraint + PayPal `PayPal-Request-Id` |
| **AI Reliability** | No hallucinations in DB mutations | Pydantic constrained schemas + LangGraph HITL approval gates |
| **Observability** | Full forensic audit trail | `audit_logs` table tracking user ID, IP, entity type, before/after diffs |
| **Security & Privacy** | Least privilege access | JWT + Role-Based Access Control on every API route + document classification |
