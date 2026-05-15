"""
Resume and JD parsing: PDF/DOCX text extraction, section detection, name extraction, JD normalization.
"""

from __future__ import annotations

import io
import logging
import re

import fitz  # PyMuPDF
from docx import Document as DocxDocument

from app.schemas import (
    FileType,
    JdSource,
    ParsedJD,
    ParsedResume,
    ResumeSections,
)

logger = logging.getLogger(__name__)

# ── Section headers (case-insensitive patterns) ─────────────────────────────

_SECTION_PATTERNS: dict[str, list[str]] = {
    "summary": [
        r"summary", r"objective", r"profile", r"about\s*me", r"professional\s*summary",
        r"career\s*summary", r"career\s*objective",
    ],
    "education": [r"education", r"academic", r"qualification", r"degree"],
    "experience": [
        r"experience", r"work\s*history", r"employment", r"professional\s*experience",
        r"work\s*experience",
    ],
    "projects": [r"project", r"personal\s*project", r"academic\s*project"],
    "skills": [
        r"skill", r"technical\s*skill", r"core\s*competenc", r"technologies",
        r"tools", r"proficienc",
    ],
    "certifications": [r"certification", r"certificate", r"licensed", r"accreditation"],
    "achievements": [
        r"achievement", r"award", r"honor", r"recognition", r"accomplishment",
    ],
}


def _compile_section_regex() -> dict[str, re.Pattern]:
    compiled = {}
    for section, patterns in _SECTION_PATTERNS.items():
        joined = "|".join(patterns)
        compiled[section] = re.compile(
            rf"^\s*(?:{joined})s?\s*[:\-–—]?\s*$", re.IGNORECASE
        )
    return compiled


_SECTION_RE = _compile_section_regex()


# ── PDF / DOCX Extraction ───────────────────────────────────────────────────

def extract_text_from_pdf(data: bytes) -> str:
    """Extract text from PDF bytes, preserving line boundaries."""
    try:
        doc = fitz.open(stream=data, filetype="pdf")
        pages = []
        for page in doc:
            pages.append(page.get_text("text"))
        doc.close()
        return "\n".join(pages)
    except Exception as e:
        logger.error("PDF extraction failed: %s", e)
        raise ValueError(f"Failed to extract text from PDF: {e}") from e


def extract_text_from_docx(data: bytes) -> str:
    """Extract text from DOCX bytes, preserving paragraph boundaries."""
    try:
        doc = DocxDocument(io.BytesIO(data))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)
    except Exception as e:
        logger.error("DOCX extraction failed: %s", e)
        raise ValueError(f"Failed to extract text from DOCX: {e}") from e


def extract_text(data: bytes, file_type: FileType) -> str:
    if file_type == FileType.pdf:
        return extract_text_from_pdf(data)
    elif file_type == FileType.docx:
        return extract_text_from_docx(data)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")


# ── Name Extraction ─────────────────────────────────────────────────────────

def _extract_candidate_name(text: str) -> str:
    """
    Heuristic: first non-empty line that looks like a name (2-4 capitalized words,
    no digits, no common section headers).
    """
    skip_words = {
        "resume", "cv", "curriculum", "vitae", "summary", "objective",
        "education", "experience", "skills", "projects", "contact",
    }
    for line in text.split("\n")[:15]:
        line = line.strip()
        if not line or len(line) < 3 or len(line) > 60:
            continue
        if any(ch.isdigit() for ch in line):
            continue
        if line.lower() in skip_words:
            continue
        words = line.split()
        if 2 <= len(words) <= 5 and all(w[0].isupper() for w in words if len(w) > 1):
            return line
    return "Unknown"


# ── Section Detection ────────────────────────────────────────────────────────

def _detect_sections(text: str) -> ResumeSections:
    """Split resume text into sections based on header detection."""
    lines = text.split("\n")
    current_section = "other"
    section_lines: dict[str, list[str]] = {
        k: [] for k in ResumeSections.model_fields.keys()
    }

    for line in lines:
        stripped = line.strip()
        matched = False
        for section_name, pattern in _SECTION_RE.items():
            if pattern.match(stripped):
                current_section = section_name
                matched = True
                break
        if not matched and stripped:
            section_lines[current_section].append(line)

    return ResumeSections(
        **{k: "\n".join(v).strip() for k, v in section_lines.items()}
    )


# ── Resume Parsing ───────────────────────────────────────────────────────────

def parse_resume(data: bytes, filename: str, file_type: FileType) -> ParsedResume:
    """Parse a resume from raw bytes into structured form."""
    raw_text = extract_text(data, file_type)
    if not raw_text.strip():
        raise ValueError(f"Resume '{filename}' produced no extractable text.")

    candidate_name = _extract_candidate_name(raw_text)
    sections = _detect_sections(raw_text)

    return ParsedResume(
        candidate_name=candidate_name,
        raw_text=raw_text,
        sections=sections,
        filename=filename,
        file_type=file_type,
    )


# ── JD Parsing ───────────────────────────────────────────────────────────────

_YOE_RE = re.compile(r"(\d+)\+?\s*(?:years?|yrs?)", re.IGNORECASE)
_LOCATION_RE = re.compile(
    r"(?:location|based\s+in|office|remote|hybrid|on-?site)\s*[:\-–]?\s*(.+)",
    re.IGNORECASE,
)


def _extract_list_after(text: str, header_pattern: str) -> list[str]:
    """Extract bullet/line items following a header pattern."""
    pattern = re.compile(
        rf"(?:{header_pattern})\s*[:\-–]?\s*\n((?:[\s]*[\-•*]\s*.+\n?)+)",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if match:
        block = match.group(1)
        return [
            re.sub(r"^[\s\-•*]+", "", line).strip()
            for line in block.split("\n")
            if line.strip()
        ]
    return []


def _extract_skills_from_text(text: str) -> list[str]:
    """Extract skills from comma/semicolon separated lists or bullet items near skill headers."""
    skills: list[str] = []
    pattern = re.compile(
        r"(?:required\s+skills?|must\s+have|key\s+skills?|technical\s+skills?|qualifications?)\s*[:\-–]?\s*\n?(.*?)(?:\n\n|\Z)",
        re.IGNORECASE | re.DOTALL,
    )
    for match in pattern.finditer(text):
        block = match.group(1)
        for line in block.split("\n"):
            line = re.sub(r"^[\s\-•*]+", "", line).strip()
            if line:
                for item in re.split(r"[,;]", line):
                    item = item.strip()
                    if item and len(item) < 80:
                        skills.append(item)
    return skills


def parse_jd(text: str | None = None, pdf_data: bytes | None = None) -> ParsedJD:
    """Parse a JD from text or PDF bytes."""
    source = JdSource.text
    if pdf_data:
        text = extract_text_from_pdf(pdf_data)
        source = JdSource.pdf
    if not text or not text.strip():
        raise ValueError("JD text is empty.")

    # Role title: first non-empty line or line with "role"/"position"/"title"
    role_title = ""
    for line in text.split("\n")[:10]:
        stripped = line.strip()
        if stripped and len(stripped) < 100:
            role_title = stripped
            break

    # Years of experience
    yoe_match = _YOE_RE.search(text)
    min_years = int(yoe_match.group(1)) if yoe_match else None

    # Location
    location = ""
    loc_match = _LOCATION_RE.search(text)
    if loc_match:
        location = loc_match.group(1).strip()[:100]

    # Skills
    required_skills = _extract_skills_from_text(text)
    preferred_skills = _extract_list_after(
        text, r"preferred\s+skills?|nice\s+to\s+have|bonus"
    )

    # Responsibilities
    responsibilities = _extract_list_after(
        text, r"responsibilities|duties|what\s+you.?ll\s+do"
    )

    # Must-have / nice-to-have
    must_have = _extract_list_after(text, r"must\s+have|required|minimum")
    nice_to_have = _extract_list_after(text, r"nice\s+to\s+have|preferred|bonus")

    # Domain: simple heuristic — look for industry keywords
    domain = ""
    domain_keywords = [
        "fintech", "healthcare", "e-commerce", "ecommerce", "saas", "edtech",
        "adtech", "logistics", "banking", "insurance", "retail", "telecom",
        "media", "gaming", "automotive", "cybersecurity", "biotech", "ai/ml",
    ]
    text_lower = text.lower()
    for kw in domain_keywords:
        if kw in text_lower:
            domain = kw
            break

    return ParsedJD(
        raw_text=text,
        role_title=role_title,
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        min_years_experience=min_years,
        domain=domain,
        location_preference=location,
        responsibilities=responsibilities,
        must_have=must_have,
        nice_to_have=nice_to_have,
        source=source,
    )
