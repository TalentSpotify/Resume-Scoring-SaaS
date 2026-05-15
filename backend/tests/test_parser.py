"""Tests for resume and JD parsing."""

import pytest
from app.parser import (
    _extract_candidate_name,
    _detect_sections,
    parse_jd,
)
from app.schemas import ResumeSections


class TestCandidateNameExtraction:
    def test_extracts_name_from_first_line(self):
        text = "John Smith\njohn@email.com\n555-1234"
        assert _extract_candidate_name(text) == "John Smith"

    def test_skips_lines_with_digits(self):
        text = "123 Main St\nJane Doe\nSoftware Engineer"
        assert _extract_candidate_name(text) == "Jane Doe"

    def test_returns_unknown_for_no_name(self):
        text = "resume\nskills\nexperience\n12345"
        assert _extract_candidate_name(text) == "Unknown"

    def test_skips_section_headers(self):
        text = "Resume\nMichael Johnson\nSoftware Developer"
        assert _extract_candidate_name(text) == "Michael Johnson"


class TestSectionDetection:
    def test_detects_experience_section(self):
        text = "John Doe\nExperience\nWorked at Google for 5 years\nSkills\nPython, Java"
        sections = _detect_sections(text)
        assert "Google" in sections.experience
        assert "Python" in sections.skills

    def test_detects_education(self):
        text = "Education\nBS Computer Science, MIT 2020\nExperience\nSoftware Engineer"
        sections = _detect_sections(text)
        assert "MIT" in sections.education

    def test_unknown_content_goes_to_other(self):
        text = "Hello world\nSome random text"
        sections = _detect_sections(text)
        assert "Hello world" in sections.other


class TestJDParsing:
    def test_basic_jd_parsing(self):
        jd_text = """Senior Software Engineer
        
We are looking for a Senior Software Engineer with 5+ years of experience.

Location: Bangalore, India

Required Skills:
- Python
- AWS
- Docker

Responsibilities:
- Design and build scalable systems
- Lead a team of engineers

Nice to have:
- Kubernetes experience
- Machine learning background
"""
        jd = parse_jd(text=jd_text)
        assert jd.role_title == "Senior Software Engineer"
        assert jd.min_years_experience == 5
        assert jd.source.value == "text"

    def test_empty_jd_raises(self):
        with pytest.raises(ValueError, match="empty"):
            parse_jd(text="")

    def test_none_jd_raises(self):
        with pytest.raises(ValueError, match="empty"):
            parse_jd(text=None)
