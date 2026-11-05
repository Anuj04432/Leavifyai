import { useState, useEffect, useMemo } from "react";
import {
  CheckSquare,
  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Check,
  X,
  Loader2,
  ShieldAlert,
  UserCheck,
  Calendar,
  RefreshCw,
  Search,
} from "lucide-react";
import { api } from "../../lib/api";
import Navbar from "../../components/layout/Navbar";
import AIRecommendationBadge from "../../components/hr/AIRecommendationBadge";

interface LeaveRequest {
  id: string;
  request_number: string;
  employee_id: string;
  employee_name?: string;
  employee_code?: string;
  leave_policy_id: string;
  policy_name?: string;
  leave_type?: string;
  start_date: string;
  end_date: string;
  total_days: number | string;
  reason?: string;
  status: "pending" | "approved" | "rejected";
  is_paid: boolean;
  source_channel: string;
  ai_recommendation?: Record<string, any>;
  ai_confidence_score?: number | null;
  reviewed_at?: string;
  review_comment?: string;
  created_at: string;
}

export default function ApprovalCockpit() {
  const [requests, setRequests] = useState<LeaveRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("pending");
  const [search, setSearch] = useState("");

  // Actioning Modal
  const [actioningRequest, setActioningRequest] = useState<LeaveRequest | null>(null);
  const [actionType, setActionType] = useState<"approve" | "reject">("approve");
  const [actionComment, setActionComment] = useState("");
  const [processing, setProcessing] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const fetchRequests = async () => {
    try {
      setLoading(true);
      const res = await api.get("/leaves/requests");
      setRequests(res.data);
    } catch (err) {
      console.error("Failed to load approval queue", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRequests();
  }, []);

  const handleProcessDecision = async () => {
    if (!actioningRequest) return;
    setActionError(null);

    try {
      setProcessing(true);
      await api.patch(`/leaves/requests/${actioningRequest.id}/action`, {
        action: actionType,
        comment: actionComment.trim() || undefined,
      });

      setActioningRequest(null);
      setActionComment("");
      await fetchRequests();
    } catch (err: any) {
      // Handles optimistic locking 409 Conflict
      setActionError(
        err.response?.data?.detail || "Action failed due to an unexpected error or concurrency conflict."
      );
    } finally {
      setProcessing(false);
    }
  };

  const filteredRequests = useMemo(() => {
    return requests.filter((r) => {
      const matchStatus = statusFilter === "all" ? true : r.status === statusFilter;
      const matchSearch =
        search === "" ||
        (r.employee_name && r.employee_name.toLowerCase().includes(search.toLowerCase())) ||
        (r.employee_code && r.employee_code.toLowerCase().includes(search.toLowerCase())) ||
        r.request_number.toLowerCase().includes(search.toLowerCase());
      return matchStatus && matchSearch;
    });
  }, [requests, statusFilter, search]);

  const pendingCount = requests.filter((r) => r.status === "pending").length;
  const approvedCount = requests.filter((r) => r.status === "approved").length;
  const rejectedCount = requests.filter((r) => r.status === "rejected").length;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans antialiased">
      <Navbar />

      <main className="flex-1 p-6 max-w-7xl w-full mx-auto space-y-6">
        {/* Title Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              <CheckSquare className="w-5 h-5 text-indigo-400" />
              HR & Manager Approval Cockpit
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Review organization-wide leave applications, audit decisions, and enforce policy compliance.
            </p>
          </div>

          <button
            onClick={fetchRequests}
            title="Refresh queue"
            className="px-3 py-1.5 bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 rounded-lg text-xs font-medium flex items-center gap-1.5 transition cursor-pointer self-start sm:self-auto"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            Sync Queue
          </button>
        </div>

        {/* PASS 1: Asymmetric 8:4 Structural Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Main 8-Column Review Queue */}
          <div className="lg:col-span-8 space-y-4">
            {/* Triage Search & Filter Tabs */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
              <div className="flex items-center gap-1">
                {[
                  { id: "pending", label: "Pending Triage", count: pendingCount },
                  { id: "approved", label: "Approved", count: approvedCount },
                  { id: "rejected", label: "Rejected", count: rejectedCount },
                  { id: "all", label: "All Submissions", count: requests.length },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setStatusFilter(tab.id)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition cursor-pointer flex items-center gap-1.5 ${
                      statusFilter === tab.id
                        ? "bg-slate-800 text-white border border-slate-700"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    <span>{tab.label}</span>
                    <span
                      className={`text-[10px] font-mono px-1.5 py-0.2 rounded-full ${
                        statusFilter === tab.id
                          ? "bg-indigo-600/30 text-indigo-300"
                          : "bg-slate-800 text-slate-500"
                      }`}
                    >
                      {tab.count}
                    </span>
                  </button>
                ))}
              </div>

              <div className="relative">
                <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Filter applicant or ID..."
                  className="bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-lg pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 outline-none w-full sm:w-48 transition"
                />
              </div>
            </div>

            {/* Applications List */}
            {loading ? (
              <div className="p-16 rounded-xl bg-slate-900 border border-slate-800 flex flex-col items-center justify-center gap-2">
                <Loader2 className="w-6 h-6 animate-spin text-indigo-500" />
                <span className="text-xs font-mono text-slate-400">Loading leave triage records...</span>
              </div>
            ) : filteredRequests.length === 0 ? (
              <div className="p-14 rounded-xl bg-slate-900 border border-slate-800 text-center space-y-2">
                <UserCheck className="w-8 h-8 text-slate-600 mx-auto" />
                <div className="text-sm font-semibold text-slate-300">Queue is completely clear</div>
                <p className="text-xs text-slate-500 max-w-sm mx-auto">
                  No applications are currently awaiting action under this view.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {filteredRequests.map((req) => (
                  <div
                    key={req.id}
                    className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3 hover:border-slate-700/80 transition"
                  >
                    {/* Header Row */}
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-bold text-indigo-400">
                            {req.request_number}
                          </span>
                          <span className="text-slate-600">•</span>
                          <span className="text-xs font-semibold text-white">
                            {req.employee_name || "Applicant"}
                          </span>
                          {req.employee_code && (
                            <span className="text-[10px] font-mono text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded">
                              {req.employee_code}
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-3 text-[11px] text-slate-400 mt-1">
                          <span className="text-slate-300 font-medium">{req.policy_name}</span>
                          <span>•</span>
                          <span>{req.is_paid ? "Paid Leave" : "Unpaid Leave"}</span>
                          <span>•</span>
                          <span className="font-mono">{req.start_date} to {req.end_date}</span>
                        </div>
                      </div>

                      <div className="text-right">
                        <div className="text-sm font-bold font-mono text-white">
                          {req.total_days} business day{Number(req.total_days) !== 1 ? "s" : ""}
                        </div>
                        <div className="mt-0.5">
                          {req.status === "approved" && (
                            <span className="inline-flex items-center gap-1 text-emerald-400 text-[11px] font-medium">
                              <CheckCircle2 className="w-3.5 h-3.5" /> Approved
                            </span>
                          )}
                          {req.status === "rejected" && (
                            <span className="inline-flex items-center gap-1 text-rose-400 text-[11px] font-medium">
                              <XCircle className="w-3.5 h-3.5" /> Rejected
                            </span>
                          )}
                          {req.status === "pending" && (
                            <span className="inline-flex items-center gap-1 text-amber-400 text-[11px] font-medium">
                              <Clock className="w-3.5 h-3.5 animate-pulse" /> Pending Action
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Applicant Context / Reason */}
                    {req.reason && (
                      <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800/80 text-xs text-slate-300">
                        <span className="text-slate-500 font-mono text-[10px] block mb-0.5">APPLICANT NOTE</span>
                        "{req.reason}"
                      </div>
                    )}

                    {/* Live AI Recommendation Engine */}
                    <AIRecommendationBadge
                      requestId={req.id}
                      recommendation={req.ai_recommendation}
                      onEvaluated={fetchRequests}
                    />

                    {/* Action Buttons for Pending Requests */}
                    {req.status === "pending" && (
                      <div className="flex items-center justify-end gap-2 pt-1 border-t border-slate-800/80">
                        <button
                          onClick={() => {
                            setActioningRequest(req);
                            setActionType("reject");
                            setActionError(null);
                          }}
                          className="px-3 py-1.5 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer"
                        >
                          <X className="w-3.5 h-3.5" />
                          Reject
                        </button>
                        <button
                          onClick={() => {
                            setActioningRequest(req);
                            setActionType("approve");
                            setActionError(null);
                          }}
                          className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer shadow-sm"
                        >
                          <Check className="w-3.5 h-3.5" />
                          Approve Request
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 4-Column Contextual Intelligence Rail */}
          <div className="lg:col-span-4 space-y-4">
            {/* Triage Overview Card */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
              <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                <ShieldAlert className="w-4 h-4 text-indigo-400" />
                Triage Overview
              </span>

              <div className="space-y-2 text-xs">
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between">
                  <span className="text-slate-400">Awaiting Decision</span>
                  <span className="font-mono text-amber-400 font-bold text-sm">{pendingCount}</span>
                </div>
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between">
                  <span className="text-slate-400">Total Reviewed</span>
                  <span className="font-mono text-slate-200 font-semibold">{approvedCount + rejectedCount}</span>
                </div>
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between">
                  <span className="text-slate-400">Concurrency Guard</span>
                  <span className="inline-flex items-center gap-1 text-emerald-400 text-[10px] font-mono">
                    <CheckCircle2 className="w-3 h-3" /> Optimistic Locking Active
                  </span>
                </div>
              </div>
            </div>

            {/* Approval Guardrails Policy */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
              <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                <Calendar className="w-4 h-4 text-indigo-400" />
                Compliance Guardrails
              </span>

              <div className="text-xs text-slate-400 space-y-2">
                <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                  <span className="font-semibold text-slate-200 block mb-0.5">Automatic Ledger Sync</span>
                  Approving deducts pending days and marks them as used. Rejecting restores days immediately.
                </div>
                <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                  <span className="font-semibold text-slate-200 block mb-0.5">Audit Trail Retention</span>
                  Every decision, timestamp, and review comment is recorded permanently in the forensic audit ledger.
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Decision Action Modal */}
      {actioningRequest && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h2 className="text-base font-bold text-white capitalize flex items-center gap-2">
                {actionType === "approve" ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                ) : (
                  <XCircle className="w-4 h-4 text-rose-400" />
                )}
                {actionType} Leave Request
              </h2>
              <button
                onClick={() => setActioningRequest(null)}
                className="text-slate-400 hover:text-white transition cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {actionError && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{actionError}</span>
              </div>
            )}

            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs space-y-1">
              <div className="flex justify-between">
                <span className="text-slate-400">Applicant:</span>
                <span className="font-semibold text-white">{actioningRequest.employee_name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Policy:</span>
                <span className="text-slate-200">{actioningRequest.policy_name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Duration:</span>
                <span className="font-mono text-indigo-400 font-bold">{actioningRequest.total_days} business days</span>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Reviewer Comment / Condition
              </label>
              <textarea
                value={actionComment}
                onChange={(e) => setActionComment(e.target.value)}
                placeholder={
                  actionType === "approve"
                    ? "Optional notes (e.g., Handover completed to peer)..."
                    : "Specify reason for rejection..."
                }
                rows={3}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-white focus:border-indigo-500 outline-none resize-none"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setActioningRequest(null)}
                className="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleProcessDecision}
                disabled={processing}
                className={`px-4 py-1.5 rounded-lg text-xs font-semibold text-white flex items-center gap-1.5 transition cursor-pointer disabled:opacity-50 ${
                  actionType === "approve"
                    ? "bg-emerald-600 hover:bg-emerald-500"
                    : "bg-rose-600 hover:bg-rose-500"
                }`}
              >
                {processing && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                Confirm {actionType}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
