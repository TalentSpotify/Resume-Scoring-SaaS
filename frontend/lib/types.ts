/* Types mirroring backend Pydantic schemas */

export type FileType = "pdf" | "docx";
export type JdSource = "text" | "pdf";
export type FilterDecision = "reject" | "shortlist" | "strong_match";

export interface PresignedUrlRequest {
  filename: string;
  content_type: string;
}

export interface PresignedUrlResponse {
  upload_url: string;
  s3_key: string;
  fields: Record<string, string>;
}

export interface UploadedFileInfo {
  filename: string;
  s3_key: string;
  size_bytes: number;
  file_type: FileType;
  status: "pending" | "uploading" | "done" | "error";
  file?: File;
}

export interface SubScores {
  llm_score: number;
  keyword_relevance_score: number;
  skill_fit_score: number;
  experience_fit_score: number;
  domain_fit_score: number;
}

export interface CandidateMetadata {
  resume_filename: string;
  resume_type: FileType;
  jd_source: JdSource;
  run_id: string;
  timestamp: string;
}

export interface CandidateResult {
  candidate_name: string;
  candidate_id: string;
  rank: number;
  overall_score: number;
  filter_decision: FilterDecision;
  subscores: SubScores;
  matched_requirements: string[];
  missing_requirements: string[];
  matched_lines: string[];
  evidence_snippets: string[];
  resume_sections: Record<string, string>;
  llm_explanation: string;
  llm_raw_json: Record<string, unknown>;
  keyword_analysis: Record<string, unknown>;
  confidence: number;
  location_match: string;
  metadata: CandidateMetadata;
}

export interface RunSummaryStats {
  total_candidates: number;
  strong_match_count: number;
  shortlist_count: number;
  reject_count: number;
  avg_score: number;
  max_score: number;
  min_score: number;
}

export interface ProcessRequest {
  resume_s3_keys: string[];
  jd_text?: string | null;
  jd_s3_key?: string | null;
}

export interface ProcessResponse {
  run_id: string;
  candidates: CandidateResult[];
  summary_stats: RunSummaryStats;
  s3_result_key: string;
}
