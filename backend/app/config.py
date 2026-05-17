"""
Configuration: environment variables, scoring weights, thresholds, AWS settings.
All scoring behavior is config-driven.
"""

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class AWSConfig:
    region: str = os.getenv("AWS_REGION", "ap-south-1")
    s3_bucket: str = os.getenv("S3_BUCKET", "resume-scoring-app-bucket")
    bedrock_model_id: str = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-sonnet-4-20250514-v1:0")
    s3_upload_prefix: str = os.getenv("S3_UPLOAD_PREFIX", "uploads")
    s3_results_prefix: str = os.getenv("S3_RESULTS_PREFIX", "results")


@dataclass(frozen=True)
class ScoringWeights:
    llm: float = float(os.getenv("WEIGHT_LLM", "0.65"))
    ats_keyword: float = float(os.getenv("WEIGHT_ATS_KEYWORD", "0.12"))
    skill_fit: float = float(os.getenv("WEIGHT_SKILL_FIT", "0.10"))
    experience_fit: float = float(os.getenv("WEIGHT_EXPERIENCE_FIT", "0.08"))
    domain_fit: float = float(os.getenv("WEIGHT_DOMAIN_FIT", "0.05"))

    def as_dict(self) -> dict:
        return {
            "llm": self.llm,
            "ats_keyword": self.ats_keyword,
            "skill_fit": self.skill_fit,
            "experience_fit": self.experience_fit,
            "domain_fit": self.domain_fit,
        }


@dataclass(frozen=True)
class Thresholds:
    reject_below: float = float(os.getenv("THRESHOLD_REJECT", "60"))
    shortlist_below: float = float(os.getenv("THRESHOLD_SHORTLIST", "80"))
    # reject < 60, shortlist 60-80, strong_match > 80


@dataclass(frozen=True)
class AppConfig:
    aws: AWSConfig = field(default_factory=AWSConfig)
    weights: ScoringWeights = field(default_factory=ScoringWeights)
    thresholds: Thresholds = field(default_factory=Thresholds)
    allowed_resume_types: tuple = (".pdf", ".docx")
    allowed_jd_types: tuple = (".pdf",)
    max_resume_size_mb: int = int(os.getenv("MAX_RESUME_SIZE_MB", "10"))
    max_jd_size_mb: int = int(os.getenv("MAX_JD_SIZE_MB", "10"))
    llm_max_retries: int = int(os.getenv("LLM_MAX_RETRIES", "2"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    cors_origins: list = field(
        default_factory=lambda: os.getenv("CORS_ORIGINS", "http://frontend-service:3000").split(",")
    )


config = AppConfig()
