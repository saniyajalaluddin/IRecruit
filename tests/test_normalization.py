"""Unit tests for Skill and Requirement Normalization Engine."""

import pytest
from backend.app.modules.matching.normalizer import SkillNormalizer


@pytest.mark.parametrize(
    "term_a,term_b",
    [
        ("Python", "python"),
        ("Python 3", "python"),
        ("JavaScript", "JS"),
        ("javascript", "es6"),
        ("PostgreSQL", "Postgres"),
        ("PostgreSQL", "pgsql"),
        ("React.js", "React"),
        ("reactjs", "react"),
        ("Node.JS", "nodejs"),
        ("Kubernetes", "k8s"),
        ("Amazon Web Services", "AWS"),
        ("Google Cloud Platform", "gcp"),
        ("Microsoft Azure", "Azure"),
        ("Docker", "containerization"),
        ("CI/CD", "Continuous Integration"),
        ("FastAPI", "fastapi"),
        ("MongoDB", "mongo"),
        ("Golang", "Go"),
        ("C++", "cpp"),
        ("C#", "csharp"),
        (".NET", "dotnet"),
        ("REST API", "restful api"),
        ("Machine Learning", "ML"),
        ("Artificial Intelligence", "AI"),
    ],
)
def test_equivalent_technologies_normalization(term_a, term_b):
    """Verify that common abbreviations and alias variations normalize to equivalent terms."""
    assert SkillNormalizer.are_equivalent(term_a, term_b) is True
    assert SkillNormalizer.canonicalize(term_a) == SkillNormalizer.canonicalize(term_b)


@pytest.mark.parametrize(
    "unrelated_a,unrelated_b",
    [
        ("Java", "JavaScript"),
        ("java", "js"),
        ("C", "C++"),
        ("C", "C#"),
        ("C++", "C#"),
        ("SQL", "NoSQL"),
        ("Python", "R"),
    ],
)
def test_unrelated_technologies_never_conflated(unrelated_a, unrelated_b):
    """Verify that distinct technologies are never incorrectly merged together."""
    assert SkillNormalizer.are_equivalent(unrelated_a, unrelated_b) is False
    assert SkillNormalizer.canonicalize(unrelated_a) != SkillNormalizer.canonicalize(unrelated_b)


def test_list_normalization_and_deduplication():
    """Verify normalizing a list of skills produces canonical, deduplicated forms."""
    raw_skills = ["Python 3", "python", "JS", "JavaScript", "Postgres", "PostgreSQL", "k8s"]
    normalized = SkillNormalizer.normalize_list(raw_skills)
    assert normalized == ["python", "javascript", "postgresql", "kubernetes"]
