"""
Amazon S3 storage: upload/download files, presigned URLs, save JSON results.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import boto3
from botocore.exceptions import ClientError

from app.config import config

logger = logging.getLogger(__name__)

_s3_client = None


def _get_s3():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client("s3", region_name=config.aws.region)
    return _s3_client


# ── Presigned URL ────────────────────────────────────────────────────────────

def generate_presigned_upload(filename: str, content_type: str) -> dict:
    """Generate a presigned POST URL for direct browser upload to S3."""
    s3 = _get_s3()
    s3_key = f"{config.aws.s3_upload_prefix}/{filename}"
    try:
        presigned = s3.generate_presigned_post(
            Bucket=config.aws.s3_bucket,
            Key=s3_key,
            Fields={"Content-Type": content_type},
            Conditions=[
                {"Content-Type": content_type},
                ["content-length-range", 1, config.max_resume_size_mb * 1024 * 1024],
            ],
            ExpiresIn=600,  # 10 minutes
        )
        return {
            "upload_url": presigned["url"],
            "fields": presigned["fields"],
            "s3_key": s3_key,
        }
    except ClientError as e:
        logger.error("Failed to generate presigned URL: %s", e)
        raise


# ── Download from S3 ─────────────────────────────────────────────────────────

def download_file(s3_key: str) -> bytes:
    """Download a file from S3 and return bytes."""
    s3 = _get_s3()
    try:
        response = s3.get_object(Bucket=config.aws.s3_bucket, Key=s3_key)
        return response["Body"].read()
    except ClientError as e:
        logger.error("Failed to download s3://%s/%s: %s", config.aws.s3_bucket, s3_key, e)
        raise


# ── Upload bytes to S3 ───────────────────────────────────────────────────────

def upload_bytes(s3_key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    """Upload raw bytes to S3."""
    s3 = _get_s3()
    try:
        s3.put_object(
            Bucket=config.aws.s3_bucket,
            Key=s3_key,
            Body=data,
            ContentType=content_type,
        )
        return s3_key
    except ClientError as e:
        logger.error("Failed to upload to s3://%s/%s: %s", config.aws.s3_bucket, s3_key, e)
        raise


# ── Save JSON Results ─────────────────────────────────────────────────────────

def save_run_result(run_id: str, result_data: dict[str, Any]) -> str:
    """Save run result JSON to S3 and return the S3 key."""
    s3_key = f"{config.aws.s3_results_prefix}/{run_id}/result.json"
    json_bytes = json.dumps(result_data, indent=2, default=str).encode("utf-8")
    upload_bytes(s3_key, json_bytes, content_type="application/json")
    logger.info("Saved run result to s3://%s/%s", config.aws.s3_bucket, s3_key)
    return s3_key


def save_candidate_result(run_id: str, candidate_id: str, result_data: dict[str, Any]) -> str:
    """Save individual candidate result JSON to S3."""
    s3_key = f"{config.aws.s3_results_prefix}/{run_id}/candidates/{candidate_id}.json"
    json_bytes = json.dumps(result_data, indent=2, default=str).encode("utf-8")
    upload_bytes(s3_key, json_bytes, content_type="application/json")
    return s3_key


# ── Load JSON Results ─────────────────────────────────────────────────────────

def load_run_result(run_id: str) -> dict[str, Any]:
    """Load a run result JSON from S3."""
    s3_key = f"{config.aws.s3_results_prefix}/{run_id}/result.json"
    data = download_file(s3_key)
    return json.loads(data)
