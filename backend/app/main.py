"""
FastAPI application bootstrap.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router
from app.config import config
from app.utils import setup_logging

setup_logging(config.log_level)

app = FastAPI(
    title="Resume Scoring API",
    description="Automated resume scoring and ranking against job descriptions",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
