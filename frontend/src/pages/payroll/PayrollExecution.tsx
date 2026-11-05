import { useState, useEffect, useMemo } from "react";
import {
  CreditCard,
  Calendar,
  Loader2,
  DollarSign,
  Play,
  Check,
  FileText,
  X,
  Printer,
} from "lucide-react";
import { api } from "../../lib/api";
import { useAuthStore } from "../../store/authStore";
import Navbar from "../../components/layout/Navbar";

interface PayrollItem {
  id: string;
  batch_id: string;
  employee_id: string;
  employee_name: string;
  employee_code: string;
  department_name?: string;
  paypal_email?: string | null;
  basic_salary: number | string;
  total_allowances: number | string;
  gross_salary: number | string;
  paid_leave_days: number | string;
  unpaid_leave_days: number | string;
  unpaid_leave_deduction: number | string;
  attendance_days?: number | string;
  statutory_deductions: Record<string, any>;
  total_deductions: number | string;
  net_salary: number | string;
  status: string;
}

interface PayrollBatch {
  id: string;
  period_year: number;
  period_month: number;
  status: string;
  total_gross: number | string;
  total_deductions: number | string;
  total_net: number | string;
  employee_count: number;
  approved_at?: string | null;
  items: PayrollItem[];
}

interface BatchSummary {
  id: string;
  period_year: number;
  period_month: number;
  status: string;
  total_gross: number | string;
  total_deductions: number | string;
  total_net: number | string;
  employee_count: number;
  created_at: string;
}

interface PayslipData {
  payroll_item_id: string;
  batch_period: string;
  employee_name: string;
  employee_code: string;
  department: string;
  designation: string;
  paypal_email?: string | null;
  basic_salary: number | string;
  allowances: Record<string, any>;
  gross_earnings: number | string;
  unpaid_leave_days: number | string;
  unpaid_leave_deduction: number | string;
  statutory_deductions: Record<string, any>;
  total_deductions: number | string;
  net_payable: number | string;
  currency: string;
}

export default function PayrollExecution() {
  const { user } = useAuthStore();

  const [batches, setBatches] = useState<BatchSummary[]>([]);
  const [activeBatch, setActiveBatch] = useState<PayrollBatch | null>(null);
  const [loadingActive, setLoadingActive] = useState(false);
  const [calculating, setCalculating] = useState(false);
  const [approving, setApproving] = useState(false);

  // Month selector
  const today = new Date();
  const [selectedYear, setSelectedYear] = useState(today.getFullYear());
  const [selectedMonth, setSelectedMonth] = useState(today.getMonth() + 1);

  // Payslip modal state
  const [selectedPayslip, setSelectedPayslip] = useState<PayslipData | null>(null);

  const isHrOrAdmin = user?.role === "admin" || user?.role === "hr";

  const fetchBatches = async () => {
    try {
      const res = await api.get("/payroll/batches");
      setBatches(res.data);

      if (res.data.length > 0) {
        await loadBatchDetail(res.data[0].id);
      }
    } catch (err) {
      console.error("Failed to load payroll batches", err);
    }
  };

  const loadBatchDetail = async (batchId: string) => {
    try {
      setLoadingActive(true);
      const res = await api.get(`/payroll/batches/${batchId}`);
      setActiveBatch(res.data);
    } catch (err) {
      console.error("Failed to load batch detail", err);
    } finally {
      setLoadingActive(false);
    }
  };

  useEffect(() => {
    fetchBatches();
  }, []);

  const handleGeneratePayroll = async () => {
    try {
      setCalculating(true);
      const res = await api.post("/payroll/batches", {
        period_year: selectedYear,
        period_month: selectedMonth,
        notes: `Standard monthly run for ${selectedYear}-${selectedMonth}`,
      });
      setActiveBatch(res.data);
      await fetchBatches();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Calculation failed.");
    } finally {
      setCalculating(false);
    }
  };

  const handleApproveBatch = async () => {
    if (!activeBatch) return;
    try {
      setApproving(true);
      const res = await api.patch(`/payroll/batches/${activeBatch.id}/approve`);
      setActiveBatch(res.data);
      await fetchBatches();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Approval failed.");
    } finally {
      setApproving(false);
    }
  };

  const handleViewPayslip = async (itemId: string) => {
    try {
      const res = await api.get(`/payroll/payslips/${itemId}`);
      setSelectedPayslip(res.data);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to load payslip.");
    }
  };

  // Readiness calculations
  const paypalCoveragePercent = useMemo(() => {
    if (!activeBatch || !activeBatch.items.length) return 0;
    const withEmail = activeBatch.items.filter((i) => !!i.paypal_email).length;
    return Math.round((withEmail / activeBatch.items.length) * 100);
  }, [activeBatch]);

  const totalUnpaidSavings = useMemo(() => {
    if (!activeBatch) return 0;
    return activeBatch.items.reduce(
      (acc, i) => acc + Number(i.unpaid_leave_deduction || 0),
      0
    );
  }, [activeBatch]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans antialiased">
      <Navbar />

      <main className="flex-1 p-6 max-w-7xl w-full mx-auto space-y-6">
        {/* Title Bar & Trigger Controls */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              <CreditCard className="w-5 h-5 text-indigo-400" />
              Payroll Calculation & Settlement Engine
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Deterministic gross-to-net calculations reconciled with approved leave records.
            </p>
          </div>

          {isHrOrAdmin && (
            <div className="flex items-center gap-2.5">
              <div className="flex items-center gap-1.5 bg-slate-900 border border-slate-800 rounded-lg px-2 py-1">
                <select
                  value={selectedYear}
                  onChange={(e) => setSelectedYear(Number(e.target.value))}
                  className="bg-transparent text-xs text-slate-200 outline-none cursor-pointer"
                >
                  {[2025, 2026, 2027].map((y) => (
                    <option key={y} value={y} className="bg-slate-900">
                      {y}
                    </option>
                  ))}
                </select>
                <span className="text-slate-600">/</span>
                <select
                  value={selectedMonth}
                  onChange={(e) => setSelectedMonth(Number(e.target.value))}
                  className="bg-transparent text-xs text-slate-200 outline-none cursor-pointer"
                >
                  {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
                    <option key={m} value={m} className="bg-slate-900">
                      {new Date(2026, m - 1).toLocaleString("default", { month: "short" })}
                    </option>
                  ))}
                </select>
              </div>

              <button
                onClick={handleGeneratePayroll}
                disabled={calculating}
                className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer disabled:opacity-50 shadow-sm"
              >
                {calculating ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Play className="w-3.5 h-3.5 fill-current" />
                )}
                Run Payroll Batch
              </button>
            </div>
          )}
        </div>

        {/* PASS 1: Asymmetric 8:4 Structural Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Main 8-Column Active Batch Table */}
          <div className="lg:col-span-8 space-y-4">
            {activeBatch ? (
              <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden space-y-0">
                {/* Batch Header Bar */}
                <div className="p-4 border-b border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-slate-950/40">
                  <div>
                    <div className="flex items-center gap-2.5">
                      <span className="text-sm font-bold text-white">
                        Batch {activeBatch.period_year}-{String(activeBatch.period_month).padStart(2, "0")}
                      </span>
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded-full uppercase font-bold ${
                          activeBatch.status === "approved"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20"
                        }`}
                      >
                        {activeBatch.status}
                      </span>
                    </div>
                    <span className="text-[11px] font-mono text-slate-400 mt-0.5 block">
                      {activeBatch.employee_count} employees reconciled
                    </span>
                  </div>

                  {isHrOrAdmin && activeBatch.status !== "approved" && (
                    <button
                      onClick={handleApproveBatch}
                      disabled={approving}
                      className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer shadow-sm disabled:opacity-50"
                    >
                      {approving ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Check className="w-3.5 h-3.5" />
                      )}
                      Approve & Lock Batch
                    </button>
                  )}
                </div>

                {/* Items Table */}
                {loadingActive ? (
                  <div className="p-16 flex flex-col items-center justify-center gap-2">
                    <Loader2 className="w-6 h-6 animate-spin text-indigo-500" />
                    <span className="text-xs font-mono text-slate-400">Computing ledger line items...</span>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse text-xs">
                      <thead>
                        <tr className="border-b border-slate-800 bg-slate-950/60 text-[11px] font-mono text-slate-400 uppercase tracking-wider">
                          <th className="py-2.5 px-4">Employee</th>
                          <th className="py-2.5 px-4 text-right">Gross</th>
                          <th className="py-2.5 px-4 text-right">Unpaid Leave</th>
                          <th className="py-2.5 px-4 text-right">Deductions</th>
                          <th className="py-2.5 px-4 text-right">Net Payable</th>
                          <th className="py-2.5 px-4 text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60">
                        {activeBatch.items.map((item) => (
                          <tr key={item.id} className="hover:bg-slate-800/30 transition">
                            <td className="py-3 px-4">
                              <div className="font-semibold text-white">{item.employee_name}</div>
                              <div className="flex items-center gap-2 text-[10px] font-mono text-slate-400 mt-0.5">
                                <span>{item.employee_code}</span>
                                {item.paypal_email ? (
                                  <span className="text-indigo-400">PayPal: {item.paypal_email}</span>
                                ) : (
                                  <span className="text-slate-500">No PayPal</span>
                                )}
                              </div>
                            </td>
                            <td className="py-3 px-4 text-right font-mono text-slate-200">
                              ${Number(item.gross_salary).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                            </td>
                            <td className="py-3 px-4 text-right">
                              {Number(item.unpaid_leave_days) > 0 ? (
                                <div>
                                  <span className="font-mono text-rose-400 font-medium">
                                    -${Number(item.unpaid_leave_deduction).toFixed(2)}
                                  </span>
                                  <span className="text-[10px] text-slate-500 block font-mono">
                                    {item.unpaid_leave_days}d unpaid
                                  </span>
                                </div>
                              ) : (
                                <span className="font-mono text-slate-500">$0.00</span>
                              )}
                            </td>
                            <td className="py-3 px-4 text-right font-mono text-slate-400">
                              -${Number(item.total_deductions).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                            </td>
                            <td className="py-3 px-4 text-right font-mono font-bold text-white text-sm">
                              ${Number(item.net_salary).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                            </td>
                            <td className="py-3 px-4 text-right">
                              <button
                                onClick={() => handleViewPayslip(item.id)}
                                className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-[11px] font-medium transition cursor-pointer"
                              >
                                Payslip
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-16 rounded-xl bg-slate-900 border border-slate-800 text-center space-y-3">
                <CreditCard className="w-8 h-8 text-slate-600 mx-auto" />
                <div className="text-sm font-semibold text-slate-300">No Payroll Batch Active</div>
                <p className="text-xs text-slate-500 max-w-sm mx-auto">
                  Click "Run Payroll Batch" above to generate deterministic gross-to-net calculations.
                </p>
              </div>
            )}
          </div>

          {/* 4-Column Contextual Intelligence Rail */}
          <div className="lg:col-span-4 space-y-4">
            {/* Total Company Run Card */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
              <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                <DollarSign className="w-4 h-4 text-indigo-400" />
                Batch Settlement Summary
              </span>

              <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                <span className="text-[10px] font-mono text-slate-500 uppercase">Total Net Disbursement</span>
                <div className="text-2xl font-bold font-mono text-white">
                  ${Number(activeBatch?.total_net || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })} USD
                </div>
                <span className="text-[10px] text-slate-400 block pt-1">
                  Gross: ${Number(activeBatch?.total_gross || 0).toLocaleString()} • Deductions: ${Number(activeBatch?.total_deductions || 0).toLocaleString()}
                </span>
              </div>

              <div className="space-y-2 text-xs">
                <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between">
                  <span className="text-slate-400">Leave Reconciliation Savings</span>
                  <span className="font-mono text-emerald-400 font-bold">
                    +${totalUnpaidSavings.toFixed(2)} USD
                  </span>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between">
                  <span className="text-slate-400">PayPal Sandbox Payouts Coverage</span>
                  <span className="font-mono text-indigo-400 font-bold">
                    {paypalCoveragePercent}% ({activeBatch?.items.filter((i) => !!i.paypal_email).length}/{activeBatch?.items.length || 0})
                  </span>
                </div>
              </div>
            </div>

            {/* Historical Batches List */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
              <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                <Calendar className="w-4 h-4 text-indigo-400" />
                Historical Runs
              </span>

              {batches.length === 0 ? (
                <p className="text-xs text-slate-500 italic py-2">No historical batches recorded.</p>
              ) : (
                <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                  {batches.map((b) => (
                    <button
                      key={b.id}
                      onClick={() => loadBatchDetail(b.id)}
                      className={`w-full p-2.5 rounded-lg text-left text-xs transition cursor-pointer flex items-center justify-between ${
                        activeBatch?.id === b.id
                          ? "bg-slate-800 border border-slate-700 text-white"
                          : "bg-slate-950 border border-slate-800 text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      <div>
                        <span className="font-semibold block text-slate-200">
                          {b.period_year}-{String(b.period_month).padStart(2, "0")}
                        </span>
                        <span className="text-[10px] font-mono text-slate-500">
                          {b.employee_count} employees
                        </span>
                      </div>
                      <div className="text-right">
                        <span className="font-mono text-white font-bold block">
                          ${Number(b.total_net).toLocaleString()}
                        </span>
                        <span className="text-[9px] uppercase font-mono text-indigo-400">
                          {b.status}
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </main>

      {/* Printable Payslip Modal */}
      {selectedPayslip && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-indigo-400" />
                <h3 className="text-sm font-bold text-white">Itemized Payslip</h3>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => window.print()}
                  className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition cursor-pointer"
                  title="Print Payslip"
                >
                  <Printer className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => setSelectedPayslip(null)}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-white transition cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3 text-xs">
              <div className="flex justify-between items-start pb-2 border-b border-slate-900">
                <div>
                  <h4 className="font-bold text-white text-sm">{selectedPayslip.employee_name}</h4>
                  <span className="text-slate-400 font-mono text-[11px]">
                    {selectedPayslip.employee_code} • {selectedPayslip.department}
                  </span>
                </div>
                <span className="px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-mono text-[10px]">
                  Period: {selectedPayslip.batch_period}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-4 pt-1">
                <div className="space-y-1.5">
                  <span className="text-[10px] font-mono text-slate-500 uppercase block">Earnings</span>
                  <div className="flex justify-between text-slate-300">
                    <span>Base Monthly:</span>
                    <span className="font-mono text-white">${Number(selectedPayslip.basic_salary).toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-slate-300">
                    <span>Allowances:</span>
                    <span className="font-mono text-white">${(Number(selectedPayslip.gross_earnings) - Number(selectedPayslip.basic_salary)).toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between font-semibold text-white pt-1 border-t border-slate-900">
                    <span>Gross Earnings:</span>
                    <span className="font-mono">${Number(selectedPayslip.gross_earnings).toFixed(2)}</span>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <span className="text-[10px] font-mono text-slate-500 uppercase block">Deductions</span>
                  {Number(selectedPayslip.unpaid_leave_days) > 0 && (
                    <div className="flex justify-between text-rose-400">
                      <span>Unpaid Leave ({selectedPayslip.unpaid_leave_days}d):</span>
                      <span className="font-mono">-${Number(selectedPayslip.unpaid_leave_deduction).toFixed(2)}</span>
                    </div>
                  )}
                  <div className="flex justify-between text-slate-300">
                    <span>Tax (TDS):</span>
                    <span className="font-mono text-rose-400">
                      -${Number(selectedPayslip.statutory_deductions.income_tax_tds || 0).toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between text-slate-300">
                    <span>Provident Fund:</span>
                    <span className="font-mono text-rose-400">
                      -${Number(selectedPayslip.statutory_deductions.provident_fund || 0).toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between font-semibold text-rose-400 pt-1 border-t border-slate-900">
                    <span>Total Deductions:</span>
                    <span className="font-mono">-${Number(selectedPayslip.total_deductions).toFixed(2)}</span>
                  </div>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-indigo-950/30 border border-indigo-500/20 flex items-center justify-between text-xs mt-3">
                <span className="font-bold text-white">Net Take-Home Pay</span>
                <span className="font-mono font-bold text-base text-indigo-400">
                  ${Number(selectedPayslip.net_payable).toFixed(2)} USD
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
