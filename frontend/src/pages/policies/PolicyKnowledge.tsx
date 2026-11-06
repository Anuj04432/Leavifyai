import { useState, useEffect } from "react";
import {
  BookOpen,
  FileCode,
  ShieldCheck,
  Calendar,
  Clock,
  Save,
  CheckCircle2,
  Loader2,
  AlertCircle,
  Tag,
} from "lucide-react";
import { api } from "../../lib/api";
import { useAuthStore } from "../../store/authStore";
import Navbar from "../../components/layout/Navbar";

interface OKFPolicy {
  policy_code: string;
  title: string;
  leave_type: string;
  annual_allowance: number;
  max_consecutive_days: number;
  notice_period_days: number;
  is_paid: boolean;
  carryover_limit: number;
  requires_manager_approval: boolean;
  tags: string[];
  last_updated: string;
  metadata: Record<string, any>;
  markdown_content: string;
  filename: string;
}

export default function PolicyKnowledge() {
  const { user } = useAuthStore();
  const [policies, setPolicies] = useState<OKFPolicy[]>([]);
  const [selectedCode, setSelectedCode] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);
  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [editedContent, setEditedContent] = useState<string>("");
  const [saving, setSaving] = useState<boolean>(false);
  const [saveSuccess, setSaveSuccess] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const isHrOrAdmin = user?.role === "admin" || user?.role === "hr";

  useEffect(() => {
    fetchPolicies();
  }, []);

  const fetchPolicies = async () => {
    try {
      setLoading(true);
      const res = await api.get("/policies/knowledge");
      setPolicies(res.data);
      if (res.data.length > 0 && !selectedCode) {
        setSelectedCode(res.data[0].policy_code);
        setEditedContent(res.data[0].markdown_content);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load policy knowledge base.");
    } finally {
      setLoading(false);
    }
  };

  const activePolicy = policies.find((p) => p.policy_code === selectedCode);

  const handleSelectPolicy = (code: string) => {
    setSelectedCode(code);
    setIsEditing(false);
    setSaveSuccess(false);
    const pol = policies.find((p) => p.policy_code === code);
    if (pol) {
      setEditedContent(pol.markdown_content);
    }
  };

  const handleSavePolicy = async () => {
    if (!activePolicy) return;
    try {
      setSaving(true);
      setError(null);
      const res = await api.put(`/policies/knowledge/${activePolicy.policy_code}`, {
        markdown_content: editedContent,
      });

      setPolicies((prev) =>
        prev.map((p) => (p.policy_code === activePolicy.policy_code ? res.data : p))
      );
      setIsEditing(false);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to update policy.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans antialiased">
      <Navbar />

      <main className="flex-1 p-6 max-w-7xl w-full mx-auto space-y-6">
        {/* Title Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-indigo-400" />
              Open Knowledge Format (OKF) Policy Repository
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Authoritative, deterministic Markdown & YAML policy contracts grounding the Agentic AI Supervisor.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono px-2.5 py-1 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-semibold uppercase">
              OKF Grounding Active
            </span>
          </div>
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Asymmetric 4:8 Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* 4-Column Policy Navigation Rail */}
          <div className="lg:col-span-4 space-y-3">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5 px-1">
              <FileCode className="w-4 h-4 text-indigo-400" />
              Company Policy Documents ({policies.length})
            </div>

            {loading ? (
              <div className="p-12 rounded-xl bg-slate-900 border border-slate-800 flex flex-col items-center justify-center gap-2">
                <Loader2 className="w-5 h-5 animate-spin text-indigo-500" />
                <span className="text-xs text-slate-400 font-mono">Loading OKF bundles...</span>
              </div>
            ) : (
              <div className="space-y-2">
                {policies.map((p) => {
                  const isSelected = p.policy_code === selectedCode;
                  return (
                    <button
                      key={p.policy_code}
                      onClick={() => handleSelectPolicy(p.policy_code)}
                      className={`w-full p-3.5 rounded-xl text-left transition cursor-pointer border ${
                        isSelected
                          ? "bg-slate-900 border-indigo-500/50 shadow-md text-white"
                          : "bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-900/60"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2 mb-1.5">
                        <span className="text-xs font-bold text-white tracking-tight">
                          {p.title}
                        </span>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-bold">
                          {p.policy_code}
                        </span>
                      </div>

                      <div className="grid grid-cols-3 gap-2 text-[10px] font-mono text-slate-400 pt-1 border-t border-slate-800/60">
                        <div>
                          <span className="text-slate-500 block">Type</span>
                          <span className="text-slate-300 capitalize">{p.leave_type}</span>
                        </div>
                        <div>
                          <span className="text-slate-500 block">Status</span>
                          <span className={p.is_paid ? "text-emerald-400" : "text-amber-400"}>
                            {p.is_paid ? "Paid" : "Loss of Pay"}
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-500 block">Allowance</span>
                          <span className="text-slate-200">{p.annual_allowance}d / yr</span>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* 8-Column Active Policy Viewer & Editor */}
          <div className="lg:col-span-8 space-y-4">
            {activePolicy ? (
              <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                {/* Header with YAML Metadata Pills */}
                <div className="p-4 border-b border-slate-800 bg-slate-950/40 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-base font-bold text-white">{activePolicy.title}</h2>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-bold">
                        {activePolicy.policy_code}
                      </span>
                    </div>
                    <div className="flex flex-wrap items-center gap-3 text-[11px] font-mono text-slate-400 mt-1.5">
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5 text-slate-500" />
                        Allowance: {activePolicy.annual_allowance}d
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5 text-slate-500" />
                        Notice: {activePolicy.notice_period_days}d
                      </span>
                      <span className="flex items-center gap-1">
                        <ShieldCheck className="w-3.5 h-3.5 text-slate-500" />
                        Max Block: {activePolicy.max_consecutive_days}d
                      </span>
                    </div>
                  </div>

                  {isHrOrAdmin && (
                    <div className="flex items-center gap-2">
                      {isEditing ? (
                        <>
                          <button
                            onClick={() => {
                              setIsEditing(false);
                              setEditedContent(activePolicy.markdown_content);
                            }}
                            disabled={saving}
                            className="px-3 py-1.5 rounded-lg border border-slate-800 text-slate-400 hover:text-white text-xs font-medium cursor-pointer"
                          >
                            Cancel
                          </button>
                          <button
                            onClick={handleSavePolicy}
                            disabled={saving}
                            className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer shadow-sm disabled:opacity-50"
                          >
                            {saving ? (
                              <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            ) : (
                              <Save className="w-3.5 h-3.5" />
                            )}
                            Save Changes
                          </button>
                        </>
                      ) : (
                        <button
                          onClick={() => setIsEditing(true)}
                          className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white rounded-lg text-xs font-medium transition cursor-pointer"
                        >
                          Edit Markdown
                        </button>
                      )}
                    </div>
                  )}
                </div>

                {saveSuccess && (
                  <div className="p-3 bg-emerald-500/10 border-b border-emerald-500/20 text-emerald-400 text-xs flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Policy rules updated successfully. Agent knowledge synchronized.</span>
                  </div>
                )}

                {/* YAML Frontmatter View */}
                <div className="p-4 bg-slate-950/70 border-b border-slate-800/80 font-mono text-[11px] space-y-1">
                  <div className="text-slate-500 text-[10px] uppercase font-bold tracking-wider mb-1 flex items-center gap-1">
                    <Tag className="w-3 h-3 text-indigo-400" />
                    Parsed YAML Frontmatter Metadata
                  </div>
                  <pre className="text-slate-300 overflow-x-auto p-2 bg-slate-950 rounded border border-slate-900">
                    {JSON.stringify(activePolicy.metadata, null, 2)}
                  </pre>
                </div>

                {/* Document Body */}
                <div className="p-5">
                  {isEditing ? (
                    <div className="space-y-2">
                      <label className="text-[11px] font-semibold text-slate-400 block font-mono">
                        Markdown Document Body:
                      </label>
                      <textarea
                        rows={14}
                        value={editedContent}
                        onChange={(e) => setEditedContent(e.target.value)}
                        className="w-full p-3 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 text-xs font-mono focus:outline-none focus:border-indigo-500 leading-relaxed resize-y"
                      />
                    </div>
                  ) : (
                    <div className="prose prose-invert max-w-none text-xs leading-relaxed text-slate-300 whitespace-pre-wrap font-sans">
                      {activePolicy.markdown_content}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="p-16 rounded-xl bg-slate-900 border border-slate-800 text-center space-y-2">
                <BookOpen className="w-8 h-8 text-slate-600 mx-auto" />
                <span className="text-xs text-slate-400 block">Select a policy from the left to view.</span>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
