"""Tests for Semantic Matching Engine, multi-signal evidence evaluation, and anti-conflation safeguards."""

import pytest
from backend.app.modules.ai_providers.mock_provider import MockEmbeddingProvider
from backend.app.modules.job_descriptions.schemas import ExtractedRequirement, RequirementCategory, RequirementPriority
from backend.app.modules.matching.engine import SemanticMatchingEngine, build_term_regex
from backend.app.modules.matching.schemas import MatchLevel
from backend.app.modules.matching.service import MatchingService
from backend.app.modules.matching.similarity import cosine_similarity
from backend.app.modules.resumes.schemas import (
    EducationItem,
    ProjectItem,
    StructuredResume,
    WorkExperienceItem,
)


def test_cosine_similarity_edge_cases():
    """Verify vector math handles identical, orthogonal, zero, and mismatched vectors."""
    # Identical vectors
    v1 = [0.6, 0.8]
    assert pytest.approx(cosine_similarity(v1, v1), 0.001) == 1.0

    # Orthogonal vectors
    v_a = [1.0, 0.0]
    v_b = [0.0, 1.0]
    assert cosine_similarity(v_a, v_b) == 0.0

    # Mismatched lengths
    assert cosine_similarity([1.0, 2.0], [1.0, 2.0, 3.0]) == 0.0

    # Empty vectors
    assert cosine_similarity([], [1.0]) == 0.0
    assert cosine_similarity([1.0], []) == 0.0

    # Zero magnitude vectors
    assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_strict_term_regex_programming_tokens():
    """Verify regex boundary correctly distinguishes C, C++, C#, Java, JavaScript, and .NET."""
    p_c = build_term_regex("c")
    p_cpp = build_term_regex("c++")
    p_csharp = build_term_regex("c#")
    p_dotnet = build_term_regex(".net")
    p_java = build_term_regex("java")
    p_js = build_term_regex("javascript")

    # C vs C++ vs C#
    cpp_text = "Proficient in C++ and Python."
    assert p_cpp.search(cpp_text) is not None
    assert p_c.search(cpp_text) is None  # Strict boundary prevents 'c' matching 'c++'
    assert p_csharp.search(cpp_text) is None

    c_text = "Experienced in C programming and Linux kernel development."
    assert p_c.search(c_text) is not None
    assert p_cpp.search(c_text) is None

    csharp_text = "Enterprise architecture with C# and .NET 8."
    assert p_csharp.search(csharp_text) is not None
    assert p_dotnet.search(csharp_text) is not None
    assert p_c.search(csharp_text) is None

    # Java vs JavaScript
    java_text = "5 years building backend microservices with Java and Spring."
    assert p_java.search(java_text) is not None
    assert p_js.search(java_text) is None

    js_text = "Frontend engineer using JavaScript, TypeScript, and React."
    assert p_js.search(js_text) is not None
    assert p_java.search(js_text) is None


@pytest.fixture
def mock_candidate_resume() -> StructuredResume:
    """Creates a sample candidate resume with explicit skills, experience, and projects."""
    raw = (
        "Jane Doe - Senior Software Engineer\n"
        "Summary: Experienced backend engineer specializing in distributed systems and cloud infrastructure.\n"
        "Skills: Python, FastAPI, Docker, Kubernetes, PostgreSQL, AWS\n"
        "Experience:\n"
        "Senior Backend Developer at CloudCorp (2021 - Present)\n"
        "- Architected scalable microservices using Python and FastAPI serving 10M daily requests.\n"
        "- Automated container deployments on Kubernetes clusters with AWS EKS.\n"
        "- Optimized PostgreSQL database queries and schemas for high-throughput transactions.\n"
        "Junior Developer at WebCo (2019 - 2021)\n"
        "- Basic knowledge of GraphQL APIs.\n"
        "- Familiar with Redis caching.\n"
    )
    return StructuredResume(
        raw_text=raw,
        summary="Experienced backend engineer specializing in distributed systems and cloud infrastructure.",
        skills=["Python", "FastAPI", "Docker", "Kubernetes", "PostgreSQL", "AWS"],
        work_experiences=[
            WorkExperienceItem(
                company="CloudCorp",
                job_title="Senior Backend Developer",
                start_date="2021",
                end_date="Present",
                highlights=[
                    "Architected scalable microservices using Python and FastAPI serving 10M daily requests.",
                    "Automated container deployments on Kubernetes clusters with AWS EKS.",
                    "Optimized PostgreSQL database queries and schemas for high-throughput transactions.",
                ],
            ),
            WorkExperienceItem(
                company="WebCo",
                job_title="Junior Developer",
                start_date="2019",
                end_date="2021",
                highlights=[
                    "Basic knowledge of GraphQL APIs.",
                    "Familiar with Redis caching.",
                ],
            ),
        ],
        projects=[
            ProjectItem(
                title="Distributed Task Queue",
                description="High performance worker queue built with Python and PostgreSQL.",
                technologies=["Python", "PostgreSQL"],
            )
        ],
        education=[
            EducationItem(
                degree="Bachelor of Science",
                field_of_study="Computer Science",
                institution="Tech University",
                graduation_year="2019",
            )
        ],
    )


@pytest.mark.asyncio
async def test_exact_requirement_matching(mock_candidate_resume: StructuredResume):
    """Verify exact literal requirement matches are classified as MATCHED."""
    engine = SemanticMatchingEngine()
    req = ExtractedRequirement(
        id="req-py",
        text="Strong proficiency in Python development",
        category=RequirementCategory.TECHNICAL_SKILL,
        priority=RequirementPriority.REQUIRED,
        normalized_terms=["python"],
    )

    results = await engine.match_requirements([req], mock_candidate_resume)
    assert len(results) == 1
    match = results[0]

    assert match.requirement_id == "req-py"
    assert match.match_level == MatchLevel.MATCHED
    assert match.signals.exact_match is True
    assert match.signals.combined_score >= 0.90
    assert "python" in [t.lower() for t in match.matched_resume_terms]


@pytest.mark.asyncio
async def test_normalized_requirement_matching(mock_candidate_resume: StructuredResume):
    """Verify alias and synonym variants (e.g. Postgres -> PostgreSQL, K8s -> Kubernetes) match."""
    engine = SemanticMatchingEngine()
    req_postgres = ExtractedRequirement(
        id="req-pg",
        text="Experience with Postgres relational database",
        category=RequirementCategory.TECHNICAL_SKILL,
        priority=RequirementPriority.REQUIRED,
        normalized_terms=["postgres"],  # Synonym for postgresql
    )
    req_k8s = ExtractedRequirement(
        id="req-k8s",
        text="Hands-on container orchestration using K8s",
        category=RequirementCategory.TECHNICAL_SKILL,
        priority=RequirementPriority.REQUIRED,
        normalized_terms=["k8s"],  # Synonym for kubernetes
    )

    results = await engine.match_requirements([req_postgres, req_k8s], mock_candidate_resume)
    assert len(results) == 2

    # Postgres matched via normalized PostgreSQL
    assert results[0].match_level == MatchLevel.MATCHED
    assert results[0].signals.normalized_match is True

    # K8s matched via normalized Kubernetes
    assert results[1].match_level == MatchLevel.MATCHED
    assert results[1].signals.normalized_match is True


@pytest.mark.asyncio
async def test_semantic_similarity_matching(mock_candidate_resume: StructuredResume):
    """Verify semantic embedding alignment when phrasing differs from exact keywords."""
    engine = SemanticMatchingEngine()
    req = ExtractedRequirement(
        id="req-microservices",
        text="Architecting scalable distributed microservices systems",
        category=RequirementCategory.RESPONSIBILITY,
        priority=RequirementPriority.REQUIRED,
        normalized_terms=["microservices", "distributed systems"],
    )

    results = await engine.match_requirements([req], mock_candidate_resume)
    assert len(results) == 1
    match = results[0]

    assert match.match_level == MatchLevel.MATCHED
    assert match.signals.semantic_similarity > 0.40
    assert match.signals.combined_score >= 0.80


@pytest.mark.asyncio
async def test_missing_requirement(mock_candidate_resume: StructuredResume):
    """Verify non-existent skills receive MISSING classification without hallucination."""
    engine = SemanticMatchingEngine()
    req_ruby = ExtractedRequirement(
        id="req-ruby",
        text="Deep expertise in Ruby on Rails development",
        category=RequirementCategory.TECHNICAL_SKILL,
        priority=RequirementPriority.REQUIRED,
        normalized_terms=["ruby", "rails"],
    )

    results = await engine.match_requirements([req_ruby], mock_candidate_resume)
    assert len(results) == 1
    match = results[0]

    assert match.match_level == MatchLevel.MISSING
    assert match.signals.exact_match is False
    assert match.signals.normalized_match is False
    assert match.signals.combined_score < 0.40


@pytest.mark.asyncio
async def test_ambiguous_requirement_detection(mock_candidate_resume: StructuredResume):
    """Verify qualifying hedging phrases (e.g. 'basic knowledge', 'familiar with') result in AMBIGUOUS."""
    engine = SemanticMatchingEngine()
    req_graphql = ExtractedRequirement(
        id="req-gql",
        text="Experience implementing GraphQL APIs",
        category=RequirementCategory.TECHNICAL_SKILL,
        priority=RequirementPriority.REQUIRED,
        normalized_terms=["graphql"],
    )
    req_redis = ExtractedRequirement(
        id="req-redis",
        text="Distributed caching architecture with Redis",
        category=RequirementCategory.TECHNICAL_SKILL,
        priority=RequirementPriority.PREFERRED,
        normalized_terms=["redis"],
    )

    results = await engine.match_requirements([req_graphql, req_redis], mock_candidate_resume)
    assert len(results) == 2

    # Candidate has 'Basic knowledge of GraphQL APIs'
    assert results[0].match_level == MatchLevel.AMBIGUOUS
    assert results[0].signals.combined_score <= 0.50

    # Candidate has 'Familiar with Redis caching'
    assert results[1].match_level == MatchLevel.AMBIGUOUS
    assert results[1].signals.combined_score <= 0.50


@pytest.mark.asyncio
async def test_anti_conflation_unrelated_skills_safeguard():
    """Verify Java candidate is NOT falsely matched for JavaScript requirement."""
    engine = SemanticMatchingEngine()
    java_resume = StructuredResume(
        raw_text="Java developer with 5 years building Spring Boot enterprise services.",
        summary="Java backend engineer.",
        skills=["Java", "Spring Boot", "SQL"],
        work_experiences=[],
        projects=[],
        education=[],
    )

    req_js = ExtractedRequirement(
        id="req-js",
        text="Frontend web development with JavaScript and React",
        category=RequirementCategory.TECHNICAL_SKILL,
        priority=RequirementPriority.REQUIRED,
        normalized_terms=["javascript"],
    )

    results = await engine.match_requirements([req_js], java_resume)
    assert len(results) == 1
    match = results[0]

    # Must NOT match Java for JavaScript
    assert match.match_level == MatchLevel.MISSING
    assert match.signals.exact_match is False
    assert match.signals.normalized_match is False


@pytest.mark.asyncio
async def test_matching_service_integration(mock_candidate_resume: StructuredResume):
    """Verify MatchingService delegates to engine and exposes reproducibility metadata."""
    service = MatchingService()
    meta = service.metadata

    assert "embedding_model" in meta
    assert "embedding_dimension" in meta
    assert meta["matching_version"] == "v1.0.0"

    req = ExtractedRequirement(
        id="req-aws",
        text="Production cloud deployments using AWS",
        category=RequirementCategory.TECHNICAL_SKILL,
        priority=RequirementPriority.REQUIRED,
        normalized_terms=["aws"],
    )

    results = await service.match_requirements([req], mock_candidate_resume)
    assert len(results) == 1
    assert results[0].match_level == MatchLevel.MATCHED
    assert results[0].signals.exact_match is True
