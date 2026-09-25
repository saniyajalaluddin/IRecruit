# IRecruit REST API Specification

**Version:** 1.0.0  
**Base URL:** `/api/v1`  
**Protocol:** HTTPS / JSON (multipart/form-data for file uploads)  
**OpenAPI Interactive UI:** `/docs` (Swagger UI), `/redoc` (ReDoc)

---

## 1. Overview & Conventions

The IRecruit API provides deterministic, evidence-grounded resume analysis against job descriptions.

### HTTP Status Codes
- `200 OK`: Request succeeded.
- `201 Created`: Resource successfully created.
- `400 Bad Request`: Invalid payload, unsupported format, or validation failure.
- `401 Unauthorized`: Missing or invalid Bearer token.
- `403 Forbidden`: Resource belongs to another user (Ownership violation) or insufficient role.
- `404 Not Found`: Requested resource does not exist.
- `422 Unprocessable Entity`: Pydantic schema validation error.
- `429 Too Many Requests`: Rate limit threshold exceeded.
- `500 Internal Server Error`: Unexpected server exception.

### Rate Limiting Headers
Every response includes real-time rate limit telemetry headers:
```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 1774526400
```

### Standard Error Response Format
```json
{
  "detail": "Descriptive error message explaining the rejection reason."
}
```

---

## 2. Authentication & Authorization

Protected endpoints require a JSON Web Token (JWT) provided in the HTTP `Authorization` header using the `Bearer` scheme:
```http
Authorization: Bearer <access_token>
```

### 2.1 Register User
- **Method:** `POST`
- **Path:** `/api/v1/auth/register`
- **Auth Required:** No

#### Request Body (`application/json`)
```json
{
  "email": "candidate@example.com",
  "password": "StrongPassword123!",
  "full_name": "Jane Doe"
}
```

#### Response (`201 Created`)
```json
{
  "id": "usr_9b1deb4d3b7d4e89",
  "email": "candidate@example.com",
  "full_name": "Jane Doe",
  "tier": "free",
  "created_at": "2026-09-25T14:30:00Z"
}
```

---

### 2.2 Authenticate / Login
- **Method:** `POST`
- **Path:** `/api/v1/auth/login`
- **Auth Required:** No

#### Request Body (`application/json`)
```json
{
  "email": "candidate@example.com",
  "password": "StrongPassword123!"
}
```

#### Response (`200 OK`)
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "usr_9b1deb4d3b7d4e89",
    "email": "candidate@example.com",
    "full_name": "Jane Doe",
    "tier": "free"
  }
}
```

---

### 2.3 Fetch Current User Profile
- **Method:** `GET`
- **Path:** `/api/v1/auth/me`
- **Auth Required:** Yes (`Bearer <token>`)

#### Response (`200 OK`)
```json
{
  "id": "usr_9b1deb4d3b7d4e89",
  "email": "candidate@example.com",
  "full_name": "Jane Doe",
  "tier": "free",
  "created_at": "2026-09-25T14:30:00Z"
}
```

---

## 3. Resume Management

### 3.1 Upload Resume
- **Method:** `POST`
- **Path:** `/api/v1/resumes/upload`
- **Auth Required:** Yes (`Bearer <token>`)
- **Content-Type:** `multipart/form-data`

#### Form Parameters
- `file`: Binary file payload (`.pdf`, `.docx`, `.txt`). Maximum size: 10 MB.

#### Response (`201 Created`)
```json
{
  "id": "res_a1b2c3d4e5f6",
  "filename": "Jane_Doe_Resume_2026.pdf",
  "file_size": 245120,
  "mime_type": "application/pdf",
  "uploaded_at": "2026-09-25T14:32:00Z",
  "parsed_sections": [
    "Contact Information",
    "Professional Experience",
    "Technical Skills",
    "Education"
  ]
}
```

---

## 4. Job Alignment Analyses

### 4.1 Run Anonymous Analysis
- **Method:** `POST`
- **Path:** `/api/v1/analyses/anonymous`
- **Auth Required:** No (Anonymous users, 24-hour expiration)

#### Request Body (`application/json`)
```json
{
  "resume_text": "Experienced Python Backend Engineer with 5 years in FastAPI, PostgreSQL, Docker, and Redis.",
  "job_description_text": "Senior Python Engineer required with strong FastAPI, PostgreSQL, Docker, and AWS experience."
}
```

#### Response (`200 OK`)
```json
{
  "analysis_id": "an_c0a80101_8a12",
  "status": "completed",
  "overall_score": 85.0,
  "grade": "B+",
  "score_breakdown": {
    "required_competencies": 35.0,
    "experience_depth": 22.0,
    "preferred_competencies": 10.0,
    "domain_alignment": 9.0,
    "education_credentials": 9.0
  },
  "matched_requirements": [
    {
      "requirement": "FastAPI",
      "status": "MATCHED",
      "priority": "REQUIRED",
      "evidence": "5 years in FastAPI",
      "confidence": 1.0
    },
    {
      "requirement": "PostgreSQL",
      "status": "MATCHED",
      "priority": "REQUIRED",
      "evidence": "PostgreSQL, Docker, and Redis",
      "confidence": 1.0
    },
    {
      "requirement": "AWS",
      "status": "MISSING",
      "priority": "PREFERRED",
      "evidence": "No supporting evidence was found in the submitted resume.",
      "confidence": 0.0
    }
  ],
  "ats_compatibility": {
    "score": 95.0,
    "is_ats_friendly": true,
    "issues_detected": []
  },
  "recommendations": [
    {
      "category": "SKILL_GAP",
      "suggestion": "If you have prior cloud deployment experience with AWS, incorporate specific project bullet points reflecting this.",
      "grounded": true
    }
  ]
}
```

---

### 4.2 Claim Anonymous Analysis
- **Method:** `POST`
- **Path:** `/api/v1/analyses/{analysis_id}/claim`
- **Auth Required:** Yes (`Bearer <token>`)

#### Response (`200 OK`)
```json
{
  "analysis_id": "an_c0a80101_8a12",
  "claimed": true,
  "user_id": "usr_9b1deb4d3b7d4e89",
  "claimed_at": "2026-09-25T14:35:00Z"
}
```

---

### 4.3 Get Candidate Dashboard Summary
- **Method:** `GET`
- **Path:** `/api/v1/analyses/dashboard`
- **Auth Required:** Yes (`Bearer <token>`)

#### Response (`200 OK`)
```json
{
  "total_analyses_run": 4,
  "average_score": 82.5,
  "top_missing_skills": [
    {"skill": "Kubernetes", "frequency": 3},
    {"skill": "AWS", "frequency": 2}
  ],
  "recent_analyses": [
    {
      "id": "an_c0a80101_8a12",
      "job_title": "Senior Python Engineer",
      "overall_score": 85.0,
      "grade": "B+",
      "created_at": "2026-09-25T14:30:00Z"
    }
  ]
}
```

---

### 4.4 Get Saved Analyses History
- **Method:** `GET`
- **Path:** `/api/v1/analyses/history`
- **Auth Required:** Yes (`Bearer <token>`)
- **Note:** Free tier users are capped at the latest 5 saved analyses.

#### Response (`200 OK`)
```json
{
  "items": [
    {
      "id": "an_c0a80101_8a12",
      "job_title": "Senior Python Engineer",
      "overall_score": 85.0,
      "grade": "B+",
      "created_at": "2026-09-25T14:30:00Z"
    }
  ],
  "total_count": 1,
  "tier_limit": 5
}
```

---

### 4.5 Get Analysis by ID
- **Method:** `GET`
- **Path:** `/api/v1/analyses/{analysis_id}`
- **Auth Required:** Yes (`Bearer <token>`)
- **Security:** Verifies caller owns the analysis; returns `403 Forbidden` if owned by another user.

#### Response (`200 OK`)
```json
{
  "id": "an_c0a80101_8a12",
  "user_id": "usr_9b1deb4d3b7d4e89",
  "overall_score": 85.0,
  "grade": "B+",
  "status": "completed",
  "created_at": "2026-09-25T14:30:00Z",
  "score_breakdown": {
    "required_competencies": 35.0,
    "experience_depth": 22.0,
    "preferred_competencies": 10.0,
    "domain_alignment": 9.0,
    "education_credentials": 9.0
  },
  "requirements": [
    {
      "text": "FastAPI",
      "priority": "REQUIRED",
      "status": "MATCHED",
      "snippets": ["5 years in FastAPI"]
    }
  ]
}
```

---

### 4.6 Get Reproducibility Metadata
- **Method:** `GET`
- **Path:** `/api/v1/analyses/{analysis_id}/reproducibility`
- **Auth Required:** Yes (`Bearer <token>`)

#### Response (`200 OK`)
```json
{
  "analysis_id": "an_c0a80101_8a12",
  "configuration_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "llm_provider": "local_mock",
  "llm_model": "deterministic-v1",
  "embedding_provider": "sentence_transformers",
  "embedding_model": "all-MiniLM-L6-v2",
  "embedding_version": "v1.0.0",
  "prompt_version": "v1.2.0",
  "scoring_version": "v1.0.0",
  "created_at": "2026-09-25T14:30:00Z",
  "explanation": "Evaluated using deterministic evidence scoring v1.0.0 with prompt v1.2.0 and embedding all-MiniLM-L6-v2."
}
```

---

### 4.7 Delete Analysis
- **Method:** `DELETE`
- **Path:** `/api/v1/analyses/{analysis_id}`
- **Auth Required:** Yes (`Bearer <token>`)

#### Response (`200 OK`)
```json
{
  "success": true,
  "deleted_analysis_id": "an_c0a80101_8a12",
  "message": "Analysis and linked evidence successfully purged."
}
```

---

## 5. Resume Versioning & Comparison

### 5.1 Create Resume Version
- **Method:** `POST`
- **Path:** `/api/v1/resumes/{resume_id}/versions`
- **Auth Required:** Yes (`Bearer <token>`)

#### Request Body (`application/json`)
```json
{
  "raw_text": "Updated resume text including recent Kubernetes and Cloud architecture experience.",
  "notes": "Added cloud certifications and Kubernetes deployment metrics"
}
```

#### Response (`201 Created`)
```json
{
  "status": "success",
  "data": {
    "id": "rv_b4c5d6e7f8",
    "resume_id": "res_a1b2c3d4e5f6",
    "version_number": 2,
    "word_count": 480,
    "created_at": "2026-09-25T14:40:00Z"
  }
}
```

---

### 5.2 Compare Resume Versions
- **Method:** `GET`
- **Path:** `/api/v1/resumes/{resume_id}/compare`
- **Auth Required:** Yes (`Bearer <token>`)
- **Query Parameters:**
  - `base_version` (int, default: 1)
  - `target_version` (int, default: 2)

#### Response (`200 OK`)
```json
{
  "status": "success",
  "data": {
    "resume_id": "res_a1b2c3d4e5f6",
    "base_version_number": 1,
    "target_version_number": 2,
    "score_progression": {
      "base_score": 70.0,
      "target_score": 85.0,
      "delta": 15.0,
      "base_grade": "C+",
      "target_grade": "B+"
    },
    "text_diffs": [
      {
        "change_type": "added",
        "text": "Architected cloud clusters on Kubernetes handling 10M requests daily."
      }
    ]
  }
}
```

---

## 6. System Health & Telemetry

### 6.1 Liveness Probe
- **Method:** `GET`
- **Path:** `/api/v1/health`
- **Auth Required:** No

#### Response (`200 OK`)
```json
{
  "status": "healthy",
  "timestamp": "2026-09-25T14:35:00Z",
  "version": "1.0.0",
  "components": {
    "database": "connected",
    "vector_engine": "ready",
    "scoring_service": "operational"
  }
}
```

---

### 6.2 Observability & Pipeline Metrics
- **Method:** `GET`
- **Path:** `/api/v1/metrics`
- **Auth Required:** No

#### Response (`200 OK`)
```json
{
  "total_requests": 1420,
  "active_users": 38,
  "p95_latency_ms": 182.4,
  "error_rate_percentage": 0.0,
  "average_analysis_time_ms": 245.1
}
```
