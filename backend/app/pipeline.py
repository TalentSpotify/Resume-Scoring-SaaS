"""
End-to-end pipeline: parse → score → rank → filter → aggregate → persist.
Orchestrates all modules into a single run.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from app.config import config
from app.llm import score_resume_with_llm
from app.parser import parse_jd, parse_resume
from app.schemas import (
    CandidateMetadata,
    CandidateResult,
    FileType,
    FilterDecision,
    JdSource,
    ParsedJD,
    ParsedResume,
    ProcessResponse,
    RunResult,
    RunSummaryStats,
    SubScores,
)
from app.scoring import compute_ats_scores
from app.storage import download_file, save_run_result

logger = logging.getLogger(__name__)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _detect_file_type(filename: str) -> FileType:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return FileType.pdf
    elif lower.endswith(".docx"):
        return FileType.docx
    raise ValueError(f"Unsupported file type: {filename}")


def _apply_filter(score: float) -> FilterDecision:
    if score >= config.thresholds.shortlist_below:
        return FilterDecision.strong_match
    elif score >= config.thresholds.reject_below:
        return FilterDecision.shortlist
    return FilterDecision.reject


def _compute_weighted_score(
    llm_score: float,
    keyword_score: float,
    skill_score: float,
    experience_score: float,
    domain_score: float,
) -> float:
    w = config.weights
    total = (
        llm_score * w.llm
        + keyword_score * w.ats_keyword
        + skill_score * w.skill_fit
        + experience_score * w.experience_fit
        + domain_score * w.domain_fit
    )
    return round(total, 2)


# ── Score a Single Candidate ─────────────────────────────────────────────────

def _score_candidate(
    resume: ParsedResume,
    jd: ParsedJD,
    run_id: str,
) -> CandidateResult:
    candidate_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now(timezone.utc).isoformat()

    # ATS scoring
    ats = compute_ats_scores(resume, jd)

    # LLM scoring
    try:
        llm_output, llm_raw = score_resume_with_llm(
            jd_text=jd.raw_text,
            resume_text=resume.raw_text,
            skills=resume.sections.skills,
            experience=resume.sections.experience,
            education=resume.sections.education,
            projects=resume.sections.projects,
            certifications=resume.sections.certifications,
        )
    except RuntimeError as e:
        logger.error("LLM scoring failed for %s: %s", resume.filename, e)
        # Fallback: use ATS scores only, LLM score = 0
        llm_output = None
        llm_raw = {"error": str(e)}

    # Compute sub-scores
    llm_score = llm_output.overall_score if llm_output else 0
    subscores = SubScores(
        llm_score=llm_score,
        keyword_relevance_score=ats.keyword_score,
        skill_fit_score=ats.skill_score,
        experience_fit_score=ats.experience_score,
        domain_fit_score=ats.domain_score,
    )

    # Weighted aggregate
    overall_score = _compute_weighted_score(
        llm_score=subscores.llm_score,
        keyword_score=subscores.keyword_relevance_score,
        skill_score=subscores.skill_fit_score,
        experience_score=subscores.experience_fit_score,
        domain_score=subscores.domain_fit_score,
    )

    # Filter decision
    filter_decision = _apply_filter(overall_score)

    # Location match
    location_match = ""
    if llm_output:
        if llm_output.location_fit_score >= 80:
            location_match = "match"
        elif llm_output.location_fit_score >= 50:
            location_match = "partial"
        else:
            location_match = "no_match"

    return CandidateResult(
        candidate_name=resume.candidate_name,
        candidate_id=candidate_id,
        rank=0,  # set during ranking
        overall_score=overall_score,
        filter_decision=filter_decision,
        subscores=subscores,
        matched_requirements=llm_output.matched_requirements if llm_output else [],
        missing_requirements=llm_output.missing_requirements if llm_output else [],
        matched_lines=llm_output.matched_evidence_lines if llm_output else [],
        evidence_snippets=llm_output.matched_evidence_lines[:10] if llm_output else [],
        resume_sections=resume.sections.model_dump(),
        llm_explanation=llm_output.explanation if llm_output else "LLM scoring failed",
        llm_raw_json=llm_raw,
        keyword_analysis=ats.model_dump(),
        confidence=llm_output.confidence if llm_output else 0,
        location_match=location_match,
        metadata=CandidateMetadata(
            resume_filename=resume.filename,
            resume_type=resume.file_type,
            jd_source=jd.source,
            run_id=run_id,
            timestamp=timestamp,
        ),
    )


# ── Run Full Pipeline ────────────────────────────────────────────────────────

def run_pipeline(
    resume_s3_keys: list[str],
    jd_text: str | None = None,
    jd_s3_key: str | None = None,
) -> ProcessResponse:
    """
    Full scoring pipeline:
    1. Parse JD
    2. Download & parse each resume
    3. Score each candidate (LLM + ATS)
    4. Rank candidates
    5. Save results to S3
    6. Return structured response
    """
    run_id = str(uuid.uuid4())[:12]
    logger.info("Starting pipeline run_id=%s with %d resumes", run_id, len(resume_s3_keys))

    # 1. Parse JD
    jd_pdf_data = None
    if jd_s3_key:
        jd_pdf_data = download_file(jd_s3_key)
        jd_text = None  # PDF takes precedence
    jd = parse_jd(text=jd_text, pdf_data=jd_pdf_data)
    logger.info("JD parsed: role=%s, skills=%d", jd.role_title, len(jd.required_skills))

    # 2. Parse resumes
    parsed_resumes: list[ParsedResume] = []
    parse_errors: list[dict] = []
    for s3_key in resume_s3_keys:
        try:
            filename = s3_key.split("/")[-1]
            file_type = _detect_file_type(filename)
            data = download_file(s3_key)
            resume = parse_resume(data, filename, file_type)
            parsed_resumes.append(resume)
            logger.info("Parsed resume: %s (%s)", resume.candidate_name, filename)
        except Exception as e:
            logger.error("Failed to parse resume %s: %s", s3_key, e)
            parse_errors.append({"s3_key": s3_key, "error": str(e)})

    if not parsed_resumes:
        raise ValueError("No resumes could be parsed successfully.")

    # 3. Score each candidate
    candidates: list[CandidateResult] = []
    for resume in parsed_resumes:
        try:
            result = _score_candidate(resume, jd, run_id)
            candidates.append(result)
        except Exception as e:
            logger.error("Failed to score %s: %s", resume.filename, e)

    if not candidates:
        raise ValueError("No candidates could be scored.")

    # 4. Rank by overall score descending
    candidates.sort(key=lambda c: c.overall_score, reverse=True)
    for i, candidate in enumerate(candidates):
        candidate.rank = i + 1

    # 5. Summary stats
    scores = [c.overall_score for c in candidates]
    summary = RunSummaryStats(
        total_candidates=len(candidates),
        strong_match_count=sum(1 for c in candidates if c.filter_decision == FilterDecision.strong_match),
        shortlist_count=sum(1 for c in candidates if c.filter_decision == FilterDecision.shortlist),
        reject_count=sum(1 for c in candidates if c.filter_decision == FilterDecision.reject),
        avg_score=round(sum(scores) / len(scores), 2),
        max_score=max(scores),
        min_score=min(scores),
    )

    # 6. Build run result and persist to S3
    run_result = RunResult(
        run_id=run_id,
        jd_text=jd.raw_text,
        candidates=candidates,
        ranking_order=[c.candidate_id for c in candidates],
        summary_stats=summary,
        threshold_config={
            "reject_below": config.thresholds.reject_below,
            "shortlist_below": config.thresholds.shortlist_below,
        },
        weights_used=config.weights.as_dict(),
        metadata={
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_resumes_submitted": len(resume_s3_keys),
            "parse_errors": parse_errors,
        },
    )

    try:
        s3_key = save_run_result(run_id, run_result.model_dump())
    except Exception as e:
        logger.error("Failed to save results to S3: %s", e)
        s3_key = ""

    return ProcessResponse(
        run_id=run_id,
        candidates=candidates,
        summary_stats=summary,
        s3_result_key=s3_key,
    )
