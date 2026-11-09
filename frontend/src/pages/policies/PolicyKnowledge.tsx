import { useState, useEffect, FormEvent } from "react";
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
  Upload,
  X,
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

  // Upload Policy State
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadForm, setUploadForm] = useState({
    title: "",
    leave_type: "",
    annual_allowance: 12,
    notice_period_days: 2,
    max_consecutive_days: 5,
    is_paid: true,
  });
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const isHrOrAdmin =
    user?.role === "admin" ||
    user?.role === "hr" ||
    user?.role === "hr_manager" ||
    user?.role === "super_admin" ||
    user?.role === "ceo" ||
    user?.role === "content_manager" ||
    !!user?.permissions?.can_manage_policies;

  useEffect(() => {
    fetchPolicies();
  }, []);

  const extractErrorMessage = (err: any, fallback: string): string => {
    const detail = err?.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((d: any) => d.msg || JSON.stringify(d)).join(", ");
    }
    if (typeof detail === "object" && detail !== null) {
      return JSON.stringify(detail);
    }
    return err?.message || fallback;
  };

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
      setError(extractErrorMessage(err, "Failed to load policy knowledge base."));
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
      setError(extractErrorMessage(err, "Failed to update policy."));
    } finally {
      setSaving(false);
    }
  };

  const handleUploadPolicy = async (e: FormEvent) => {
    e.preventDefault();
    if (!uploadFile) {
      setUploadError("Please select a policy document file (.pdf, .md, or .txt).");
      return;
    }
    try {
      setUploading(true);
      setUploadError(null);
      const fd = new FormData();
      fd.append("file", uploadFile);
      if (uploadForm.title) fd.append("title", uploadForm.title);
      if (uploadForm.leave_type) fd.append("leave_type", uploadForm.leave_type);
      fd.append("annual_allowance", String(uploadForm.annual_allowance));
      fd.append("notice_period_days", String(uploadForm.notice_period_days));
      fd.append("max_consecutive_days", String(uploadForm.max_consecutive_days));
      fd.append("is_paid", String(uploadForm.is_paid));

      const res = await api.post("/policies/knowledge/upload", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setShowUploadModal(false);
      setUploadFile(null);
      setUploadForm({
        title: "",
        leave_type: "",
        annual_allowance: 12,
        notice_period_days: 2,
        max_consecutive_days: 5,
        is_paid: true,
      });
      await fetchPolicies();
      if (res.data?.policy_code) {
        setSelectedCode(res.data.policy_code);
        setEditedContent(res.data.markdown_content || "");
      }
    } catch (err: any) {
      setUploadError(extractErrorMessage(err, "Failed to upload policy document."));
    } finally {
      setUploading(false);
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
            {isHrOrAdmin && (
              <button
                type="button"
                onClick={() => {
                  setUploadError(null);
                  setShowUploadModal(true);
                }}
                className="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs flex items-center gap-1.5 transition-colors motion-reduce:transition-none cursor-pointer shadow-sm"
              >
                <Upload className="w-3.5 h-3.5" />
                Upload Policy Document
              </button>
            )}
            <span className="text-xs px-2.5 py-1 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-medium">
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
            <div className="text-xs font-semibold text-slate-300 flex items-center gap-1.5 px-1">
              <FileCode className="w-4 h-4 text-indigo-400" />
              Company Policy Documents ({policies.length})
            </div>

            {loading ? (
              <div className="p-12 rounded-xl bg-slate-900 border border-slate-800 flex flex-col items-center justify-center gap-2">
                <Loader2 className="w-5 h-5 animate-spin text-indigo-500" />
                <span className="text-xs text-slate-400">Loading OKF bundles…</span>
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
                <div className="p-4 bg-slate-950/70 border-b border-slate-800/80 text-xs space-y-1">
                  <div className="text-slate-400 text-xs font-semibold mb-1 flex items-center gap-1">
                    <Tag className="w-3 h-3 text-indigo-400" />
                    Parsed YAML Frontmatter Metadata
                  </div>
                  <pre className="text-slate-300 font-mono text-[11px] overflow-x-auto p-2 bg-slate-950 rounded border border-slate-900">
                    {JSON.stringify(activePolicy.metadata, null, 2)}
                  </pre>
                </div>

                {/* Document Body */}
                <div className="p-5">
                  {isEditing ? (
                    <div className="space-y-2">
                      <label className="text-xs font-semibold text-slate-400 block mb-1">
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

      {/* Upload Policy Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/90 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Upload className="w-4 h-4 text-indigo-400" />
                Upload Company Leave Policy
              </h2>
              <button
                onClick={() => setShowUploadModal(false)}
                className="text-slate-400 hover:text-white transition cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {uploadError && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{uploadError}</span>
              </div>
            )}

            <form onSubmit={handleUploadPolicy} className="space-y-3.5 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">
                  Policy Document File (.pdf, .md, or .txt) *
                </label>
                <input
                  type="file"
                  required
                  accept=".pdf,.md,.txt"
                  onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-300 text-xs file:mr-3 file:py-1 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-indigo-600 file:text-white hover:file:bg-indigo-500 file:cursor-pointer"
                />
                <p className="text-[11px] text-slate-500 mt-1">
                  Upload PDF handbooks, OKF Markdown with YAML headers, or plain text. Multi-page PDFs will be extracted, chunked, and embedded into RAG automatically.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">
                    Policy Title
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Parental Leave"
                    value={uploadForm.title}
                    onChange={(e) => setUploadForm({ ...uploadForm, title: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-slate-200 outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">
                    Leave Type Slug
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. parental"
                    value={uploadForm.leave_type}
                    onChange={(e) => setUploadForm({ ...uploadForm, leave_type: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, "") })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-slate-200 outline-none focus:border-indigo-500 font-mono"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">
                    Annual Entitlement
                  </label>
                  <input
                    type="number"
                    min={0}
                    value={uploadForm.annual_allowance}
                    onChange={(e) => setUploadForm({ ...uploadForm, annual_allowance: Number(e.target.value) })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-slate-200 outline-none focus:border-indigo-500 font-mono"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">
                    Notice Days
                  </label>
                  <input
                    type="number"
                    min={0}
                    value={uploadForm.notice_period_days}
                    onChange={(e) => setUploadForm({ ...uploadForm, notice_period_days: Number(e.target.value) })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-slate-200 outline-none focus:border-indigo-500 font-mono"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">
                    Max Consecutive
                  </label>
                  <input
                    type="number"
                    min={1}
                    value={uploadForm.max_consecutive_days}
                    onChange={(e) => setUploadForm({ ...uploadForm, max_consecutive_days: Number(e.target.value) })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-slate-200 outline-none focus:border-indigo-500 font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">
                  Remuneration Type
                </label>
                <select
                  value={uploadForm.is_paid ? "true" : "false"}
                  onChange={(e) => setUploadForm({ ...uploadForm, is_paid: e.target.value === "true" })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-slate-200 outline-none focus:border-indigo-500"
                >
                  <option value="true">Paid Leave (Full Remuneration)</option>
                  <option value="false">Unpaid Leave (Loss of Pay / LOP applies)</option>
                </select>
              </div>

              <div className="pt-3 flex justify-end gap-2.5 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium transition cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={uploading}
                  className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium flex items-center gap-1.5 transition cursor-pointer disabled:opacity-50"
                >
                  {uploading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Deploy Policy to OKF
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
