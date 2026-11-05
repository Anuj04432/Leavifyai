import { useState } from "react";
import { Sparkles, CheckCircle2, XCircle, AlertCircle, Loader2, BookOpen } from "lucide-react";
import { api } from "../../lib/api";

interface AIRecommendationProps {
  requestId: string;
  recommendation?: {
    decision?: "APPROVE" | "REJECT" | "NEEDS_REVIEW" | string;
    confidence_score?: number;
    reasoning?: string;
    policy_citations?: string[];
  } | null;
  onEvaluated?: () => void;
}

export default function AIRecommendationBadge({
  requestId,
  recommendation,
  onEvaluated,
}: AIRecommendationProps) {
  const [evaluating, setEvaluating] = useState(false);
  const [liveRec, setLiveRec] = useState(recommendation);

  const handleEvaluate = async () => {
    try {
      setEvaluating(true);
      const res = await api.post(`/agents/evaluate-request/${requestId}`);
      setLiveRec(res.data.recommendation);
      if (onEvaluated) onEvaluated();
    } catch (err) {
      console.error("Failed to generate AI evaluation", err);
    } finally {
      setEvaluating(false);
    }
  };

  const rec = liveRec || recommendation;

  if (!rec) {
    return (
      <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between text-xs">
        <div className="flex items-center gap-2 text-slate-400">
          <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
          <span>No AI evaluation generated yet.</span>
        </div>
        <button
          onClick={handleEvaluate}
          disabled={evaluating}
          className="px-2.5 py-1 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 rounded text-[11px] font-semibold flex items-center gap-1 transition cursor-pointer disabled:opacity-50"
        >
          {evaluating ? <Loader2 className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />}
          Run AI Review
        </button>
      </div>
    );
  }

  const decision = (rec.decision || "NEEDS_REVIEW").toUpperCase();
  const confidence = Math.round((rec.confidence_score || 0.95) * 100);

  return (
    <div className="p-3 rounded-lg bg-slate-950 border border-slate-800/90 space-y-2 text-xs">
      {/* Header with Decision Badge & Confidence */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
          <span className="font-semibold text-slate-200">AI Policy Copilot</span>

          {decision === "APPROVE" && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-mono font-bold">
              <CheckCircle2 className="w-3 h-3" /> APPROVE
            </span>
          )}
          {decision === "REJECT" && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20 text-[10px] font-mono font-bold">
              <XCircle className="w-3 h-3" /> REJECT
            </span>
          )}
          {decision !== "APPROVE" && decision !== "REJECT" && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[10px] font-mono font-bold">
              <AlertCircle className="w-3 h-3" /> NEEDS REVIEW
            </span>
          )}
        </div>

        <span className="text-[10px] font-mono text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
          {confidence}% Confidence
        </span>
      </div>

      {/* Reasoning Text */}
      {rec.reasoning && (
        <p className="text-[11px] text-slate-300 leading-relaxed">
          {rec.reasoning}
        </p>
      )}

      {/* Policy Rule Citations */}
      {rec.policy_citations && rec.policy_citations.length > 0 && (
        <div className="pt-1.5 border-t border-slate-900 flex flex-wrap items-center gap-1.5">
          <span className="text-[10px] font-mono text-slate-500 flex items-center gap-1">
            <BookOpen className="w-2.5 h-2.5" /> Citations:
          </span>
          {rec.policy_citations.map((cite, idx) => (
            <span
              key={idx}
              className="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-[10px] font-mono text-slate-400"
            >
              {cite}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
