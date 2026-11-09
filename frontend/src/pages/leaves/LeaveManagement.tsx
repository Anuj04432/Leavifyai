import { useState, useEffect, useMemo, FormEvent } from "react";
import { Link } from "react-router-dom";
import {
  Calendar,
  Clock,
  CheckCircle2,
  AlertCircle,
  Plus,
  ShieldCheck,
  Loader2,
  X,
  Check,
  CalendarDays,
  Info,
  BookOpen,
  Upload,
} from "lucide-react";
import { api } from "../../lib/api";
import { useAuthStore } from "../../store/authStore";
import Navbar from "../../components/layout/Navbar";

interface LeavePolicy {
  id: string;
  name: string;
  leave_type: string;
  days_allowed: number;
  carry_forward: boolean;
  max_carry_forward_days: number;
  is_paid: boolean;
  approval_required: boolean;
}

interface LeaveBalance {
  id: string;
  leave_policy_id: string;
  year: number;
  total_allocated: number | string;
  used: number | string;
  pending: number | string;
  carried_forward: number | string;
  available: number | string;
  policy_name?: string;
  leave_type?: string;
  is_paid?: boolean;
}

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
  status: "pending" | "approved" | "rejected" | "cancelled";
  is_paid: boolean;
  source_channel: string;
  reviewed_at?: string;
  review_comment?: string;
  created_at: string;
}

export default function LeaveManagement() {
  const { user } = useAuthStore();
  const isCeoOrHr =
    user?.role === "ceo" ||
    user?.role === "admin" ||
    user?.role === "super_admin" ||
    user?.role === "hr" ||
    user?.role === "hr_manager" ||
    user?.role === "content_manager" ||
    !!user?.permissions?.can_manage_policies;

  const [policies, setPolicies] = useState<LeavePolicy[]>([]);
  const [balances, setBalances] = useState<LeaveBalance[]>([]);
  const [requests, setRequests] = useState<LeaveRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("all");

  // Application Modal state
  const [showApplyModal, setShowApplyModal] = useState(false);
  const [applying, setApplying] = useState(false);
  const [applyError, setApplyError] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    policy_id: "",
    start_date: "",
    end_date: "",
    reason: "",
  });

  // Actioning states (Approve / Reject)
  const [actioningId, setActioningId] = useState<string | null>(null);
  const [actionComment, setActionComment] = useState("");
  const [activeActionModal, setActiveActionModal] = useState<{
    id: string;
    request_number: string;
    action: "approve" | "reject";
  } | null>(null);

  const isHrOrAdmin = user?.role === "admin" || user?.role === "hr" || user?.role === "manager";

  const fetchData = async () => {
    try {
      setLoading(true);
      const [policiesRes, balancesRes, requestsRes] = await Promise.all([
        api.get("/leaves/policies"),
        api.get("/leaves/balances"),
        api.get("/leaves/requests"),
      ]);
      setPolicies(policiesRes.data);
      setBalances(balancesRes.data);
      setRequests(requestsRes.data);

      if (policiesRes.data.length > 0 && !formData.policy_id) {
        setFormData((prev) => ({ ...prev, policy_id: policiesRes.data[0].id }));
      }
    } catch (err: any) {
      console.error("Failed to load leave data", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Helper: Calculate working days client-side for dynamic feedback
  const previewWorkingDays = useMemo(() => {
    if (!formData.start_date || !formData.end_date) return 0;
    const start = new Date(formData.start_date);
    const end = new Date(formData.end_date);
    if (isNaN(start.getTime()) || isNaN(end.getTime()) || end < start) return 0;

    let count = 0;
    const cur = new Date(start);
    while (cur <= end) {
      const day = cur.getDay();
      if (day !== 0 && day !== 6) count++;
      cur.setDate(cur.getDate() + 1);
    }
    return count;
  }, [formData.start_date, formData.end_date]);

  const selectedPolicyBalance = useMemo(() => {
    return balances.find((b) => b.leave_policy_id === formData.policy_id);
  }, [balances, formData.policy_id]);

  const handleApplySubmit = async (e: FormEvent) => {
    e.preventDefault();
    setApplyError(null);

    if (previewWorkingDays <= 0) {
      setApplyError("Please select a date range with at least one working day.");
      return;
    }

    try {
      setApplying(true);
      await api.post("/leaves/requests", {
        leave_policy_id: formData.policy_id,
        start_date: formData.start_date,
        end_date: formData.end_date,
        reason: formData.reason.trim() || undefined,
      });

      setShowApplyModal(false);
      setFormData({
        policy_id: policies[0]?.id || "",
        start_date: "",
        end_date: "",
        reason: "",
      });
      await fetchData();
    } catch (err: any) {
      setApplyError(err.response?.data?.detail || "Failed to submit leave request.");
    } finally {
      setApplying(false);
    }
  };

  const handleProcessAction = async () => {
    if (!activeActionModal) return;
    try {
      setActioningId(activeActionModal.id);
      await api.patch(`/leaves/requests/${activeActionModal.id}/action`, {
        action: activeActionModal.action,
        comment: actionComment.trim() || undefined,
      });
      setActiveActionModal(null);
      setActionComment("");
      await fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Action processing failed.");
    } finally {
      setActioningId(null);
    }
  };

  const filteredRequests = useMemo(() => {
    if (statusFilter === "all") return requests;
    return requests.filter((r) => r.status.toLowerCase() === statusFilter);
  }, [requests, statusFilter]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans antialiased">
      <Navbar />

      {/* Main Content Viewport */}
      <main className="flex-1 p-6 max-w-7xl w-full mx-auto space-y-6">
        {/* Title Bar & Application Action */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              <Calendar className="w-5 h-5 text-indigo-400" />
              Leave & Time-Off Management
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Submit applications, track balances, and audit approval chains.
            </p>
          </div>

          <div className="flex items-center gap-2">
            {isCeoOrHr && (
              <Link
                to="/policies"
                className="px-3.5 py-1.5 bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer"
              >
                <BookOpen className="w-3.5 h-3.5 text-indigo-400" />
                Upload / View Policies (PDF)
              </Link>
            )}
            <button
              onClick={() => {
                setApplyError(null);
                setShowApplyModal(true);
              }}
              className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer self-start sm:self-auto"
            >
              <Plus className="w-3.5 h-3.5" />
              Apply for Leave
            </button>
          </div>
        </div>

        {/* Asymmetric 8:4 Structural Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Main 8-Column Applications Roster */}
          <div className="lg:col-span-8 space-y-4">
            {/* Filter Tabs */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-2.5 flex items-center justify-between">
              <div className="flex items-center gap-1">
                {[
                  { id: "all", label: "All Requests" },
                  { id: "pending", label: "Pending Review" },
                  { id: "approved", label: "Approved" },
                  { id: "rejected", label: "Rejected" },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setStatusFilter(tab.id)}
                    className={`px-3 py-1 rounded-lg text-xs font-medium transition cursor-pointer ${
                      statusFilter === tab.id
                        ? "bg-slate-800 text-white border border-slate-700"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              <span className="text-[11px] font-mono text-slate-500 mr-2">
                {filteredRequests.length} record{filteredRequests.length !== 1 ? "s" : ""}
              </span>
            </div>

            {/* Applications Table Card */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
              {loading ? (
                <div className="p-12 flex flex-col items-center justify-center gap-3">
                  <Loader2 className="w-6 h-6 animate-spin text-indigo-500 motion-reduce:animate-none" />
                  <span className="text-xs text-slate-400">Synchronizing leave ledger…</span>
                </div>
              ) : filteredRequests.length === 0 ? (
                <div className="p-12 text-center space-y-2">
                  <CalendarDays className="w-8 h-8 text-slate-600 mx-auto" />
                  <div className="text-sm font-medium text-slate-300">No leave requests recorded</div>
                  <p className="text-xs text-slate-500 max-w-sm mx-auto">
                    There are no leave requests matching this filter. Submit a new application or adjust status.
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="border-b border-slate-800 bg-slate-950/40 text-xs text-slate-400 font-medium">
                        <th className="py-2.5 px-4">Request #</th>
                        <th className="py-2.5 px-4">Applicant</th>
                        <th className="py-2.5 px-4">Category</th>
                        <th className="py-2.5 px-4">Duration</th>
                        <th className="py-2.5 px-4">Status</th>
                        {isHrOrAdmin && <th className="py-2.5 px-4 text-right">Actions</th>}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 text-xs">
                      {filteredRequests.map((req) => (
                        <tr key={req.id} className="hover:bg-slate-800/30 transition-colors motion-reduce:transition-none">
                          <td className="py-3 px-4 font-mono font-medium text-indigo-400 text-xs">
                            {req.request_number}
                          </td>
                          <td className="py-3 px-4">
                            <div className="font-semibold text-white">
                              {req.employee_name || "Self Application"}
                            </div>
                            {req.employee_code && (
                              <div className="text-xs font-mono text-slate-500">{req.employee_code}</div>
                            )}
                          </td>
                          <td className="py-3 px-4">
                            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-slate-800 text-slate-200 text-xs">
                              {req.policy_name || "Leave"}
                            </span>
                            <div className="text-[10px] text-slate-500 mt-0.5">
                              {req.is_paid ? "Paid" : "Unpaid"}
                            </div>
                          </td>
                          <td className="py-3 px-4">
                            <div className="text-slate-200 font-medium">
                              {req.total_days} day{Number(req.total_days) !== 1 ? "s" : ""}
                            </div>
                            <div className="text-xs font-mono text-slate-500">
                              {req.start_date} → {req.end_date}
                            </div>
                            {req.reason && (
                              <p className="text-xs text-slate-400 truncate max-w-[180px] mt-0.5" title={req.reason}>
                                “{req.reason}”
                              </p>
                            )}
                          </td>
                          <td className="py-3 px-4">
                            {req.status === "approved" && (
                              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-medium">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                                Approved
                              </span>
                            )}
                            {req.status === "rejected" && (
                              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20 text-xs font-medium">
                                <span className="w-1.5 h-1.5 rounded-full bg-rose-400"></span>
                                Rejected
                              </span>
                            )}
                            {req.status === "pending" && (
                              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 text-xs font-medium">
                                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse motion-reduce:animate-none"></span>
                                Pending
                              </span>
                            )}
                          </td>
                          {isHrOrAdmin && (
                            <td className="py-3 px-4 text-right">
                              {req.status === "pending" ? (
                                <div className="flex items-center justify-end gap-1.5">
                                  <button
                                    onClick={() =>
                                      setActiveActionModal({
                                        id: req.id,
                                        request_number: req.request_number,
                                        action: "approve",
                                      })
                                    }
                                    title="Approve request"
                                    className="p-1 rounded bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 transition cursor-pointer"
                                  >
                                    <Check className="w-3.5 h-3.5" />
                                  </button>
                                  <button
                                    onClick={() =>
                                      setActiveActionModal({
                                        id: req.id,
                                        request_number: req.request_number,
                                        action: "reject",
                                      })
                                    }
                                    title="Reject request"
                                    className="p-1 rounded bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 transition cursor-pointer"
                                  >
                                    <X className="w-3.5 h-3.5" />
                                  </button>
                                </div>
                              ) : (
                                <span className="text-[10px] font-mono text-slate-500">Processed</span>
                              )}
                            </td>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          {/* 4-Column Contextual Intelligence Rail */}
          <div className="lg:col-span-4 space-y-4">
            {/* Balance Ledger Card */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3.5">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-indigo-400" />
                  Annual Balance Ledger
                </span>
                <span className="text-xs font-mono text-indigo-400 bg-indigo-500/10 px-1.5 py-0.5 rounded border border-indigo-500/20">
                  {new Date().getFullYear()} CY
                </span>
              </div>

              {balances.length === 0 ? (
                <p className="text-xs text-slate-500 italic py-2">No active policy balances configured.</p>
              ) : (
                <div className="space-y-3">
                  {balances.map((bal) => (
                    <div
                      key={bal.id}
                      className="p-2.5 rounded-lg bg-slate-950 border border-slate-800/80 space-y-1.5"
                    >
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-semibold text-white">{bal.policy_name || "Leave"}</span>
                        <span className="font-mono text-indigo-400 font-bold">
                          {bal.available}d left
                        </span>
                      </div>
                      <div className="grid grid-cols-3 gap-2 text-xs text-slate-400 pt-1 border-t border-slate-900">
                        <div>
                          Alloc: <span className="text-slate-200">{bal.total_allocated}d</span>
                        </div>
                        <div>
                          Used: <span className="text-slate-200">{bal.used}d</span>
                        </div>
                        <div>
                          Pending: <span className="text-amber-400">{bal.pending}d</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Policy Rules & Guardrails Card */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
              <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                <Info className="w-4 h-4 text-indigo-400" />
                Policy Guardrails
              </span>

              <div className="text-xs text-slate-400 space-y-2">
                <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800/80 flex items-start gap-2">
                  <Clock className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
                  <div>
                    <div className="font-medium text-slate-200">Weekend Exclusion</div>
                    <p className="text-[11px] text-slate-400">
                      Saturdays and Sundays are automatically deducted from duration counts.
                    </p>
                  </div>
                </div>

                <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800/80 flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
                  <div>
                    <div className="font-medium text-slate-200">Conflict Prevention</div>
                    <p className="text-[11px] text-slate-400">
                      Overlapping requests for the same date window are rejected with HTTP 409.
                    </p>
                  </div>
                </div>

                {isCeoOrHr && (
                  <Link
                    to="/policies"
                    className="mt-3 w-full py-2 px-3 rounded-lg bg-indigo-600/10 hover:bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 font-medium text-xs flex items-center justify-center gap-1.5 transition"
                  >
                    <Upload className="w-3.5 h-3.5" />
                    Upload / Deploy Policy (PDF / MD)
                  </Link>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Apply Leave Modal */}
      {showApplyModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/90 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Calendar className="w-4 h-4 text-indigo-400" />
                Apply for Leave
              </h2>
              <button
                onClick={() => setShowApplyModal(false)}
                className="text-slate-400 hover:text-white transition cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {applyError && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{applyError}</span>
              </div>
            )}

            <form onSubmit={handleApplySubmit} className="space-y-3.5">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Leave Category</label>
                <select
                  value={formData.policy_id}
                  onChange={(e) => setFormData({ ...formData, policy_id: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white focus:border-indigo-500 outline-none"
                  required
                >
                  {policies.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.is_paid ? "Paid" : "Unpaid"})
                    </option>
                  ))}
                </select>
                {selectedPolicyBalance && (
                  <div className="text-[11px] font-mono text-slate-400 mt-1">
                    Available balance: <span className="text-indigo-400">{selectedPolicyBalance.available} days</span>
                  </div>
                )}
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Start Date</label>
                  <input
                    type="date"
                    value={formData.start_date}
                    onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white focus:border-indigo-500 outline-none"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">End Date</label>
                  <input
                    type="date"
                    value={formData.end_date}
                    onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white focus:border-indigo-500 outline-none"
                    required
                  />
                </div>
              </div>

              {previewWorkingDays > 0 && (
                <div className="p-2.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-xs text-indigo-300 flex items-center justify-between">
                  <span>Calculated Business Days:</span>
                  <span className="font-mono font-bold text-white">{previewWorkingDays} day{previewWorkingDays !== 1 ? "s" : ""}</span>
                </div>
              )}

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Reason / Note</label>
                <textarea
                  value={formData.reason}
                  onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
                  placeholder="Provide context for manager review..."
                  rows={3}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-white focus:border-indigo-500 outline-none resize-none"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowApplyModal(false)}
                  className="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium transition cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={applying}
                  className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition disabled:opacity-50 cursor-pointer"
                >
                  {applying && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Submit Application
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Action Approval/Rejection Modal */}
      {activeActionModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/90 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-sm w-full p-5 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <h3 className="text-sm font-bold text-white capitalize">
                {activeActionModal.action} Leave Request
              </h3>
              <button
                onClick={() => setActiveActionModal(null)}
                className="text-slate-400 hover:text-white transition-colors motion-reduce:transition-none cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-slate-300">
              Confirm {activeActionModal.action} action on request{" "}
              <span className="font-mono text-indigo-400">{activeActionModal.request_number}</span>?
            </p>

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">
                Optional Reviewer Note
              </label>
              <textarea
                value={actionComment}
                onChange={(e) => setActionComment(e.target.value)}
                placeholder="Reason or conditions…"
                rows={2}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-white focus:border-indigo-500 outline-none resize-none"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setActiveActionModal(null)}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleProcessAction}
                disabled={!!actioningId}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold text-white flex items-center gap-1.5 transition cursor-pointer ${
                  activeActionModal.action === "approve"
                    ? "bg-emerald-600 hover:bg-emerald-500"
                    : "bg-rose-600 hover:bg-rose-500"
                }`}
              >
                {actioningId && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                Confirm {activeActionModal.action}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
