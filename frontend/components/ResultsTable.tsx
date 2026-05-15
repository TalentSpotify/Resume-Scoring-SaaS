"use client";

import { useState } from "react";
import { Users, TrendingUp, XCircle, Award, Code2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ProcessResponse } from "@/lib/types";
import CandidateCard from "./CandidateCard";

interface ResultsTableProps {
  result: ProcessResponse;
}

function StatCard({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: typeof Users;
  label: string;
  value: string | number;
  color: string;
}) {
  return (
    <div className="flex items-center gap-3 px-4 py-3 bg-white border border-zinc-200 rounded-xl">
      <div className={cn("p-2 rounded-lg", color)}>
        <Icon className="w-4 h-4" />
      </div>
      <div>
        <p className="text-xs text-zinc-500">{label}</p>
        <p className="text-lg font-bold text-zinc-900">{value}</p>
      </div>
    </div>
  );
}

export default function ResultsTable({ result }: ResultsTableProps) {
  const [filter, setFilter] = useState<"all" | "strong_match" | "shortlist" | "reject">(
    "all"
  );
  const [showJson, setShowJson] = useState(false);
  const stats = result.summary_stats;

  const filtered =
    filter === "all"
      ? result.candidates
      : result.candidates.filter((c) => c.filter_decision === filter);

  return (
    <div className="space-y-5">
      {/* Summary stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard
          icon={Users}
          label="Total"
          value={stats.total_candidates}
          color="bg-zinc-100 text-zinc-600"
        />
        <StatCard
          icon={Award}
          label="Strong Match"
          value={stats.strong_match_count}
          color="bg-emerald-50 text-emerald-600"
        />
        <StatCard
          icon={TrendingUp}
          label="Shortlisted"
          value={stats.shortlist_count}
          color="bg-amber-50 text-amber-600"
        />
        <StatCard
          icon={XCircle}
          label="Rejected"
          value={stats.reject_count}
          color="bg-red-50 text-red-600"
        />
      </div>

      {/* Score range */}
      <div className="flex items-center gap-4 text-xs text-zinc-500">
        <span>
          Avg: <strong className="text-zinc-700">{stats.avg_score.toFixed(1)}</strong>
        </span>
        <span>
          Range:{" "}
          <strong className="text-zinc-700">
            {stats.min_score.toFixed(1)} — {stats.max_score.toFixed(1)}
          </strong>
        </span>
        <span>
          Run: <strong className="text-zinc-700 font-mono">{result.run_id}</strong>
        </span>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2">
        {(["all", "strong_match", "shortlist", "reject"] as const).map((f) => {
          const labels = {
            all: "All",
            strong_match: "Strong Match",
            shortlist: "Shortlist",
            reject: "Rejected",
          };
          return (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={cn(
                "px-3 py-1.5 text-xs font-medium rounded-lg transition-all",
                filter === f
                  ? "bg-zinc-900 text-white"
                  : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200"
              )}
            >
              {labels[f]}
            </button>
          );
        })}
        <div className="flex-1" />
        <button
          onClick={() => setShowJson(!showJson)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-zinc-100 text-zinc-600 rounded-lg hover:bg-zinc-200 transition-all"
        >
          <Code2 className="w-3.5 h-3.5" />
          {showJson ? "Hide JSON" : "View JSON"}
        </button>
      </div>

      {/* JSON viewer */}
      {showJson && (
        <div className="bg-zinc-900 rounded-xl p-4 overflow-auto max-h-[400px]">
          <pre className="text-xs text-zinc-300 font-mono whitespace-pre-wrap">
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}

      {/* Candidate cards */}
      <div className="space-y-2">
        {filtered.map((c, i) => (
          <CandidateCard key={c.candidate_id} candidate={c} index={i} />
        ))}
        {filtered.length === 0 && (
          <p className="text-sm text-zinc-400 text-center py-8">
            No candidates match this filter.
          </p>
        )}
      </div>
    </div>
  );
}
