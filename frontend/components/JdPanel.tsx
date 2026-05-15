"use client";

import { useCallback, useRef, useState } from "react";
import { FileText, Upload, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { uploadJdDirect } from "@/lib/api";

interface JdPanelProps {
  jdText: string;
  jdS3Key: string;
  jdFilename: string;
  onJdTextChange: (text: string) => void;
  onJdS3KeyChange: (key: string, filename: string) => void;
  disabled?: boolean;
}

export default function JdPanel({
  jdText,
  jdS3Key,
  jdFilename,
  onJdTextChange,
  onJdS3KeyChange,
  disabled,
}: JdPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [mode, setMode] = useState<"text" | "pdf">(jdS3Key ? "pdf" : "text");
  const [uploading, setUploading] = useState(false);

  const handlePdfUpload = useCallback(
    async (file: File) => {
      if (!file.type.includes("pdf")) return;
      setUploading(true);
      try {
        const result = await uploadJdDirect(file);
        onJdS3KeyChange(result.s3_key, result.filename);
        onJdTextChange("");
      } catch (err) {
        console.error("JD upload failed:", err);
      } finally {
        setUploading(false);
      }
    },
    [onJdS3KeyChange, onJdTextChange]
  );

  const clearPdf = useCallback(() => {
    onJdS3KeyChange("", "");
    setMode("text");
  }, [onJdS3KeyChange]);

  return (
    <div className="space-y-3">
      {/* Mode tabs */}
      <div className="flex gap-1 p-0.5 bg-zinc-100 rounded-lg w-fit">
        <button
          className={cn(
            "px-3 py-1.5 text-xs font-medium rounded-md transition-all",
            mode === "text"
              ? "bg-white text-zinc-900 shadow-sm"
              : "text-zinc-500 hover:text-zinc-700"
          )}
          onClick={() => {
            setMode("text");
            onJdS3KeyChange("", "");
          }}
          disabled={disabled}
        >
          Paste Text
        </button>
        <button
          className={cn(
            "px-3 py-1.5 text-xs font-medium rounded-md transition-all",
            mode === "pdf"
              ? "bg-white text-zinc-900 shadow-sm"
              : "text-zinc-500 hover:text-zinc-700"
          )}
          onClick={() => setMode("pdf")}
          disabled={disabled}
        >
          Upload PDF
        </button>
      </div>

      {mode === "text" ? (
        <textarea
          value={jdText}
          onChange={(e) => onJdTextChange(e.target.value)}
          placeholder="Paste the full job description here — role title, requirements, responsibilities, qualifications..."
          className={cn(
            "w-full h-[280px] px-4 py-3 text-sm bg-zinc-50 border border-zinc-200 rounded-xl",
            "resize-none focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500",
            "placeholder:text-zinc-400 text-zinc-700 leading-relaxed",
            disabled && "opacity-50"
          )}
          disabled={disabled}
        />
      ) : (
        <div>
          {jdS3Key ? (
            <div className="flex items-center gap-3 px-4 py-3 bg-zinc-50 border border-zinc-200 rounded-xl">
              <FileText className="w-5 h-5 text-teal-600 shrink-0" />
              <span className="text-sm text-zinc-700 truncate flex-1">{jdFilename}</span>
              <button onClick={clearPdf} disabled={disabled}>
                <X className="w-4 h-4 text-zinc-400 hover:text-red-500" />
              </button>
            </div>
          ) : (
            <div
              className={cn(
                "border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all",
                "border-zinc-300 hover:border-zinc-400 hover:bg-zinc-50/50",
                uploading && "animate-pulse",
                disabled && "opacity-50 pointer-events-none"
              )}
              onClick={() => inputRef.current?.click()}
            >
              <Upload className="w-8 h-8 mx-auto mb-3 text-zinc-400" />
              <p className="text-sm font-medium text-zinc-700">
                {uploading ? "Uploading..." : "Upload JD as PDF"}
              </p>
              <p className="text-xs text-zinc-400 mt-1">PDF, up to 10 MB</p>
              <input
                ref={inputRef}
                type="file"
                accept=".pdf"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files?.[0]) handlePdfUpload(e.target.files[0]);
                  e.target.value = "";
                }}
                disabled={disabled}
              />
            </div>
          )}
        </div>
      )}

      {mode === "text" && jdText && (
        <p className="text-xs text-zinc-400 text-right">
          {jdText.length.toLocaleString()} characters
        </p>
      )}
    </div>
  );
}
