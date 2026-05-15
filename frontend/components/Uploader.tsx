"use client";

import { useCallback, useRef, useState } from "react";
import { Upload, FileText, X, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { getPresignedUrl, uploadFileToS3, uploadResumesDirect } from "@/lib/api";
import type { UploadedFileInfo } from "@/lib/types";

interface UploaderProps {
  files: UploadedFileInfo[];
  onFilesChange: (files: UploadedFileInfo[]) => void;
  disabled?: boolean;
}

const ALLOWED_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
];
const MAX_SIZE = 10 * 1024 * 1024;

export default function Uploader({ files, onFilesChange, disabled }: UploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const addFiles = useCallback(
    async (incoming: FileList | File[]) => {
      const newFiles: UploadedFileInfo[] = [];
      for (const file of Array.from(incoming)) {
        if (!ALLOWED_TYPES.includes(file.type)) continue;
        if (file.size > MAX_SIZE) continue;
        if (files.some((f) => f.filename === file.name)) continue;

        const ext = file.name.toLowerCase().endsWith(".pdf") ? "pdf" : "docx";
        newFiles.push({
          filename: file.name,
          s3_key: "",
          size_bytes: file.size,
          file_type: ext as "pdf" | "docx",
          status: "pending",
          file,
        });
      }
      if (!newFiles.length) return;

      const merged = [...files, ...newFiles];
      onFilesChange(merged);

      // Upload each file
      for (const entry of newFiles) {
        const idx = merged.findIndex((f) => f.filename === entry.filename);
        try {
          merged[idx] = { ...merged[idx], status: "uploading" };
          onFilesChange([...merged]);

          const presigned = await getPresignedUrl(entry.filename, entry.file!.type);
          await uploadFileToS3(entry.file!, presigned);

          merged[idx] = { ...merged[idx], status: "done", s3_key: presigned.s3_key };
          onFilesChange([...merged]);
        } catch (err) {
          console.error("Upload failed for", entry.filename, err);
          // Fallback: try direct upload
          try {
            const result = await uploadResumesDirect([entry.file!]);
            if (result.uploaded.length > 0) {
              merged[idx] = {
                ...merged[idx],
                status: "done",
                s3_key: result.uploaded[0].s3_key,
              };
            } else {
              merged[idx] = { ...merged[idx], status: "error" };
            }
          } catch {
            merged[idx] = { ...merged[idx], status: "error" };
          }
          onFilesChange([...merged]);
        }
      }
    },
    [files, onFilesChange]
  );

  const removeFile = useCallback(
    (filename: string) => {
      onFilesChange(files.filter((f) => f.filename !== filename));
    },
    [files, onFilesChange]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (!disabled) addFiles(e.dataTransfer.files);
    },
    [addFiles, disabled]
  );

  const statusIcon = (status: UploadedFileInfo["status"]) => {
    switch (status) {
      case "uploading":
        return <Loader2 className="w-4 h-4 animate-spin text-amber-500" />;
      case "done":
        return <CheckCircle className="w-4 h-4 text-emerald-500" />;
      case "error":
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        return <div className="w-4 h-4 rounded-full bg-zinc-300" />;
    }
  };

  return (
    <div className="space-y-3">
      <div
        className={cn(
          "border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200",
          dragOver
            ? "border-teal-500 bg-teal-50/50"
            : "border-zinc-300 hover:border-zinc-400 hover:bg-zinc-50/50",
          disabled && "opacity-50 pointer-events-none"
        )}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <Upload className="w-8 h-8 mx-auto mb-3 text-zinc-400" />
        <p className="text-sm font-medium text-zinc-700">
          Drop resumes here or click to browse
        </p>
        <p className="text-xs text-zinc-400 mt-1">PDF or DOCX, up to 10 MB each</p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.docx"
          className="hidden"
          onChange={(e) => {
            if (e.target.files) addFiles(e.target.files);
            e.target.value = "";
          }}
          disabled={disabled}
        />
      </div>

      {files.length > 0 && (
        <div className="space-y-1.5 max-h-[240px] overflow-y-auto pr-1">
          {files.map((f) => (
            <div
              key={f.filename}
              className="flex items-center gap-2 px-3 py-2 bg-zinc-50 rounded-lg text-sm group"
            >
              <FileText className="w-4 h-4 text-zinc-400 shrink-0" />
              <span className="truncate flex-1 text-zinc-700">{f.filename}</span>
              <span className="text-xs text-zinc-400 shrink-0">
                {(f.size_bytes / 1024).toFixed(0)} KB
              </span>
              {statusIcon(f.status)}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  removeFile(f.filename);
                }}
                className="opacity-0 group-hover:opacity-100 transition-opacity"
                disabled={disabled}
              >
                <X className="w-4 h-4 text-zinc-400 hover:text-red-500" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
