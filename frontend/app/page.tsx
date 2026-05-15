"use client";

import { useState } from "react";
import { Zap, Loader2, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import Uploader from "@/components/Uploader";
import JdPanel from "@/components/JdPanel";
import ResultsTable from "@/components/ResultsTable";
import { processResumes } from "@/lib/api";
import type { UploadedFileInfo, ProcessResponse } from "@/lib/types";

export default function Home() {
  const [files, setFiles] = useState<UploadedFileInfo[]>([]);
  const [jdText, setJdText] = useState("");
  const [jdS3Key, setJdS3Key] = useState("");
  const [jdFilename, setJdFilename] = useState("");
  const [processing, setProcessing] = useState(false);
  const [result, setResult] = useState<ProcessResponse | null>(null);
  const [error, setError] = useState("");

  const readyFiles = files.filter((f) => f.status === "done" && f.s3_key);
  const canProcess = readyFiles.length > 0 && (jdText.trim() || jdS3Key) && !processing;

  const handleProcess = async () => {
    setProcessing(true);
    setError("");
    setResult(null);

    try {
      const resp = await processResumes({
        resume_s3_keys: readyFiles.map((f) => f.s3_key),
        jd_text: jdText.trim() || null,
        jd_s3_key: jdS3Key || null,
      });
      setResult(resp);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Processing failed";
      setError(msg);
    } finally {
      setProcessing(false);
    }
  };

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b border-zinc-200 bg-white/60 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-teal-500 to-emerald-600 flex items-center justify-center">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-zinc-900 tracking-tight">
                Resume Scorer
              </h1>
              <p className="text-xs text-zinc-400">
                AI-powered candidate ranking
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {readyFiles.length > 0 && (
              <span className="text-xs text-zinc-500">
                {readyFiles.length} resume{readyFiles.length !== 1 ? "s" : ""} ready
              </span>
            )}
            <button
              onClick={handleProcess}
              disabled={!canProcess}
              className={cn(
                "flex items-center gap-2 px-5 py-2.5 text-sm font-semibold rounded-xl transition-all duration-200",
                canProcess
                  ? "bg-zinc-900 text-white hover:bg-zinc-800 active:scale-[0.98] shadow-lg shadow-zinc-900/20"
                  : "bg-zinc-200 text-zinc-400 cursor-not-allowed"
              )}
            >
              {processing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Scoring...
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4" />
                  Score Candidates
                </>
              )}
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* Two-panel input area */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: Resume upload */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-zinc-800">Resumes</h2>
              <span className="text-xs text-zinc-400">Upload PDF or DOCX</span>
            </div>
            <Uploader
              files={files}
              onFilesChange={setFiles}
              disabled={processing}
            />
          </div>

          {/* Right: JD input */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-zinc-800">
                Job Description
              </h2>
              <span className="text-xs text-zinc-400">Paste or upload</span>
            </div>
            <JdPanel
              jdText={jdText}
              jdS3Key={jdS3Key}
              jdFilename={jdFilename}
              onJdTextChange={setJdText}
              onJdS3KeyChange={(key, name) => {
                setJdS3Key(key);
                setJdFilename(name);
              }}
              disabled={processing}
            />
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="flex items-start gap-3 px-4 py-3 bg-red-50 border border-red-200 rounded-xl">
            <AlertTriangle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-red-800">Processing Error</p>
              <p className="text-xs text-red-600 mt-0.5">{error}</p>
            </div>
          </div>
        )}

        {/* Processing indicator */}
        {processing && (
          <div className="flex flex-col items-center justify-center py-16 space-y-4">
            <div className="relative">
              <div className="w-16 h-16 border-4 border-zinc-200 rounded-full" />
              <div className="absolute inset-0 w-16 h-16 border-4 border-teal-500 border-t-transparent rounded-full animate-spin" />
            </div>
            <div className="text-center">
              <p className="text-sm font-medium text-zinc-700">
                Analyzing {readyFiles.length} resume{readyFiles.length !== 1 ? "s" : ""}...
              </p>
              <p className="text-xs text-zinc-400 mt-1">
                Running LLM + ATS scoring pipeline
              </p>
            </div>
          </div>
        )}

        {/* Results */}
        {result && !processing && (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-bold text-zinc-900">Results</h2>
              <div className="h-px flex-1 bg-zinc-200" />
            </div>
            <ResultsTable result={result} />
          </div>
        )}
      </main>
    </div>
  );
}
