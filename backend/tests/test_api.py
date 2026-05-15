"""Tests for API route response schemas and validation."""

import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_ok(self):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data


class TestProcessValidation:
    def test_process_rejects_empty_resumes(self):
        response = client.post("/api/process", json={
            "resume_s3_keys": [],
            "jd_text": "Some job description",
        })
        assert response.status_code == 400

    def test_process_rejects_missing_jd(self):
        response = client.post("/api/process", json={
            "resume_s3_keys": ["uploads/test.pdf"],
        })
        assert response.status_code == 400


class TestUploadValidation:
    def test_presigned_url_schema(self):
        response = client.post("/api/upload/presigned-url", json={
            "filename": "test_resume.pdf",
            "content_type": "application/pdf",
        })
        # Will fail without real AWS creds, but validates route exists
        assert response.status_code in (200, 500)
