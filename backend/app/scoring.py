"""
ATS-style scoring: keyword relevance, skill fit, experience fit, domain fit.
Uses spaCy for NLP, RapidFuzz for fuzzy matching, regex for pattern extraction.
"""

from __future__ import annotations

import logging
import re

import numpy as np
from rapidfuzz import fuzz, process

from app.schemas import KeywordAnalysis, ParsedJD, ParsedResume

logger = logging.getLogger(__name__)

# ── spaCy Lazy Load ──────────────────────────────────────────────────────────

_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        import spacy
        try:
            _nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spaCy model not found, using blank English model")
            _nlp = spacy.blank("en")
    return _nlp


# ── Helpers ──────────────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def _extract_tokens(text: str) -> set[str]:
    """Extract meaningful tokens, filtering stopwords and short tokens."""
    nlp = _get_nlp()
    doc = nlp(text[:100000])  # limit to avoid memory issues
    tokens = set()
    for token in doc:
        if not token.is_stop and not token.is_punct and len(token.text) > 2:
            tokens.add(token.lemma_.lower())
    return tokens


def _fuzzy_match_list(
    needles: list[str], haystack: str, threshold: int = 75
) -> tuple[list[str], list[str]]:
    """
    Match each needle against the haystack using fuzzy matching.
    Returns (matched, missing).
    """
    matched, missing = [], []
    haystack_lower = haystack.lower()
    for needle in needles:
        if not needle.strip():
            continue
        # Exact substring first
        if needle.lower() in haystack_lower:
            matched.append(needle)
            continue
        # Fuzzy match
        score = fuzz.partial_ratio(needle.lower(), haystack_lower)
        if score >= threshold:
            matched.append(needle)
        else:
            missing.append(needle)
    return matched, missing


# ── Keyword Relevance Score ──────────────────────────────────────────────────

def compute_keyword_score(resume: ParsedResume, jd: ParsedJD) -> tuple[float, list[str], list[str]]:
    """
    Compute keyword overlap between JD and resume.
    Returns (score 0-100, matched_keywords, missing_keywords).
    """
    # Combine all JD requirements as keywords
    jd_keywords = set()
    for skill in jd.required_skills + jd.preferred_skills:
        jd_keywords.add(skill.lower().strip())
    for item in jd.must_have + jd.nice_to_have:
        for word in _extract_tokens(item):
            jd_keywords.add(word)
    for resp in jd.responsibilities:
        for word in _extract_tokens(resp):
            jd_keywords.add(word)

    if not jd_keywords:
        return 50.0, [], []  # neutral if no keywords extracted

    resume_text_lower = resume.raw_text.lower()
    resume_tokens = _extract_tokens(resume.raw_text)

    matched = []
    missing = []
    for kw in jd_keywords:
        if kw in resume_text_lower or kw in resume_tokens:
            matched.append(kw)
        else:
            missing.append(kw)

    score = (len(matched) / len(jd_keywords)) * 100 if jd_keywords else 50
    return round(min(score, 100), 2), matched, missing


# ── Skill Fit Score ──────────────────────────────────────────────────────────

def compute_skill_score(resume: ParsedResume, jd: ParsedJD) -> tuple[float, list[str], list[str]]:
    """
    Fuzzy-match JD required + preferred skills against resume text.
    Returns (score 0-100, matched_skills, missing_skills).
    """
    all_skills = jd.required_skills + jd.preferred_skills
    if not all_skills:
        return 50.0, [], []

    resume_text = resume.raw_text + "\n" + resume.sections.skills
    matched, missing = _fuzzy_match_list(all_skills, resume_text, threshold=70)

    # Weight required skills more heavily
    required_count = len(jd.required_skills)
    if required_count > 0:
        required_matched = len([s for s in matched if s in jd.required_skills])
        required_ratio = required_matched / required_count
        total_ratio = len(matched) / len(all_skills) if all_skills else 0
        score = (required_ratio * 0.7 + total_ratio * 0.3) * 100
    else:
        score = (len(matched) / len(all_skills)) * 100 if all_skills else 50

    return round(min(score, 100), 2), matched, missing


# ── Experience Fit Score ─────────────────────────────────────────────────────

_YEARS_RE = re.compile(r"(\d+)\+?\s*(?:years?|yrs?)", re.IGNORECASE)


def compute_experience_score(resume: ParsedResume, jd: ParsedJD) -> float:
    """
    Compare years of experience mentioned in resume vs JD requirement.
    Returns score 0-100.
    """
    if jd.min_years_experience is None:
        return 70.0  # neutral if JD doesn't specify

    # Extract max years mentioned in resume
    experience_text = resume.sections.experience or resume.raw_text
    matches = _YEARS_RE.findall(experience_text)
    resume_years = max((int(m) for m in matches), default=0)

    required = jd.min_years_experience
    if required <= 0:
        return 70.0

    if resume_years >= required:
        return min(100.0, 70.0 + (resume_years / required) * 30)
    else:
        ratio = resume_years / required
        return round(ratio * 70, 2)


# ── Domain Fit Score ─────────────────────────────────────────────────────────

def compute_domain_score(resume: ParsedResume, jd: ParsedJD) -> float:
    """
    Check if the resume mentions the JD's domain.
    Returns score 0-100.
    """
    if not jd.domain:
        return 70.0  # neutral

    resume_lower = resume.raw_text.lower()
    # Direct match
    if jd.domain.lower() in resume_lower:
        return 95.0

    # Fuzzy match
    score = fuzz.partial_ratio(jd.domain.lower(), resume_lower)
    if score >= 80:
        return 85.0
    elif score >= 60:
        return 60.0
    return 30.0


# ── Full ATS Analysis ────────────────────────────────────────────────────────

def compute_ats_scores(resume: ParsedResume, jd: ParsedJD) -> KeywordAnalysis:
    """Run all ATS scoring components and return a unified KeywordAnalysis."""
    keyword_score, matched_kw, missing_kw = compute_keyword_score(resume, jd)
    skill_score, matched_skills, missing_skills = compute_skill_score(resume, jd)
    experience_score = compute_experience_score(resume, jd)
    domain_score = compute_domain_score(resume, jd)

    return KeywordAnalysis(
        matched_keywords=matched_kw,
        missing_keywords=missing_kw,
        keyword_score=keyword_score,
        skill_matched=matched_skills,
        skill_missing=missing_skills,
        skill_score=skill_score,
        experience_score=experience_score,
        domain_score=domain_score,
    )
