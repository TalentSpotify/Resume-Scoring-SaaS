"use client";

import { useState } from "react";
import {
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  XCircle,
  MinusCircle,
  MapPin,
  Award,
  BarChart3,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { CandidateResult, FilterDecision } from "@/lib/types";

const DECISION_CONFIG: Record<
  FilterDecision,
  { label: string; color: string; bg: string; icon: typeof CheckCircle2 }
> = {
  strong_match: {
    label: "Strong Match",
    color: "text-emerald-700",
    bg: "bg-emerald-50 border-emerald-200",
    icon: CheckCircle2,
  },
  shortlist: {
    label: "Shortlist",
    color: "text-amber-700",
    bg: "bg-amber-50 border-amber-200",
    icon: MinusCircle,
  },
  reject: {
    label: "Reject",
    color: "text-red-700",
    bg: "bg-red-50 border-red-200",
    icon: XCircle,
  },
};

function ScoreBar({ label, score }: { label: string; score: number }) {
  const color =
    score >= 80 ? "bg-emerald-500" : score >= 60 ? "bg-amber-500" : "bg-red-400";
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-zinc-500">{label}</span>
        <span className="font-medium text-zinc-700">{score.toFixed(1)}</span>
      </div>
      <div className="h-1.5 bg-zinc-100 rounded-full overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all duration-500", color)}
          style={{ width: `${Math.min(score, 100)}%` }}
        />
      </div>
    </div>
  );
}

interface CandidateCardProps {
  candidate: CandidateResult;
  index: number;
}

export default function CandidateCard({ candidate: c, index }: CandidateCardProps) {
  const [expanded, setExpanded] = useState(false);
  const cfg = DECISION_CONFIG[c.filter_decision];
  const Icon = cfg.icon;

  return (
    <div
      className={cn(
        "border rounded-xl overflow-hidden transition-all duration-200",
        cfg.bg
      )}
    >
      {/* Header */}
      <button
        className="w-full flex items-center gap-3 px-4 py-3 text-left"
        onClick={() => setExpanded(!expanded)}
      >
        <span className="flex items-center justify-center w-7 h-7 rounded-full bg-white/70 text-xs font-bold text-zinc-600 shrink-0">
          {c.rank}
        </span>
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-zinc-900 text-sm truncate">
            {c.candidate_name}
          </p>
          <p className="text-xs text-zinc-500 truncate">
            {c.metadata.resume_filename}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <div className="text-right">
            <p className="text-lg font-bold text-zinc-900">{c.overall_score.toFixed(1)}</p>
            <div className={cn("flex items-center gap-1 text-xs font-medium", cfg.color)}>
              <Icon className="w-3 h-3" />
              {cfg.label}
            </div>
          </div>
          {expanded ? (
            <ChevronUp className="w-4 h-4 text-zinc-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-zinc-400" />
          )}
        </div>
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="px-4 pb-4 space-y-4 border-t border-white/50">
          {/* Sub-scores */}
          <div className="pt-3 space-y-2">
            <h4 className="text-xs font-semibold text-zinc-600 uppercase tracking-wider flex items-center gap-1.5">
              <BarChart3 className="w-3.5 h-3.5" />
              Score Breakdown
            </h4>
            <div className="grid gap-2">
              <ScoreBar label="LLM Score" score={c.subscores.llm_score} />
              <ScoreBar label="Keyword Relevance" score={c.subscores.keyword_relevance_score} />
              <ScoreBar label="Skill Fit" score={c.subscores.skill_fit_score} />
              <ScoreBar label="Experience Fit" score={c.subscores.experience_fit_score} />
              <ScoreBar label="Domain Fit" score={c.subscores.domain_fit_score} />
            </div>
          </div>

          {/* Location */}
          {c.location_match && (
            <div className="flex items-center gap-1.5 text-xs text-zinc-600">
              <MapPin className="w-3.5 h-3.5" />
              Location: {c.location_match}
            </div>
          )}

          {/* Matched requirements */}
          {c.matched_requirements.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-zinc-600 uppercase tracking-wider flex items-center gap-1.5 mb-1.5">
                <Award className="w-3.5 h-3.5" />
                Matched Requirements
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {c.matched_requirements.map((r, i) => (
                  <span
                    key={i}
                    className="px-2 py-0.5 text-xs bg-emerald-100 text-emerald-700 rounded-full"
                  >
                    {r}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Missing requirements */}
          {c.missing_requirements.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-zinc-600 uppercase tracking-wider mb-1.5">
                Missing Requirements
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {c.missing_requirements.map((r, i) => (
                  <span
                    key={i}
                    className="px-2 py-0.5 text-xs bg-red-100 text-red-700 rounded-full"
                  >
                    {r}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* LLM Explanation */}
          {c.llm_explanation && (
            <div>
              <h4 className="text-xs font-semibold text-zinc-600 uppercase tracking-wider mb-1.5">
                Analysis
              </h4>
              <p className="text-xs text-zinc-600 leading-relaxed bg-white/50 rounded-lg p-3">
                {c.llm_explanation}
              </p>
            </div>
          )}

          {/* Confidence */}
          {c.confidence > 0 && (
            <p className="text-xs text-zinc-400">
              Confidence: {(c.confidence * 100).toFixed(0)}%
            </p>
          )}
        </div>
      )}
    </div>
  );
}
