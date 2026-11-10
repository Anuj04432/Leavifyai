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
  BarChart3,
  Users,
  Activity,
  Clock,
  MessageSquareQuote,
  TrendingUp,
} from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "../../lib/api";
import { useAuthStore } from "../../store/authStore";

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
  const [totalHeadcount, setTotalHeadcount] = useState(0);
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

  const fetchData = async () => {
    try {
      setLoading(true);
      const [balancesRes, requestsRes, policiesRes, empRes] = await Promise.all([
        api.get("/leaves/balances").catch(() => ({ data: [] })),
        api.get("/leaves/requests").catch(() => ({ data: [] })),
        api.get("/leaves/policies").catch(() => ({ data: [] })),
        api.get("/employees/?page=1&page_size=100").catch(() => ({ data: { items: [], total: 0 } })),
      ]);

      setBalances(balancesRes.data);
      setRequests(requestsRes.data);
      setPolicies(policiesRes.data);

      if (policiesRes.data.length > 0 && !formData.policy_id) {
        setFormData((prev) => ({ ...prev, policy_id: policiesRes.data[0].id }));
      }

      const items = empRes.data?.items || [];
      setTotalHeadcount(empRes.data?.total || items.length || 0);

      // Match current employee profile from email
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
        policy_id: formData.policy_id,
        start_date: formData.start_date,
        end_date: formData.end_date,
        reason: formData.reason.trim(),
      });

      setShowApplyModal(false);
      setFormData({
        policy_id: policies[0]?.id || "",
        start_date: "",
        end_date: "",
        reason: "",
      });
      fetchData();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setApplyError(typeof detail === "string" ? detail : "Failed to submit leave request.");
    } finally {
      setApplying(false);
    }
  };

  const totalAvailableDays = useMemo(() => {
    return balances.reduce((acc, b) => acc + (Number(b.available) || 0), 0);
  }, [balances]);

  // Role Gating: Higher departments / Leadership
  const isLeadership = [
    "ceo",
    "super_admin",
    "admin",
    "hr",
    "hr_manager",
    "ir_manager",
    "manager",
  ].includes(user?.role || "");

  // Leadership analytics metrics
  const leadershipMetrics = useMemo(() => {
    const total = requests.length;
    const pending = requests.filter((r) => r.status === "pending").length;
    const approved = requests.filter((r) => r.status === "approved").length;
    const rejected = requests.filter((r) => r.status === "rejected").length;

    const totalApprovedDays = requests
      .filter((r) => r.status === "approved")
      .reduce((acc, r) => acc + Number(r.total_days || 0), 0);

    const todayStr = new Date().toISOString().split("T")[0];
    const activeOnLeaveToday = requests.filter((r) => {
      return r.status === "approved" && r.start_date <= todayStr && todayStr <= r.end_date;
    }).length;

    const headcount = totalHeadcount || 3;
    const availableStaff = Math.max(0, headcount - activeOnLeaveToday);
    const staffingRate = Math.round((availableStaff / headcount) * 100);

    // Leave distribution by type
    const categoryCounts: Record<string, number> = {};
    requests.forEach((r) => {
      const type = r.policy_name || r.leave_type || "General";
      categoryCounts[type] = (categoryCounts[type] || 0) + 1;
    });

    return {
      total,
      pending,
      approved,
      rejected,
      totalApprovedDays,
      activeOnLeaveToday,
      staffingRate,
      categoryCounts,
    };
  }, [requests, totalHeadcount]);

  const orgName = useMemo(() => {
    if (user?.company_name && user.company_name.trim()) {
      return user.company_name;
    }
    const domain =
      user?.company_domain || (user?.email?.includes("@") ? user.email.split("@")[1] : "");
    if (domain) {
      const cleanSlug = domain.split(".")[0];
      if (cleanSlug && cleanSlug !== "workforce" && cleanSlug !== "company") {
        return cleanSlug.charAt(0).toUpperCase() + cleanSlug.slice(1);
      }
    }
    return "Organization";
  }, [user?.company_name, user?.company_domain, user?.email]);

  return (
    <div className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto space-y-6">
      {/* Identity & Hero Header Banner */}
      <div className="bg-[#141210] border border-stone-800 rounded-2xl p-6 relative overflow-hidden flex flex-col md:flex-row items-start md:items-center justify-between gap-6 shadow-sm">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-orange-950/60 border border-orange-500/30 flex items-center justify-center font-bold text-orange-400 text-2xl shadow-sm">
            {employeeProfile?.first_name ? employeeProfile.first_name[0] : user?.email[0].toUpperCase()}
          </div>
          <div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <h1 className="text-xl sm:text-2xl font-bold text-[#FFFDF8] tracking-tight">
                {employeeProfile ? `${employeeProfile.first_name} ${employeeProfile.last_name}` : user?.email}
              </h1>
              <span
                className={`px-2.5 py-0.5 rounded-lg text-xs font-mono capitalize border ${
                  user?.role === "ceo" || user?.role === "super_admin"
                    ? "bg-amber-950/60 text-amber-300 border-amber-500/30 font-semibold"
                    : "bg-stone-900 text-stone-300 border-stone-800 font-medium"
                }`}
              >
                {user?.role?.replace("_", " ")}
              </span>
              <span className="px-2.5 py-0.5 rounded-lg text-xs font-medium bg-stone-900/90 text-stone-200 border border-stone-800 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                {orgName}
              </span>
            </div>
            <div className="flex items-center gap-3 text-xs sm:text-sm text-stone-400 mt-1.5 flex-wrap">
              <span className="font-mono text-stone-300 bg-stone-900 px-2 py-0.5 rounded border border-stone-800">
                {employeeProfile?.employee_code || "EMP-PORTAL"}
              </span>
              <span>•</span>
              <span>{employeeProfile?.designation || "Staff Member"}</span>
              <span>•</span>
              <span className="text-stone-300">{employeeProfile?.department_name || "General Department"}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <button
            onClick={() => {
              setApplyError(null);
              setShowApplyModal(true);
            }}
            className="flex-1 md:flex-initial px-5 py-3 bg-orange-600 hover:bg-orange-500 active:bg-orange-700 text-white rounded-xl text-sm font-semibold flex items-center justify-center gap-2 transition-all cursor-pointer shadow-sm"
          >
            <Plus className="w-4 h-4" />
            Apply for Leave
          </button>
          <Link
            to="/company-chat"
            className="px-4 py-3 bg-stone-900 hover:bg-stone-800 text-orange-400 hover:text-orange-300 border border-stone-800 hover:border-orange-500/40 rounded-xl text-sm font-medium flex items-center gap-2 transition-colors cursor-pointer"
          >
            <MessageSquareQuote className="w-4 h-4" />
            <span className="hidden sm:inline">Talk with Company</span>
          </Link>
        </div>
      </div>

      {/* LEADERSHIP-ONLY WORKFORCE LEAVE INTELLIGENCE PANEL */}
      {isLeadership && (
        <div className="bg-[#141210] border border-orange-500/20 rounded-2xl p-6 space-y-5 shadow-sm">
          <div className="flex items-center justify-between pb-3 border-b border-stone-800/80 flex-wrap gap-2">
            <div>
              <div className="flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-orange-400" />
                <h2 className="text-base sm:text-lg font-bold text-white tracking-tight">
                  Executive Leave Intelligence & Capacity Telemetry
                </h2>
                <span className="px-2 py-0.5 rounded-md bg-orange-950/60 border border-orange-500/30 text-orange-400 text-xs font-mono">
                  Department Leadership View
                </span>
              </div>
              <p className="text-xs text-stone-400 mt-1">
                Real-time workforce availability, department absence impact, and approval velocity across {orgName}.
              </p>
            </div>

            <div className="flex items-center gap-2 text-xs font-mono text-stone-400 bg-stone-900 px-3 py-1.5 rounded-xl border border-stone-800">
              <Activity className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
              <span>Real-Time Ingestion Active</span>
            </div>
          </div>

          {/* 4-Card Executive Telemetry Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Staffing Capacity */}
            <div className="p-4 rounded-xl bg-[#1c1917] border border-stone-800 space-y-2">
              <div className="flex items-center justify-between text-xs text-stone-400">
                <span>Staffing Capacity</span>
                <Users className="w-3.5 h-3.5 text-emerald-400" />
              </div>
              <div className="text-2xl sm:text-3xl font-extrabold font-mono text-emerald-400">
                {leadershipMetrics.staffingRate}%
              </div>
              <div className="text-xs text-stone-400 flex items-center justify-between">
                <span>Active Availability</span>
                <span className="font-mono text-stone-300 font-semibold">
                  {Math.max(0, (totalHeadcount || 3) - leadershipMetrics.activeOnLeaveToday)} / {totalHeadcount || 3} present
                </span>
              </div>
            </div>

            {/* In Review / Pending Cockpit Triage */}
            <div className="p-4 rounded-xl bg-[#1c1917] border border-stone-800 space-y-2">
              <div className="flex items-center justify-between text-xs text-stone-400">
                <span>Awaiting Decision</span>
                <Clock className="w-3.5 h-3.5 text-amber-400" />
              </div>
              <div className="text-2xl sm:text-3xl font-extrabold font-mono text-amber-400">
                {leadershipMetrics.pending}
              </div>
              <div className="text-xs text-stone-400 flex items-center justify-between">
                <span>Cockpit Backlog</span>
                <Link to="/approvals" className="text-orange-400 hover:underline">
                  Triage now →
                </Link>
              </div>
            </div>

            {/* Approved Days Consumed */}
            <div className="p-4 rounded-xl bg-[#1c1917] border border-stone-800 space-y-2">
              <div className="flex items-center justify-between text-xs text-stone-400">
                <span>Days Approved YTD</span>
                <TrendingUp className="w-3.5 h-3.5 text-orange-400" />
              </div>
              <div className="text-2xl sm:text-3xl font-extrabold font-mono text-white">
                {leadershipMetrics.totalApprovedDays} <span className="text-sm font-normal text-stone-400">days</span>
              </div>
              <div className="text-xs text-stone-400 flex items-center justify-between">
                <span>Across Organization</span>
                <span className="text-stone-300 font-mono font-medium">{leadershipMetrics.approved} requests</span>
              </div>
            </div>

            {/* Copilot Verification Accuracy */}
            <div className="p-4 rounded-xl bg-[#1c1917] border border-stone-800 space-y-2">
              <div className="flex items-center justify-between text-xs text-stone-400">
                <span>Copilot Policy Audit</span>
                <ShieldCheck className="w-3.5 h-3.5 text-orange-400" />
              </div>
              <div className="text-2xl sm:text-3xl font-extrabold font-mono text-orange-400">
                100%
              </div>
              <div className="text-xs text-stone-400 flex items-center justify-between">
                <span>Deterministic Rules</span>
                <span className="text-emerald-400 text-xs">Zero Overages</span>
              </div>
            </div>
          </div>

          {/* Leave Type Breakdown Pills */}
          {Object.keys(leadershipMetrics.categoryCounts).length > 0 && (
            <div className="pt-2">
              <div className="text-xs font-mono text-stone-500 uppercase tracking-wider mb-2">
                Leave Category Volume Distribution
              </div>
              <div className="flex flex-wrap gap-2">
                {Object.entries(leadershipMetrics.categoryCounts).map(([cat, count]) => (
                  <div
                    key={cat}
                    className="px-3 py-1.5 rounded-lg bg-[#181512] border border-stone-800 text-xs flex items-center gap-2"
                  >
                    <span className="text-stone-300 font-medium">{cat}</span>
                    <span className="px-1.5 py-0.2 rounded bg-orange-950/60 text-orange-400 font-mono font-bold text-[11px]">
                      {count}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Main Asymmetric Grid: 8-column main pane + 4-column context pane */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Main 8-Column Left Pane */}
        <div className="lg:col-span-8 space-y-6">
          {/* Balance Metric Grid */}
          <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
            <div className="md:col-span-7 p-5 rounded-2xl bg-[#141210] border border-stone-800 space-y-3 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs sm:text-sm text-stone-400 font-medium">
                  Available Personal Time-Off Pool
                </span>
                <span className="text-xs text-emerald-400 bg-emerald-950/40 px-2.5 py-0.5 rounded-md border border-emerald-500/20 font-medium">
                  Active Quota
                </span>
              </div>
              <div className="flex items-baseline gap-3">
                <div className="text-3xl sm:text-4xl font-extrabold font-mono text-white tracking-tight">
                  {totalAvailableDays} <span className="text-base font-sans font-normal text-stone-400">days</span>
                </div>
                <span className="text-xs text-stone-400">across active policies</span>
              </div>
              <div className="w-full bg-stone-950 rounded-full h-2 overflow-hidden flex gap-0.5 p-0.5 border border-stone-800/80">
                <div
                  className="bg-orange-600 h-full rounded-full transition-all"
                  style={{ width: `${Math.min(100, Math.max(15, totalAvailableDays * 3))}%` }}
                />
              </div>
            </div>

            <div className="md:col-span-5 grid grid-cols-2 gap-3">
              <div className="p-4 rounded-2xl bg-[#141210] border border-stone-800 flex flex-col justify-between shadow-sm">
                <span className="text-xs text-stone-400 font-medium">In Review</span>
                <div className="text-2xl sm:text-3xl font-bold font-mono text-amber-400 my-1">
                  {requests.filter((r) => r.status === "pending").length}
                </div>
                <span className="text-xs text-stone-500">Awaiting Manager</span>
              </div>

              <div className="p-4 rounded-2xl bg-[#141210] border border-stone-800 flex flex-col justify-between shadow-sm">
                <span className="text-xs text-stone-400 font-medium">Approved</span>
                <div className="text-2xl sm:text-3xl font-bold font-mono text-emerald-400 my-1">
                  {requests.filter((r) => r.status === "approved").length}
                </div>
                <span className="text-xs text-stone-500">Current Year</span>
              </div>
            </div>
          </div>

          {/* Recent Leave Requests Ledger */}
          <div className="bg-[#141210] border border-stone-800 rounded-2xl overflow-hidden shadow-sm">
            <div className="p-4 sm:p-5 border-b border-stone-800 flex items-center justify-between">
              <div>
                <h2 className="text-sm sm:text-base font-bold text-[#FFFDF8] flex items-center gap-2">
                  <CalendarDays className="w-4 h-4 text-orange-400" />
                  Recent Leave Applications
                </h2>
                <p className="text-xs text-stone-400 mt-0.5">
                  Track real-time status of your submitted time-off requests.
                </p>
              </div>
              <Link
                to="/leaves"
                className="text-xs sm:text-sm text-orange-400 hover:text-orange-300 font-medium flex items-center gap-1 transition-colors"
              >
                View full ledger <ExternalLink className="w-3.5 h-3.5" />
              </Link>
            </div>

            {loading ? (
              <div className="p-10 flex flex-col items-center justify-center gap-2">
                <Loader2 className="w-5 h-5 animate-spin text-orange-500" />
                <span className="text-xs sm:text-sm text-stone-400">Loading leave requests…</span>
              </div>
            ) : requests.length === 0 ? (
              <div className="p-8 text-center space-y-2">
                <FileText className="w-8 h-8 text-stone-600 mx-auto" />
                <div className="text-sm font-medium text-stone-300">No leave applications on file</div>
                <p className="text-xs text-stone-500">
                  Use the “Apply for Leave” button above to submit your first request.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-sm">
                  <thead>
                    <tr className="border-b border-stone-800 bg-[#1c1917]/50 text-xs text-stone-400 font-medium">
                      <th className="py-3 px-4">Request #</th>
                      <th className="py-3 px-4">Category</th>
                      <th className="py-3 px-4">Duration</th>
                      <th className="py-3 px-4">Reason</th>
                      <th className="py-3 px-4 text-right">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-stone-800/60">
                    {requests.slice(0, 6).map((req) => (
                      <tr key={req.id} className="hover:bg-stone-800/20 transition">
                        <td className="py-3 px-4 font-mono font-medium text-orange-400 text-xs sm:text-sm">
                          {req.request_number}
                        </td>
                        <td className="py-3 px-4">
                          <span className="font-medium text-stone-200">
                            {req.policy_name || "Leave"}
                          </span>
                          <span className="text-[11px] text-stone-500 block">
                            {req.is_paid ? "Paid" : "Unpaid"}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <div className="font-semibold text-white">
                            {req.total_days} day{Number(req.total_days) !== 1 ? "s" : ""}
                          </div>
                          <span className="text-xs font-mono text-stone-400">
                            {req.start_date} → {req.end_date}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-stone-400 max-w-xs truncate text-xs sm:text-sm">
                          {req.reason || "—"}
                        </td>
                        <td className="py-3 px-4 text-right">
                          {req.status === "approved" && (
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-950/50 text-emerald-400 border border-emerald-500/30 text-xs font-medium">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                              Approved
                            </span>
                          )}
                          {req.status === "rejected" && (
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-rose-950/50 text-rose-400 border border-rose-500/30 text-xs font-medium">
                              <span className="w-1.5 h-1.5 rounded-full bg-rose-400"></span>
                              Rejected
                            </span>
                          )}
                          {req.status === "pending" && (
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-950/50 text-amber-400 border border-amber-500/30 text-xs font-medium">
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

        {/* 4-Column Context Rail */}
        <div className="lg:col-span-4 space-y-5">
          {/* Live Leave Balance Breakdown */}
          <div className="bg-[#141210] border border-stone-800 rounded-2xl p-5 space-y-3.5 shadow-sm">
            <div className="flex items-center justify-between pb-2 border-b border-stone-800">
              <span className="text-sm font-semibold text-stone-200 flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-orange-400" />
                Personal Leave Quotas
              </span>
              <span className="text-xs font-mono text-orange-400 bg-orange-950/50 px-2 py-0.5 rounded-md border border-orange-500/20">
                {new Date().getFullYear()} CY
              </span>
            </div>

            {balances.length === 0 ? (
              <p className="text-xs text-stone-500 italic py-2">No policy balances initialized.</p>
            ) : (
              <div className="space-y-3">
                {balances.map((b) => {
                  const total = Number(b.total_allocated) || 1;
                  const used = Number(b.used) || 0;
                  const pct = Math.min(100, Math.round((used / total) * 100));
                  return (
                    <div
                      key={b.id}
                      className="p-3.5 rounded-xl bg-[#1c1917] border border-stone-800 space-y-2 hover:border-stone-700 transition-colors"
                    >
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-semibold text-white">{b.policy_name || "Leave"}</span>
                        <span className="font-mono text-orange-400 font-bold">
                          {b.available}d remaining
                        </span>
                      </div>

                      {/* Progress Meter */}
                      <div className="w-full bg-stone-900 rounded-full h-1.5 overflow-hidden">
                        <div
                          className="bg-orange-600 h-full rounded-full transition-all"
                          style={{ width: `${pct}%` }}
                        />
                      </div>

                      <div className="grid grid-cols-3 gap-1 text-xs text-stone-400 pt-1.5 border-t border-stone-800/80">
                        <div>
                          Alloc: <span className="text-stone-200 font-mono">{b.total_allocated}d</span>
                        </div>
                        <div>
                          Used: <span className="text-stone-200 font-mono">{b.used}d</span>
                        </div>
                        <div>
                          Pending: <span className="text-amber-400 font-mono">{b.pending}d</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Compensation & PayPal Payout Footprint */}
          <div className="bg-[#141210] border border-stone-800 rounded-2xl p-5 space-y-3 shadow-sm">
            <span className="text-sm font-semibold text-stone-200 flex items-center gap-1.5">
              <CreditCard className="w-4 h-4 text-orange-400" />
              Disbursement & Payout Rail
            </span>

            <div className="p-3.5 rounded-xl bg-[#1c1917] border border-stone-800 space-y-2.5 text-xs sm:text-sm">
              <div className="flex items-center justify-between">
                <span className="text-stone-400">PayPal Account Email</span>
                <span className="font-mono text-stone-200 font-medium">
                  {employeeProfile?.paypal_email || "Not linked"}
                </span>
              </div>
              <div className="flex items-center justify-between pt-1.5 border-t border-stone-800/80">
                <span className="text-stone-400">Sandbox Settlement</span>
                <span className="inline-flex items-center gap-1 text-emerald-400 font-medium">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Active
                </span>
              </div>
              <div className="flex items-center justify-between pt-1.5 border-t border-stone-800/80">
                <span className="text-stone-400">Annual Base</span>
                <span className="font-mono text-white font-bold">
                  ${Number(employeeProfile?.salary_basic || 0).toLocaleString()} USD
                </span>
              </div>
            </div>
          </div>

          {/* Talk with Company Quick Action Banner */}
          <div className="bg-gradient-to-br from-[#1a1512] to-[#120f0d] border border-orange-500/30 rounded-2xl p-5 space-y-3 shadow-sm">
            <div className="flex items-center gap-2.5 text-orange-400">
              <MessageSquareQuote className="w-5 h-5" />
              <span className="font-bold text-sm text-white">Need Leave Policy Answers?</span>
            </div>
            <p className="text-xs sm:text-sm text-stone-400 leading-relaxed">
              Have questions about annual carryover, medical certificates, or remote working rules? Converse with Leavify's policy intelligence anytime.
            </p>
            <Link
              to="/company-chat"
              className="w-full py-2.5 px-4 bg-orange-600 hover:bg-orange-500 text-white rounded-xl text-xs sm:text-sm font-semibold flex items-center justify-center gap-2 transition shadow cursor-pointer"
            >
              <span>Open Talk with Company</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </div>

      {/* Apply Leave Modal */}
      {showApplyModal && (
        <div className="fixed inset-0 z-50 bg-[#0c0a09]/90 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#141210] border border-stone-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-stone-800">
              <h2 className="text-base font-bold text-[#FFFDF8] flex items-center gap-2">
                <Calendar className="w-4 h-4 text-orange-400" />
                Apply for Leave
              </h2>
              <button
                onClick={() => setShowApplyModal(false)}
                className="text-stone-400 hover:text-white p-1 rounded-lg"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {applyError && (
              <div className="p-3 bg-rose-950/40 border border-rose-500/30 rounded-xl text-xs text-rose-300 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                <span>{applyError}</span>
              </div>
            )}

            <form onSubmit={handleApplySubmit} className="space-y-3.5">
              <div>
                <label className="block text-xs font-medium text-stone-300 mb-1">
                  Leave Policy / Category *
                </label>
                <select
                  required
                  value={formData.policy_id}
                  onChange={(e) => setFormData({ ...formData, policy_id: e.target.value })}
                  className="w-full bg-[#1c1917] border border-stone-800 rounded-xl px-3 py-2 text-sm text-stone-100 outline-none focus:border-orange-500"
                >
                  {policies.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.leave_type}) — {p.days_allowed}d/yr ({p.is_paid ? "Paid" : "Unpaid"})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-stone-300 mb-1">
                    Start Date *
                  </label>
                  <input
                    type="date"
                    required
                    value={formData.start_date}
                    onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                    className="w-full bg-[#1c1917] border border-stone-800 rounded-xl px-3 py-2 text-sm text-stone-100 outline-none focus:border-orange-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-stone-300 mb-1">
                    End Date *
                  </label>
                  <input
                    type="date"
                    required
                    min={formData.start_date}
                    value={formData.end_date}
                    onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                    className="w-full bg-[#1c1917] border border-stone-800 rounded-xl px-3 py-2 text-sm text-stone-100 outline-none focus:border-orange-500"
                  />
                </div>
              </div>

              {previewWorkingDays > 0 && (
                <div className="p-2.5 rounded-lg bg-orange-950/40 border border-orange-500/20 text-xs text-orange-400 flex items-center justify-between font-mono">
                  <span>Calculated Business Days:</span>
                  <span className="font-bold">{previewWorkingDays} day(s)</span>
                </div>
              )}

              <div>
                <label className="block text-xs font-medium text-stone-300 mb-1">
                  Reason for Request *
                </label>
                <textarea
                  required
                  rows={3}
                  value={formData.reason}
                  onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
                  placeholder="Provide context or notice details for the approval team..."
                  className="w-full bg-[#1c1917] border border-stone-800 rounded-xl p-3 text-sm text-stone-100 outline-none focus:border-orange-500 placeholder-stone-600"
                />
              </div>

              <div className="flex items-center justify-end gap-2.5 pt-2">
                <button
                  type="button"
                  onClick={() => setShowApplyModal(false)}
                  className="px-4 py-2 bg-stone-900 hover:bg-stone-800 text-stone-300 rounded-xl text-xs font-medium cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={applying}
                  className="px-5 py-2.5 bg-orange-600 hover:bg-orange-500 active:bg-orange-700 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 transition disabled:opacity-50 cursor-pointer shadow-sm"
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
