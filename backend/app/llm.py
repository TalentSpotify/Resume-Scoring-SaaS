"""
LLM integration: Amazon Bedrock Claude via LangChain.
Handles prompt composition, structured output parsing, and retry logic.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from app.config import config
from app.schemas import FilterDecision, LLMScoreOutput

logger = logging.getLogger(__name__)

# ── Bedrock Client ───────────────────────────────────────────────────────────

_bedrock_llm: ChatBedrock | None = None


def get_bedrock_llm() -> ChatBedrock:
    global _bedrock_llm
    if _bedrock_llm is None:
        _bedrock_llm = ChatBedrock(
            model_id=config.aws.bedrock_model_id,
            region_name=config.aws.region,
            model_kwargs={"max_tokens": 4096, "temperature": 0},
        )
    return _bedrock_llm


# ── Prompt Template ──────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert technical recruiter and resume evaluator. You evaluate resumes against job descriptions with precision and fairness.

IMPORTANT FAIRNESS RULES:
- Do NOT consider candidate name, gender, age, college tier, or photos for scoring.
- DO consider location if the JD specifies a location preference.
- Focus only on skills, experience, projects, domain knowledge, and role fit.

SCORING RUBRIC (each 0-100):
1. jd_coverage_score: How well does the resume cover JD requirements?
2. experience_relevance_score: How relevant is the work experience?
3. project_relevance_score: How relevant are projects?
4. role_fit_score: How well does the candidate fit the target role level?
5. seniority_fit_score: Does seniority match?
6. domain_fit_score: Does domain expertise match?
7. location_fit_score: Does location match if JD specifies one? (100 if no location preference)
8. employability_score: Overall employability for this specific role.

THRESHOLD DEFINITIONS:
- Below {reject_threshold}: Reject
- {reject_threshold} to {shortlist_threshold}: Shortlist
- Above {shortlist_threshold}: Strong Match

You MUST respond with ONLY valid JSON matching this exact schema, no markdown fences, no extra text:
{{
  "overall_score": <float 0-100>,
  "jd_coverage_score": <float 0-100>,
  "experience_relevance_score": <float 0-100>,
  "project_relevance_score": <float 0-100>,
  "role_fit_score": <float 0-100>,
  "seniority_fit_score": <float 0-100>,
  "domain_fit_score": <float 0-100>,
  "location_fit_score": <float 0-100>,
  "employability_score": <float 0-100>,
  "matched_requirements": [<list of JD requirements met by the resume>],
  "missing_requirements": [<list of JD requirements NOT met>],
  "matched_evidence_lines": [<exact lines/phrases from resume supporting matched requirements>],
  "explanation": "<detailed human-readable explanation of the score>",
  "confidence": <float 0-1, your confidence in this evaluation>,
  "classification": "<reject|shortlist|strong_match>"
}}"""

USER_PROMPT_TEMPLATE = """Evaluate this resume against the job description.

=== JOB DESCRIPTION ===
{jd_text}

=== RESUME TEXT ===
{resume_text}

=== RESUME STRUCTURED DATA ===
Skills: {skills}
Experience: {experience}
Education: {education}
Projects: {projects}
Certifications: {certifications}

Respond with ONLY the JSON object. No markdown, no explanation outside the JSON."""


def _build_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", USER_PROMPT_TEMPLATE),
    ])


# ── Parse LLM Response ──────────────────────────────────────────────────────

def _parse_llm_json(raw: str) -> dict[str, Any]:
    """Parse JSON from LLM response, handling common formatting issues."""
    text = raw.strip()
    # Strip markdown fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    return json.loads(text)


def _dict_to_llm_output(data: dict[str, Any]) -> LLMScoreOutput:
    """Convert parsed dict to LLMScoreOutput, handling missing fields gracefully."""
    classification_raw = data.get("classification", "reject")
    try:
        classification = FilterDecision(classification_raw)
    except ValueError:
        classification = FilterDecision.reject

    return LLMScoreOutput(
        overall_score=float(data.get("overall_score", 0)),
        jd_coverage_score=float(data.get("jd_coverage_score", 0)),
        experience_relevance_score=float(data.get("experience_relevance_score", 0)),
        project_relevance_score=float(data.get("project_relevance_score", 0)),
        role_fit_score=float(data.get("role_fit_score", 0)),
        seniority_fit_score=float(data.get("seniority_fit_score", 0)),
        domain_fit_score=float(data.get("domain_fit_score", 0)),
        location_fit_score=float(data.get("location_fit_score", 0)),
        employability_score=float(data.get("employability_score", 0)),
        matched_requirements=data.get("matched_requirements", []),
        missing_requirements=data.get("missing_requirements", []),
        matched_evidence_lines=data.get("matched_evidence_lines", []),
        explanation=data.get("explanation", ""),
        confidence=float(data.get("confidence", 0)),
        classification=classification,
    )


# ── Score a Single Resume ────────────────────────────────────────────────────

def score_resume_with_llm(
    jd_text: str,
    resume_text: str,
    skills: str,
    experience: str,
    education: str,
    projects: str,
    certifications: str,
) -> tuple[LLMScoreOutput, dict[str, Any]]:
    """
    Score a resume against a JD using Bedrock Claude.
    Returns (parsed_output, raw_json_dict).
    Retries on parse failure up to config.llm_max_retries times.
    """
    llm = get_bedrock_llm()
    prompt = _build_prompt()

    messages = prompt.format_messages(
        reject_threshold=config.thresholds.reject_below,
        shortlist_threshold=config.thresholds.shortlist_below,
        jd_text=jd_text,
        resume_text=resume_text,
        skills=skills or "Not specified",
        experience=experience or "Not specified",
        education=education or "Not specified",
        projects=projects or "Not specified",
        certifications=certifications or "Not specified",
    )

    last_error = None
    for attempt in range(1, config.llm_max_retries + 2):  # +1 for initial + retries
        try:
            logger.info("LLM scoring attempt %d", attempt)
            response = llm.invoke(messages)
            raw_text = response.content if isinstance(response.content, str) else str(response.content)
            raw_dict = _parse_llm_json(raw_text)
            parsed = _dict_to_llm_output(raw_dict)
            return parsed, raw_dict
        except json.JSONDecodeError as e:
            last_error = e
            logger.warning("LLM returned malformed JSON (attempt %d): %s", attempt, e)
        except Exception as e:
            last_error = e
            logger.warning("LLM call failed (attempt %d): %s", attempt, e)

    logger.error("LLM scoring failed after %d attempts: %s", config.llm_max_retries + 1, last_error)
    raise RuntimeError(f"LLM scoring failed after retries: {last_error}")
