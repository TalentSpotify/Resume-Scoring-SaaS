"""
FastAPI route definitions: upload presigned URLs, process, results, health.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.config import config
from app.pipeline import run_pipeline
from app.schemas import (
    ErrorResponse,
    HealthResponse,
    PresignedUrlRequest,
    PresignedUrlResponse,
    ProcessRequest,
    ProcessResponse,
)
from app.storage import (
    generate_presigned_upload,
    load_run_result,
    upload_bytes,
)
from app.utils import safe_filename

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


# ── Health ───────────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse()


# ── Presigned Upload URL ─────────────────────────────────────────────────────

@router.post("/upload/presigned-url", response_model=PresignedUrlResponse)
async def get_presigned_url(req: PresignedUrlRequest):
    """Generate a presigned POST URL for the frontend to upload directly to S3."""
    try:
        sanitized = safe_filename(req.filename)
        unique_name = f"{uuid.uuid4().hex[:8]}_{sanitized}"
        result = generate_presigned_upload(unique_name, req.content_type)
        return PresignedUrlResponse(**result)
    except Exception as e:
        logger.error("Presigned URL generation failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── Direct Upload (fallback for simpler setups) ─────────────────────────────

@router.post("/upload/resumes")
async def upload_resumes(files: list[UploadFile] = File(...)):
    """Upload resumes directly through the backend (fallback if presigned URLs aren't used)."""
    uploaded = []
    for file in files:
        ext = file.filename.lower().rsplit(".", 1)[-1] if file.filename else ""
        if f".{ext}" not in config.allowed_resume_types:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file.filename}. Allowed: {config.allowed_resume_types}",
            )
        data = await file.read()
        sanitized = safe_filename(file.filename or "resume")
        s3_key = f"{config.aws.s3_upload_prefix}/{uuid.uuid4().hex[:8]}_{sanitized}"
        upload_bytes(s3_key, data, content_type=file.content_type or "application/octet-stream")
        uploaded.append({
            "filename": file.filename,
            "s3_key": s3_key,
            "size_bytes": len(data),
        })
    return {"uploaded": uploaded}


@router.post("/upload/jd")
async def upload_jd(file: UploadFile = File(...)):
    """Upload a JD PDF through the backend."""
    ext = file.filename.lower().rsplit(".", 1)[-1] if file.filename else ""
    if f".{ext}" not in config.allowed_jd_types:
        raise HTTPException(status_code=400, detail=f"Unsupported JD file type. Allowed: {config.allowed_jd_types}")
    data = await file.read()
    sanitized = safe_filename(file.filename or "jd.pdf")
    s3_key = f"{config.aws.s3_upload_prefix}/jd/{uuid.uuid4().hex[:8]}_{sanitized}"
    upload_bytes(s3_key, data, content_type=file.content_type or "application/pdf")
    return {"filename": file.filename, "s3_key": s3_key, "size_bytes": len(data)}


# ── Process ──────────────────────────────────────────────────────────────────

@router.post("/process", response_model=ProcessResponse)
async def process_candidates(req: ProcessRequest):
    """
    Score and rank all resumes against the JD.
    Synchronous processing — caller waits for results.
    """
    if not req.resume_s3_keys:
        raise HTTPException(status_code=400, detail="No resume S3 keys provided.")
    if not req.jd_text and not req.jd_s3_key:
        raise HTTPException(status_code=400, detail="Provide either jd_text or jd_s3_key.")

    try:
        result = run_pipeline(
            resume_s3_keys=req.resume_s3_keys,
            jd_text=req.jd_text,
            jd_s3_key=req.jd_s3_key,
        )
        return result
    except ValueError as e:
        logger.error("Pipeline validation error: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Pipeline failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing failed: {e}")


# ── Results ──────────────────────────────────────────────────────────────────

@router.get("/runs/{run_id}")
async def get_run(run_id: str):
    """Retrieve a full run result from S3."""
    try:
        result = load_run_result(run_id)
        return result
    except Exception as e:
        logger.error("Failed to load run %s: %s", run_id, e)
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")


@router.get("/runs/{run_id}/results")
async def get_run_results(run_id: str):
    """Retrieve just the candidates and summary from a run."""
    try:
        result = load_run_result(run_id)
        return {
            "candidates": result.get("candidates", []),
            "summary_stats": result.get("summary_stats", {}),
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")


@router.get("/runs/{run_id}/candidate/{candidate_id}")
async def get_candidate(run_id: str, candidate_id: str):
    """Retrieve a single candidate result from a run."""
    try:
        result = load_run_result(run_id)
        for candidate in result.get("candidates", []):
            if candidate.get("candidate_id") == candidate_id:
                return candidate
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found in run {run_id}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
