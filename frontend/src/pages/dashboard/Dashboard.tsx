import { useState, useEffect, useMemo, FormEvent } from "react";
import {
  Calendar,
  CheckCircle2,
  AlertCircle,
  Plus,
  CreditCard,
  ShieldCheck,
  Loader2,
  X,
  FileText,
  CalendarDays,
  ExternalLink,
  Bot,
  Sparkles,
  Send,
} from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "../../lib/api";
import { useAuthStore } from "../../store/authStore";
import Navbar from "../../components/layout/Navbar";

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

interface LeavePolicy {
  id: string;
  name: string;
  leave_type: string;
  days_allowed: number;
  is_paid: boolean;
}

interface LeaveRequest {
  id: string;
  request_number: string;
  employee_id: string;
  policy_name?: string;
  leave_type?: string;
  start_date: string;
  end_date: string;
  total_days: number | string;
  reason?: string;
  status: "pending" | "approved" | "rejected";
  is_paid: boolean;
  created_at: string;
}

interface EmployeeProfile {
  id: string;
  employee_code: string;
  first_name: string;
  last_name: string;
  email: string;
  designation?: string;
  department_name?: string;
  salary_basic?: number | string;
  paypal_email?: string | null;
  date_of_joining?: string;
}

export default function Dashboard() {
  const { user } = useAuthStore();

  const [balances, setBalances] = useState<LeaveBalance[]>([]);
  const [requests, setRequests] = useState<LeaveRequest[]>([]);
  const [policies, setPolicies] = useState<LeavePolicy[]>([]);
  const [employeeProfile, setEmployeeProfile] = useState<EmployeeProfile | null>(null);
  const [loading, setLoading] = useState(true);

  // Apply Leave Modal state
  const [showApplyModal, setShowApplyModal] = useState(false);
  const [applying, setApplying] = useState(false);
  const [applyError, setApplyError] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    policy_id: "",
    start_date: "",
    end_date: "",
    reason: "",
  });

  // Embedded Employee AI Assistant State
  const [aiInput, setAiInput] = useState("");
  const [aiLoading, setAiLoading] = useState(false);
  const [aiResponse, setAiResponse] = useState<string | null>(null);
  const [aiExtracted, setAiExtracted] = useState<any | null>(null);

  const handleAiAsk = async (promptText?: string) => {
    const q = promptText || aiInput.trim();
    if (!q || aiLoading) return;
    try {
      setAiLoading(true);
      setAiResponse(null);
      setAiExtracted(null);
      const res = await api.post("/agents/chat", { message: q });
      setAiResponse(res.data.reply);
      if (res.data.extracted_leave?.is_leave_request) {
        setAiExtracted(res.data.extracted_leave);
      }
      setAiInput("");
    } catch (err: any) {
      setAiResponse("AI assistant is currently updating context. Please try again shortly.");
    } finally {
      setAiLoading(false);
    }
  };

  const handleApplyFromAi = () => {
    if (!aiExtracted) return;
    let targetPolicyId = policies[0]?.id || "";
    if (aiExtracted.leave_type) {
      const matched = policies.find(
        (p) => p.leave_type.toLowerCase() === aiExtracted.leave_type.toLowerCase()
      );
      if (matched) targetPolicyId = matched.id;
    }
    setFormData({
      policy_id: targetPolicyId,
      start_date: aiExtracted.start_date || "",
      end_date: aiExtracted.end_date || "",
      reason: aiExtracted.reason || "",
    });
    setApplyError(null);
    setShowApplyModal(true);
  };

  const fetchData = async () => {
    try {
      setLoading(true);
      const [balancesRes, requestsRes, policiesRes, empRes] = await Promise.all([
        api.get("/leaves/balances").catch(() => ({ data: [] })),
        api.get("/leaves/requests").catch(() => ({ data: [] })),
        api.get("/leaves/policies").catch(() => ({ data: [] })),
        api.get("/employees/?page=1&page_size=100").catch(() => ({ data: { items: [] } })),
      ]);

      setBalances(balancesRes.data);
      setRequests(requestsRes.data);
      setPolicies(policiesRes.data);

      if (policiesRes.data.length > 0 && !formData.policy_id) {
        setFormData((prev) => ({ ...prev, policy_id: policiesRes.data[0].id }));
      }

      // Match current employee profile from email
      const items = empRes.data?.items || [];
      const found = items.find((e: any) => e.email.toLowerCase() === user?.email.toLowerCase());
      if (found) {
        setEmployeeProfile(found);
      } else if (items.length > 0) {
        setEmployeeProfile(items[0]);
      }
    } catch (err) {
      console.error("Failed to load dashboard data", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [user]);

  // Dynamic preview of business days
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

  const handleApplySubmit = async (e: FormEvent) => {
    e.preventDefault();
    setApplyError(null);

    if (previewWorkingDays <= 0) {
      setApplyError("Select a date range with at least one working day (Mon-Fri).");
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
      setApplyError(err.response?.data?.detail || "Failed to submit application.");
    } finally {
      setApplying(false);
    }
  };

  const totalAvailableDays = balances.reduce(
    (acc, b) => acc + Number(b.available || 0),
    0
  );

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans antialiased">
      <Navbar />

      <main className="flex-1 p-6 max-w-7xl w-full mx-auto space-y-6">
        {/* Identity & Hero Banner */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 relative overflow-hidden flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center font-bold text-white text-xl">
              {employeeProfile?.first_name ? employeeProfile.first_name[0] : user?.email[0].toUpperCase()}
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h1 className="text-xl font-bold text-white tracking-tight">
                  {employeeProfile ? `${employeeProfile.first_name} ${employeeProfile.last_name}` : user?.email}
                </h1>
                <span className="px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 text-xs capitalize font-medium">
                  {user?.role?.replace("_", " ")}
                </span>
              </div>
              <div className="flex items-center gap-4 text-xs text-slate-400 mt-1">
                <span className="flex items-center gap-1 font-mono text-slate-300">
                  {employeeProfile?.employee_code || "EMP-PORTAL"}
                </span>
                <span>•</span>
                <span>{employeeProfile?.designation || "Staff Member"}</span>
                <span>•</span>
                <span className="text-slate-300">{employeeProfile?.department_name || "Engineering"}</span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3 w-full md:w-auto">
            <button
              onClick={() => {
                setApplyError(null);
                setShowApplyModal(true);
              }}
              className="flex-1 md:flex-initial px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition cursor-pointer shadow-sm"
            >
              <Plus className="w-4 h-4" />
              Apply for Leave
            </button>
            <Link
              to="/leaves"
              className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg text-xs font-medium flex items-center gap-1.5 transition"
            >
              <Calendar className="w-3.5 h-3.5" />
              All Requests
            </Link>
          </div>
        </div>

        {/* PASS 1: Asymmetric 8:4 Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Main 8-Column Left Pane */}
          <div className="lg:col-span-8 space-y-6">
            {/* PASS 1: Asymmetric Balance Metric Grid (7:5 Split) */}
            <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
              <div className="md:col-span-7 p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-400 font-medium">
                    Available Time-Off Pool
                  </span>
                  <span className="text-xs text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 font-medium">
                    Active Entitlement
                  </span>
                </div>
                <div className="flex items-baseline gap-3">
                  <div className="text-3xl font-extrabold font-mono text-white tracking-tight">
                    {totalAvailableDays} <span className="text-sm font-sans font-normal text-slate-400">days</span>
                  </div>
                  <span className="text-xs text-slate-400">across all active company policies</span>
                </div>
                <div className="w-full bg-slate-950 rounded-full h-1.5 overflow-hidden flex gap-0.5 p-0.5 border border-slate-800/80">
                  <div
                    className="bg-indigo-500 h-full rounded-full"
                    style={{ width: `${Math.min(100, Math.max(15, totalAvailableDays * 3))}%` }}
                  />
                </div>
              </div>

              <div className="md:col-span-5 grid grid-cols-2 gap-3">
                <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex flex-col justify-between">
                  <span className="text-xs text-slate-400 font-medium">In review</span>
                  <div className="text-2xl font-bold font-mono text-amber-400 my-1">
                    {requests.filter((r) => r.status === "pending").length}
                  </div>
                  <span className="text-xs text-slate-500">Awaiting Manager</span>
                </div>

                <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex flex-col justify-between">
                  <span className="text-xs text-slate-400 font-medium">Approved</span>
                  <div className="text-2xl font-bold font-mono text-emerald-400 my-1">
                    {requests.filter((r) => r.status === "approved").length}
                  </div>
                  <span className="text-xs text-slate-500">Current Year</span>
                </div>
              </div>
            </div>

            {/* Recent Requests Section */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden space-y-0">
              <div className="p-4 border-b border-slate-800 flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-bold text-white flex items-center gap-2">
                    <CalendarDays className="w-4 h-4 text-indigo-400" />
                    Recent Leave Applications
                  </h2>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Track real-time status of your submitted time-off requests.
                  </p>
                </div>
                <Link
                  to="/leaves"
                  className="text-xs text-indigo-400 hover:text-indigo-300 font-medium flex items-center gap-1"
                >
                  View full ledger <ExternalLink className="w-3 h-3" />
                </Link>
              </div>

              {loading ? (
                <div className="p-10 flex flex-col items-center justify-center gap-2">
                  <Loader2 className="w-5 h-5 animate-spin text-indigo-500" />
                  <span className="text-xs text-slate-400">Loading leave requests…</span>
                </div>
              ) : requests.length === 0 ? (
                <div className="p-8 text-center space-y-2">
                  <FileText className="w-8 h-8 text-slate-600 mx-auto" />
                  <div className="text-xs font-medium text-slate-300">No leave applications on file</div>
                  <p className="text-xs text-slate-500">
                    Use the “Apply for Leave” button above to submit your first request.
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="border-b border-slate-800 bg-slate-950/40 text-xs text-slate-400 font-medium">
                        <th className="py-2.5 px-4">Request #</th>
                        <th className="py-2.5 px-4">Category</th>
                        <th className="py-2.5 px-4">Duration</th>
                        <th className="py-2.5 px-4">Reason</th>
                        <th className="py-2.5 px-4 text-right">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {requests.slice(0, 5).map((req) => (
                        <tr key={req.id} className="hover:bg-slate-800/20 transition">
                          <td className="py-3 px-4 font-mono font-medium text-indigo-400">
                            {req.request_number}
                          </td>
                          <td className="py-3 px-4">
                            <span className="font-medium text-slate-200">
                              {req.policy_name || "Leave"}
                            </span>
                            <span className="text-[10px] text-slate-500 block">
                              {req.is_paid ? "Paid" : "Unpaid"}
                            </span>
                          </td>
                          <td className="py-3 px-4">
                            <div className="font-semibold text-white">
                              {req.total_days} day{Number(req.total_days) !== 1 ? "s" : ""}
                            </div>
                            <span className="text-[10px] font-mono text-slate-500">
                              {req.start_date} → {req.end_date}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-slate-400 max-w-xs truncate">
                            {req.reason || "—"}
                          </td>
                          <td className="py-3 px-4 text-right">
                            {req.status === "approved" && (
                              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[11px] font-medium">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                                Approved
                              </span>
                            )}
                            {req.status === "rejected" && (
                              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20 text-[11px] font-medium">
                                <span className="w-1.5 h-1.5 rounded-full bg-rose-400"></span>
                                Rejected
                              </span>
                            )}
                            {req.status === "pending" && (
                              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[11px] font-medium">
                                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse"></span>
                                In Review
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          {/* 4-Column Contextual Intelligence Rail */}
          <div className="lg:col-span-4 space-y-5">
            {/* Live Leave Balance Breakdown */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3.5">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-indigo-400" />
                  Your Leave Balances
                </span>
                <span className="text-xs font-mono text-indigo-400 bg-indigo-500/10 px-1.5 py-0.5 rounded border border-indigo-500/20">
                  {new Date().getFullYear()} CY
                </span>
              </div>

              {balances.length === 0 ? (
                <p className="text-xs text-slate-500 italic py-2">No policy balances initialized.</p>
              ) : (
                <div className="space-y-3">
                  {balances.map((b) => {
                    const total = Number(b.total_allocated) || 1;
                    const used = Number(b.used) || 0;
                    const pct = Math.min(100, Math.round((used / total) * 100));
                    return (
                      <div
                        key={b.id}
                        className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-2 hover:border-slate-700/80 transition-colors motion-reduce:transition-none"
                      >
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-semibold text-white">{b.policy_name || "Leave"}</span>
                          <span className="font-mono text-indigo-400 font-bold">
                            {b.available}d remaining
                          </span>
                        </div>

                        {/* Progress Meter */}
                        <div className="w-full bg-slate-900 rounded-full h-1 overflow-hidden">
                          <div
                            className="bg-indigo-500 h-full rounded-full"
                            style={{ width: `${pct}%` }}
                          />
                        </div>

                        <div className="grid grid-cols-3 gap-1 text-xs text-slate-400 pt-1 border-t border-slate-900">
                          <div>
                            Alloc: <span className="text-slate-200">{b.total_allocated}d</span>
                          </div>
                          <div>
                            Used: <span className="text-slate-200">{b.used}d</span>
                          </div>
                          <div>
                            Pending: <span className="text-amber-400">{b.pending}d</span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Compensation & PayPal Payout Footprint */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
              <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                <CreditCard className="w-4 h-4 text-indigo-400" />
                Disbursement & Payout Rail
              </span>

              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Direct PayPal Email</span>
                  <span className="font-mono text-slate-200 font-medium">
                    {employeeProfile?.paypal_email || "Not linked"}
                  </span>
                </div>
                <div className="flex items-center justify-between pt-1 border-t border-slate-900">
                  <span className="text-slate-400">Sandbox Settlement</span>
                  <span className="inline-flex items-center gap-1 text-emerald-400 text-xs">
                    <CheckCircle2 className="w-3 h-3" /> Active
                  </span>
                </div>
                <div className="flex items-center justify-between pt-1 border-t border-slate-900">
                  <span className="text-slate-400">Annual Base</span>
                  <span className="font-mono text-white font-bold">
                    ${Number(employeeProfile?.salary_basic || 0).toLocaleString()} USD
                  </span>
                </div>
              </div>
            </div>

            {/* Embedded Employee AI Leave Assistant */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <span className="text-xs font-semibold text-white flex items-center gap-1.5">
                  <Bot className="w-4 h-4 text-indigo-400" />
                  WorkforceAI Leave Copilot
                </span>
                <span className="text-xs text-indigo-400 bg-indigo-500/10 px-1.5 py-0.5 rounded border border-indigo-500/20">
                  Gemini 2.5
                </span>
              </div>

              <p className="text-[11px] text-slate-400 leading-relaxed">
                Ask about company leave rules, check entitlement, or draft leave requests in natural language.
              </p>

              {/* Quick Prompt Pills */}
              <div className="flex flex-wrap gap-1.5 pt-1">
                <button
                  type="button"
                  onClick={() => handleAiAsk("What is my current leave balance?")}
                  className="px-2 py-1 rounded bg-slate-950 hover:bg-slate-800 border border-slate-800 text-[10px] text-slate-300 transition-colors motion-reduce:transition-none"
                >
                  Check my balances
                </button>
                <button
                  type="button"
                  onClick={() => handleAiAsk("What is the notice requirement for casual leave?")}
                  className="px-2 py-1 rounded bg-slate-950 hover:bg-slate-800 border border-slate-800 text-[10px] text-slate-300 transition-colors motion-reduce:transition-none"
                >
                  Casual leave rules
                </button>
                <button
                  type="button"
                  onClick={() => handleAiAsk("Can I take 2 days sick leave?")}
                  className="px-2 py-1 rounded bg-slate-950 hover:bg-slate-800 border border-slate-800 text-[10px] text-slate-300 transition-colors motion-reduce:transition-none"
                >
                  Sick leave policy
                </button>
              </div>

              {/* Chat Input */}
              <div className="flex gap-1.5 pt-1">
                <input
                  type="text"
                  placeholder="e.g. I need next Friday off…"
                  value={aiInput}
                  onChange={(e) => setAiInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleAiAsk()}
                  className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 outline-none focus:border-indigo-500"
                />
                <button
                  type="button"
                  onClick={() => handleAiAsk()}
                  disabled={aiLoading || !aiInput.trim()}
                  className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold flex items-center justify-center transition-colors motion-reduce:transition-none cursor-pointer"
                >
                  {aiLoading ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Send className="w-3.5 h-3.5" />
                  )}
                </button>
              </div>

              {/* AI Response Display */}
              {aiResponse && (
                <div className="p-3 rounded-lg bg-slate-950 border border-indigo-500/20 text-xs text-slate-300 space-y-2 mt-2">
                  <div className="text-xs text-indigo-400 flex items-center gap-1 font-medium">
                    <Sparkles className="w-3 h-3" />
                    Agent Response:
                  </div>
                  <p className="text-[11px] leading-relaxed whitespace-pre-wrap">{aiResponse}</p>
                  {aiExtracted && (
                    <button
                      type="button"
                      onClick={handleApplyFromAi}
                      className="w-full mt-2 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition-colors motion-reduce:transition-none cursor-pointer flex items-center justify-center gap-1.5 whitespace-nowrap"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      Apply for Extracted Leave
                    </button>
                  )}
                </div>
              )}
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
                  <span className="font-mono font-bold text-white">
                    {previewWorkingDays} day{previewWorkingDays !== 1 ? "s" : ""}
                  </span>
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
    </div>
  );
}
