"""Tests for ATS scoring logic."""

import pytest
from app.schemas import ParsedResume, ParsedJD, ResumeSections, FileType, JdSource
from app.scoring import (
    compute_keyword_score,
    compute_skill_score,
    compute_experience_score,
    compute_domain_score,
    compute_ats_scores,
)


def _make_resume(text: str = "", skills: str = "", experience: str = "") -> ParsedResume:
    return ParsedResume(
        candidate_name="Test User",
        raw_text=text,
        sections=ResumeSections(skills=skills, experience=experience),
        filename="test.pdf",
        file_type=FileType.pdf,
    )


def _make_jd(
    required_skills: list[str] | None = None,
    min_years: int | None = None,
    domain: str = "",
) -> ParsedJD:
    return ParsedJD(
        raw_text="Senior Software Engineer role",
        role_title="Senior Software Engineer",
        required_skills=required_skills or [],
        min_years_experience=min_years,
        domain=domain,
        source=JdSource.text,
    )


class TestKeywordScore:
    def test_full_keyword_match(self):
        resume = _make_resume(text="Python AWS Docker Kubernetes")
        jd = _make_jd(required_skills=["Python", "AWS", "Docker"])
        score, matched, missing = compute_keyword_score(resume, jd)
        assert score > 50
        assert len(matched) > 0

    def test_no_keyword_match(self):
        resume = _make_resume(text="Java Spring Boot")
        jd = _make_jd(required_skills=["Python", "AWS", "Docker"])
        score, matched, missing = compute_keyword_score(resume, jd)
        assert len(missing) > 0

    def test_no_jd_keywords_returns_neutral(self):
        resume = _make_resume(text="Python developer")
        jd = _make_jd(required_skills=[])
        score, _, _ = compute_keyword_score(resume, jd)
        assert score == 50.0


class TestSkillScore:
    def test_skill_match(self):
        resume = _make_resume(text="Experienced in Python and AWS", skills="Python, AWS, Docker")
        jd = _make_jd(required_skills=["Python", "AWS"])
        score, matched, missing = compute_skill_score(resume, jd)
        assert score > 70
        assert "Python" in matched

    def test_no_skills_in_jd(self):
        resume = _make_resume(text="Python developer")
        jd = _make_jd(required_skills=[])
        score, _, _ = compute_skill_score(resume, jd)
        assert score == 50.0


class TestExperienceScore:
    def test_meets_requirement(self):
        resume = _make_resume(experience="8 years of software engineering")
        jd = _make_jd(min_years=5)
        score = compute_experience_score(resume, jd)
        assert score >= 70

    def test_below_requirement(self):
        resume = _make_resume(experience="2 years of experience")
        jd = _make_jd(min_years=5)
        score = compute_experience_score(resume, jd)
        assert score < 70

    def test_no_requirement_neutral(self):
        resume = _make_resume(experience="10 years")
        jd = _make_jd(min_years=None)
        score = compute_experience_score(resume, jd)
        assert score == 70.0


class TestDomainScore:
    def test_domain_match(self):
        resume = _make_resume(text="5 years in fintech building payment systems")
        jd = _make_jd(domain="fintech")
        score = compute_domain_score(resume, jd)
        assert score >= 85

    def test_no_domain_neutral(self):
        resume = _make_resume(text="Software engineer")
        jd = _make_jd(domain="")
        score = compute_domain_score(resume, jd)
        assert score == 70.0


class TestATSScoresIntegration:
    def test_produces_keyword_analysis(self):
        resume = _make_resume(
            text="Python developer with 5 years in fintech",
            skills="Python, AWS",
            experience="5 years of software engineering",
        )
        jd = _make_jd(required_skills=["Python", "AWS"], min_years=3, domain="fintech")
        analysis = compute_ats_scores(resume, jd)
        assert analysis.keyword_score >= 0
        assert analysis.skill_score >= 0
        assert analysis.experience_score >= 0
        assert analysis.domain_score >= 0
