# IRecruit — Technical Architecture Blueprint

## 1. System Overview & Philosophy

**IRecruit** is structured as an enterprise-grade **Modular Monolith**. It balances high cohesion within domain modules with loose coupling across system boundaries.

The core philosophical distinction of IRecruit is **deterministic evidence grounding**:
- Machine Learning and Vector Embeddings are utilized to discover candidate evidence.
- Mathematical scoring algorithms calculate objective alignment percentages.
- LLMs provide natural language explanations and targeted phrasing optimizations.
- **The LLM never sets the score, never invents missing competencies, and never operates on raw un-sanitized user input.**

```mermaid
flowchart TD
    Client["Client Browser (Responsive Web UI)"] -->|HTTP / REST| Gateway["FastAPI REST Gateway (/api/v1/)"]

    subgraph Security_Perimeter ["Security & Privacy Perimeter"]
        Gateway --> RateLimiter["Rate Limiter & Throttler"]
        RateLimiter --> Auth["Auth & RBAC (JWT / Passlib)"]
        Auth --> InjectionFilter["Prompt Injection Sanitizer"]
        InjectionFilter --> PIIRedactor["PII Minimization Engine"]
    end

    subgraph Intelligence_Pipeline ["Evidence-Grounded Intelligence Pipeline"]
        PIIRedactor --> DocParser["Document Parser (PDF / DOCX)"]
        DocParser --> Normalizer["Skill Normalizer & Taxonomy Engine"]
        Normalizer --> Matcher["Multi-Signal Semantic Matcher"]
        Matcher --> EvidenceEngine["Evidence Verification Engine"]
        EvidenceEngine --> DeterministicScoring["Deterministic Scoring Engine"]
    end

    subgraph Quality_and_Audit ["Auditing & Reporting"]
        DeterministicScoring --> ATSAudit["ATS Compatibility Audit"]
        DeterministicScoring --> GapEngine["Gap & Recommendation Engine"]
        DeterministicScoring --> ReproEngine["Reproducibility & Hash Tracker"]
    end

    subgraph Persistence ["Persistence & Storage"]
        ReproEngine --> DB[("SQLAlchemy 2.0 Async DB (PostgreSQL / SQLite)")]
        DocParser --> FileStore[("Secure File Storage")]
    end
```

---

## 2. End-to-End Analysis Pipeline

When an analysis is requested, the system executes an automated 7-stage pipeline:

```mermaid
sequenceDiagram
    autonumber
    actor Candidate
    participant API as FastAPI Gateway
    participant Security as Security & PII Shield
    participant Parser as Resume & JD Parsers
    participant Matcher as Semantic Matching Engine
    participant Evidence as Evidence Engine
    participant Scoring as Scoring Service
    participant DB as Async Database

    Candidate->>API: POST /api/v1/analyses/anonymous (Resume + JD)
    API->>Security: Scan Prompt Injection & Redact PII
    Security-->>API: Sanitized, PII-Masked Texts
    API->>Parser: Parse Resume Sections & Extract Prioritized JD Requirements
    Parser-->>API: StructuredResume & ParsedJobDescription
    API->>Matcher: Match Requirements (Exact + Normalized + Vector Cosine)
    Matcher-->>API: List[RequirementMatchResult]
    API->>Evidence: Extract Verbatim Quotes & Classify (MATCHED / PARTIAL / MISSING)
    Evidence-->>API: List[RequirementEvidence]
    API->>Scoring: Calculate Deterministic Alignment Scores (Weights: 40/25/15/10/10)
    Scoring-->>API: AlignmentScoreResult (0–100 Score, Component Breakdown)
    API->>DB: Persist Entities with SHA-256 Configuration Hash
    DB-->>API: Stored Analysis Record
    API-->>Candidate: 200 OK (Score, Evidence Badges, ATS Findings, Recommendations)
```

---

## 3. Database Schema & Entity-Relationship Model

The persistence layer enforces strict referential integrity, foreign key cascades, and ownership partitioning:

```mermaid
erDiagram
    User ||--o{ Resume : owns
    User ||--o{ Analysis : owns
    User ||--o{ AuditEvent : generates
    User ||--o{ UsageRecord : incurs
    Resume ||--|{ ResumeVersion : has
    ResumeVersion ||--o{ Analysis : evaluated_in
    JobDescription ||--o{ Analysis : targets
    Analysis ||--|{ Requirement : specifies
    Analysis ||--|{ Evidence : validates
    Analysis ||--o{ Recommendation : suggests

    User {
        string id PK
        string email UK
        string hashed_password
        string full_name
        string role
        boolean is_active
        datetime created_at
    }

    Resume {
        string id PK
        string user_id FK
        string title
        string original_filename
        string file_path
        integer file_size_bytes
        string content_type
    }

    ResumeVersion {
        string id PK
        string resume_id FK
        integer version_number
        text raw_text
        text pii_masked_text
        json structured_data
    }

    JobDescription {
        string id PK
        string user_id FK
        string title
        string company_name
        text raw_text
        json structured_requirements
    }

    Analysis {
        string id PK
        string user_id FK
        string resume_id FK
        string resume_version_id FK
        string job_description_id FK
        float overall_score
        json component_scores
        json weights
        string scoring_version
        string prompt_version
        string llm_provider
        string llm_model
        string embedding_provider
        string embedding_model
        string embedding_version
        float execution_duration_ms
        boolean is_anonymous
        string session_id
    }

    Evidence {
        string id PK
        string analysis_id FK
        string requirement_id FK
        string classification
        text quote
        float confidence
        json context_metadata
    }
```

---

## 4. Provider-Agnostic AI Architecture

Domain services depend strictly on abstract provider protocols (`BaseLLMProvider` and `BaseEmbeddingProvider`). This architecture decouples business logic from specific vendors:

- **Factory Pattern**: `get_llm_provider()` and `get_embedding_provider()` resolve implementations dynamically based on environment configuration (`LLM_PROVIDER=openai`, `LLM_PROVIDER=ollama`, or `LLM_PROVIDER=mock`).
- **Zero API Key Leakage**: Keys are read strictly via Pydantic settings from isolated environment variables.
- **Circuit Breaking & Fallbacks**: Graceful fallback to deterministic heuristics if an external provider suffers network timeouts or rate limits.

---

## 5. Security Posture & Threat Model (STRIDE)

| Threat Category | Specific Threat | System Mitigation |
| :--- | :--- | :--- |
| **Spoofing** | Unauthorized access to user reports | JWT Bearer authentication with 30-minute expiry; session validation. |
| **Tampering** | Prompt injection altering alignment scores | Input sanitization using `PromptInjectionDetector`; deterministic scoring bypassing LLM outputs. |
| **Repudiation** | Denying analysis deletion or data access | Immutable `AuditEvent` logs tracking user ID, IP address, timestamp, and resource ID. |
| **Information Disclosure** | Leakage of candidate PII in logs or LLM payloads | Automated `PIIService` redaction of SSNs, credit cards, phones, and addresses prior to external tokenization. |
| **Denial of Service** | Resource exhaustion via massive file uploads or rapid requests | Strict 10MB file limit; MIME sniffing; sliding-window token bucket `RateLimiter`. |
| **Elevation of Privilege** | Cross-tenant analysis manipulation | Row-level ownership verification (`verify_analysis_ownership`) on all read/write endpoints. |

---

## 6. Reproducibility & Model Tracking

Every generated analysis calculates a deterministic SHA-256 configuration signature:
$$\text{Signature} = \text{SHA256}(\text{provider} : \text{model} \parallel \text{embedder} : \text{embedder\_model} : \text{version} \parallel \text{prompt\_version} \parallel \text{scoring\_version})$$

This signature guarantees that any audit can verify the exact configuration that produced a historical report.
