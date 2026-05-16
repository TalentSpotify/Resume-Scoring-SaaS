/* API client for backend communication */

import type {
  PresignedUrlResponse,
  ProcessRequest,
  ProcessResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "/api";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }

  return res.json() as Promise<T>;
}

/* ── Presigned Upload ──────────────────────────────────────────────────── */

export async function getPresignedUrl(
  filename: string,
  contentType: string
): Promise<PresignedUrlResponse> {
  return apiFetch<PresignedUrlResponse>("/upload/presigned-url", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      filename,
      content_type: contentType,
    }),
  });
}

export async function uploadFileToS3(
  file: File,
  presigned: PresignedUrlResponse
): Promise<void> {
  const formData = new FormData();

  Object.entries(presigned.fields).forEach(([key, val]) => {
    formData.append(key, val);
  });

  formData.append("file", file);

  const res = await fetch(presigned.upload_url, {
    method: "POST",
    body: formData,
  });

  if (!res.ok && res.status !== 204) {
    throw new Error(`S3 upload failed: ${res.status}`);
  }
}

/* ── Direct Upload (fallback) ──────────────────────────────────────────── */

export async function uploadResumesDirect(
  files: File[]
): Promise<{
  uploaded: {
    filename: string;
    s3_key: string;
    size_bytes: number;
  }[];
}> {
  const formData = new FormData();

  files.forEach((f) => formData.append("files", f));

  return apiFetch("/upload/resumes", {
    method: "POST",
    body: formData,
  });
}

export async function uploadJdDirect(
  file: File
): Promise<{
  filename: string;
  s3_key: string;
  size_bytes: number;
}> {
  const formData = new FormData();

  formData.append("file", file);

  return apiFetch("/upload/jd", {
    method: "POST",
    body: formData,
  });
}

/* ── Process ───────────────────────────────────────────────────────────── */

export async function processResumes(
  req: ProcessRequest
): Promise<ProcessResponse> {
  return apiFetch<ProcessResponse>("/process", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(req),
  });
}

/* ── Results ───────────────────────────────────────────────────────────── */

export async function getRunResult(
  runId: string
): Promise<Record<string, unknown>> {
  return apiFetch(`/runs/${runId}`);
}