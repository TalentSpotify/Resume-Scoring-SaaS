"""
All Pydantic models: upload metadata, parsed resume/JD, scoring, candidate results, run results.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────────────

class FileType(str, Enum):
    pdf = "pdf"
    docx = "docx"


class JdSource(str, Enum):
    text = "text"
    pdf = "pdf"


class FilterDecision(str, Enum):
    reject = "reject"
    shortlist = "shortlist"
    strong_match = "strong_match"


# ── Upload ───────────────────────────────────────────────────────────────────

class UploadedFile(BaseModel):
    filename: str
    s3_key: str
    file_type: FileType
    size_bytes: int


class PresignedUrlRequest(BaseModel):
    filename: str
    content_type: str


class PresignedUrlResponse(BaseModel):
    upload_url: str
    s3_key: str
    fields: dict[str, str] = Field(default_factory=dict)


# ── Parsed Resume ────────────────────────────────────────────────────────────

class ResumeSections(BaseModel):
    summary: str = ""
    education: str = ""
    experience: str = ""
    projects: str = ""
    skills: str = ""
    certifications: str = ""
    achievements: str = ""
    other: str = ""


class ParsedResume(BaseModel):
    candidate_name: str = ""
    raw_text: str = ""
    sections: ResumeSections = Field(default_factory=ResumeSections)
    filename: str = ""
    file_type: FileType = FileType.pdf


# ── Parsed JD ────────────────────────────────────────────────────────────────

class ParsedJD(BaseModel):
    raw_text: str = ""
    role_title: str = ""
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    min_years_experience: int | None = None
    domain: str = ""
    location_preference: str = ""
    responsibilities: list[str] = Field(default_factory=list)
    must_have: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)
    source: JdSource = JdSource.text


# ── LLM Output ───────────────────────────────────────────────────────────────

class LLMScoreOutput(BaseModel):
    overall_score: float = 0
    jd_coverage_score: float = 0
    experience_relevance_score: float = 0
    project_relevance_score: float = 0
    role_fit_score: float = 0
    seniority_fit_score: float = 0
    domain_fit_score: float = 0
    location_fit_score: float = 0
    employability_score: float = 0
    matched_requirements: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    matched_evidence_lines: list[str] = Field(default_factory=list)
    explanation: str = ""
    confidence: float = 0
    classification: FilterDecision = FilterDecision.reject


# ── ATS / Keyword Analysis ───────────────────────────────────────────────────

class KeywordAnalysis(BaseModel):
    matched_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    keyword_score: float = 0
    skill_matched: list[str] = Field(default_factory=list)
    skill_missing: list[str] = Field(default_factory=list)
    skill_score: float = 0
    experience_score: float = 0
    domain_score: float = 0


# ── Sub-scores ───────────────────────────────────────────────────────────────

class SubScores(BaseModel):
    llm_score: float = 0
    keyword_relevance_score: float = 0
    skill_fit_score: float = 0
    experience_fit_score: float = 0
    domain_fit_score: float = 0


# ── Candidate Result ─────────────────────────────────────────────────────────

class CandidateMetadata(BaseModel):
    resume_filename: str = ""
    resume_type: FileType = FileType.pdf
    jd_source: JdSource = JdSource.text
    run_id: str = ""
    timestamp: str = ""


class CandidateResult(BaseModel):
    candidate_name: str = ""
    candidate_id: str = ""
    rank: int = 0
    overall_score: float = 0
    filter_decision: FilterDecision = FilterDecision.reject
    subscores: SubScores = Field(default_factory=SubScores)
    matched_requirements: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    matched_lines: list[str] = Field(default_factory=list)
    evidence_snippets: list[str] = Field(default_factory=list)
    resume_sections: dict[str, str] = Field(default_factory=dict)
    llm_explanation: str = ""
    llm_raw_json: dict[str, Any] = Field(default_factory=dict)
    keyword_analysis: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0
    location_match: str = ""
    metadata: CandidateMetadata = Field(default_factory=CandidateMetadata)


# ── Run Result ───────────────────────────────────────────────────────────────

class RunSummaryStats(BaseModel):
    total_candidates: int = 0
    strong_match_count: int = 0
    shortlist_count: int = 0
    reject_count: int = 0
    avg_score: float = 0
    max_score: float = 0
    min_score: float = 0


class RunResult(BaseModel):
    run_id: str = ""
    jd_text: str = ""
    candidates: list[CandidateResult] = Field(default_factory=list)
    ranking_order: list[str] = Field(default_factory=list)  # candidate_ids in rank order
    summary_stats: RunSummaryStats = Field(default_factory=RunSummaryStats)
    threshold_config: dict[str, float] = Field(default_factory=dict)
    weights_used: dict[str, float] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── API Request / Response ───────────────────────────────────────────────────

class ProcessRequest(BaseModel):
    resume_s3_keys: list[str]
    jd_text: str | None = None
    jd_s3_key: str | None = None


class ProcessResponse(BaseModel):
    run_id: str
    candidates: list[CandidateResult]
    summary_stats: RunSummaryStats
    s3_result_key: str = ""


class ErrorResponse(BaseModel):
    detail: str
    run_id: str | None = None


class HealthResponse(BaseModel):
    status: str = "ok"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
