import { useState } from "react";
import {
  X,
  CreditCard,
  ShieldCheck,
  Send,
  Loader2,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import { api } from "../../lib/api";

interface PayoutItem {
  id: string;
  employee_name: string;
  employee_code: string;
  paypal_email?: string | null;
  net_salary: number | string;
}

interface BatchForPayout {
  id: string;
  period_year: number;
  period_month: number;
  total_net: number | string;
  employee_count: number;
  items: PayoutItem[];
}

interface ExecutePayoutModalProps {
  batch: BatchForPayout;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export default function ExecutePayoutModal({
  batch,
  isOpen,
  onClose,
  onSuccess,
}: ExecutePayoutModalProps) {
  const [emailSubject, setEmailSubject] = useState(
    `WorkforceAI Salary Disbursement for ${batch.period_year}-${String(
      batch.period_month
    ).padStart(2, "0")}`
  );
  const [note, setNote] = useState(
    "Automated salary payout authorized via WorkforceAI deterministic payroll engine."
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [disbursementResult, setDisbursementResult] = useState<any | null>(null);

  if (!isOpen) return null;

  const handleExecutePayout = async () => {
    setSubmitting(true);
    setError(null);

    try {
      const res = await api.post(`/payments/disburse-payroll/${batch.id}`, {
        batch_id: batch.id,
        email_subject: emailSubject,
        note: note,
      });
      setDisbursementResult(res.data);
      onSuccess();
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          "Failed to execute PayPal payout disbursement. Please verify sandbox configuration."
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
      <div className="relative w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
              <CreditCard className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-white tracking-tight">
                  PayPal Sandbox Batch Payout
                </h3>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 uppercase font-bold">
                  Sandbox Active
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                Batch {batch.period_year}-{String(batch.period_month).padStart(2, "0")} • {batch.employee_count} Recipients
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 overflow-y-auto space-y-5 text-xs">
          {error && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold block">Disbursement Failed</span>
                <span className="text-[11px]">{error}</span>
              </div>
            </div>
          )}

          {disbursementResult ? (
            /* Success Receipt View */
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center gap-3">
                <CheckCircle2 className="w-5 h-5 shrink-0" />
                <div>
                  <div className="font-bold text-sm text-emerald-300">
                    Disbursement Executed Successfully
                  </div>
                  <div className="text-[11px] text-emerald-400/80 font-mono mt-0.5">
                    Batch ID: {disbursementResult.payout_batch_id}
                  </div>
                </div>
              </div>

              <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800 space-y-2">
                <div className="flex justify-between text-slate-400">
                  <span>Total Settled:</span>
                  <span className="font-mono text-white font-bold">
                    ${Number(disbursementResult.total_amount).toLocaleString(undefined, { minimumFractionDigits: 2 })} USD
                  </span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Recipient Count:</span>
                  <span className="font-mono text-slate-200">{disbursementResult.item_count}</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Disbursed Timestamp:</span>
                  <span className="font-mono text-slate-300 text-[11px]">
                    {new Date(disbursementResult.disbursed_at).toLocaleString()}
                  </span>
                </div>
              </div>

              {/* Itemized status */}
              <div className="space-y-2">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                  Disbursed Line Items ({disbursementResult.items.length})
                </span>
                <div className="border border-slate-800 rounded-lg overflow-hidden divide-y divide-slate-800/60 max-h-48 overflow-y-auto">
                  {disbursementResult.items.map((item: any, idx: number) => (
                    <div key={idx} className="p-2.5 flex items-center justify-between bg-slate-950/40">
                      <div>
                        <div className="font-medium text-white text-[11px]">{item.employee_name}</div>
                        <div className="text-[10px] font-mono text-slate-400">{item.recipient_email}</div>
                      </div>
                      <div className="text-right">
                        <div className="font-mono font-bold text-white text-xs">
                          ${Number(item.amount).toFixed(2)} USD
                        </div>
                        <div className="text-[9px] font-mono text-emerald-400 uppercase">
                          {item.status} • {item.transaction_id || "TRANS-RECORDED"}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            /* Disbursement Configuration View */
            <div className="space-y-4">
              {/* Summary Banner */}
              <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between">
                <div>
                  <span className="text-[10px] font-mono text-slate-500 uppercase block">Total Net Authorized</span>
                  <span className="text-xl font-bold font-mono text-white">
                    ${Number(batch.total_net).toLocaleString(undefined, { minimumFractionDigits: 2 })} USD
                  </span>
                </div>
                <div className="text-right">
                  <span className="text-[10px] font-mono text-slate-500 uppercase block">Employees Reconciled</span>
                  <span className="text-base font-bold font-mono text-indigo-400">
                    {batch.employee_count}
                  </span>
                </div>
              </div>

              {/* Input: Subject */}
              <div className="space-y-1.5">
                <label className="text-[11px] font-semibold text-slate-300">
                  Email Subject
                </label>
                <input
                  type="text"
                  value={emailSubject}
                  onChange={(e) => setEmailSubject(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 text-xs focus:outline-none focus:border-indigo-500"
                />
              </div>

              {/* Input: Note */}
              <div className="space-y-1.5">
                <label className="text-[11px] font-semibold text-slate-300">
                  Payment Note (Included in PayPal transaction)
                </label>
                <textarea
                  rows={2}
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 text-xs focus:outline-none focus:border-indigo-500 resize-none"
                />
              </div>

              {/* Recipients Preview */}
              <div className="space-y-1.5">
                <label className="text-[11px] font-semibold text-slate-300 block">
                  Disbursement Recipients Preview
                </label>
                <div className="border border-slate-800 rounded-lg overflow-hidden divide-y divide-slate-800/60 max-h-40 overflow-y-auto">
                  {batch.items.map((item) => (
                    <div key={item.id} className="p-2.5 flex items-center justify-between bg-slate-950/40">
                      <div>
                        <div className="font-medium text-white text-[11px]">{item.employee_name}</div>
                        <div className="text-[10px] font-mono text-slate-400">
                          {item.paypal_email || "Default Account Email"}
                        </div>
                      </div>
                      <div className="font-mono font-bold text-white text-xs">
                        ${Number(item.net_salary).toFixed(2)} USD
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Idempotency Protection Callout */}
              <div className="p-3 rounded-lg bg-indigo-500/5 border border-indigo-500/20 flex items-start gap-2.5 text-slate-300">
                <ShieldCheck className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                <div className="text-[11px] leading-relaxed">
                  <span className="font-semibold text-white">Idempotency & Re-entrancy Guarantee:</span> Each line item uses a unique SHA-derived idempotency token (`PAY-{"{batch}"}-{"{item}"}`). Re-transmitting will never result in duplicate charges.
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/60 flex items-center justify-end gap-2.5">
          {disbursementResult ? (
            <button
              onClick={onClose}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold transition cursor-pointer"
            >
              Done & Close
            </button>
          ) : (
            <>
              <button
                onClick={onClose}
                disabled={submitting}
                className="px-3.5 py-1.5 rounded-lg border border-slate-800 text-slate-300 hover:text-white hover:bg-slate-800 text-xs font-medium transition cursor-pointer disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleExecutePayout}
                disabled={submitting}
                className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer disabled:opacity-50 shadow-sm"
              >
                {submitting ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Send className="w-3.5 h-3.5" />
                )}
                Authorize & Disburse via PayPal
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
