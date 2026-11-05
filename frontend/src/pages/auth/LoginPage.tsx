import { useState, FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ShieldCheck, Lock, Mail, Loader2, Cpu, CheckCircle2, ArrowRight } from "lucide-react";
import { api } from "../../lib/api";
import { useAuthStore } from "../../store/authStore";

export default function LoginPage() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await api.post("/auth/login", { email, password });
      const { access_token, refresh_token, user } = res.data;
      if (user) {
        setAuth(access_token, refresh_token, user);
      } else {
        const meRes = await api.get("/auth/me", {
          headers: { Authorization: `Bearer ${access_token}` },
        });
        setAuth(access_token, refresh_token, meRes.data);
      }
      navigate("/employees");
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : "Invalid email or password. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  const fillQuickLogin = (roleEmail: string) => {
    setEmail(roleEmail);
    setPassword("Password123!");
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex">
      {/* PASS 1: Asymmetric Left Architecture Panel (Hidden on small screens) */}
      <div className="hidden lg:flex lg:w-5/12 bg-slate-900 border-r border-slate-800 flex-col justify-between p-12 relative overflow-hidden">
        {/* Subtle grid pattern background */}
        <div className="absolute inset-0 opacity-[0.03] pointer-events-none bg-[radial-gradient(#fff_1px,transparent_1px)] [background-size:16px_16px]" />

        <div>
          {/* Logo & Product Identity */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center font-bold text-lg text-white">
              W
            </div>
            <div>
              <span className="font-extrabold text-white text-lg tracking-tight block">
                WorkforceAI
              </span>
              <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400 block -mt-0.5">
                Enterprise Payroll OS
              </span>
            </div>
          </div>

          {/* Value Prop Headline */}
          <div className="mt-16 space-y-4">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              Neon Postgres 18.6 Live
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight text-white leading-tight">
              Agentic AI workforce & automated payroll operations.
            </h1>
            <p className="text-sm text-slate-400 leading-relaxed">
              Autonomous workforce management engine with vector memory, dual compliance rails, and automated PayPal Payouts.
            </p>
          </div>
        </div>

        {/* System Capabilities Rail */}
        <div className="space-y-4 pt-12 border-t border-slate-800/80">
          <div className="flex items-start gap-3">
            <Cpu className="w-5 h-5 text-indigo-400 mt-0.5 shrink-0" />
            <div>
              <div className="text-xs font-semibold text-white">Continuous Policy Verification</div>
              <div className="text-[11px] text-slate-400 leading-normal">
                Autonomous leave ledger balancing and tax bracket deduction engine.
              </div>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <CheckCircle2 className="w-5 h-5 text-indigo-400 mt-0.5 shrink-0" />
            <div>
              <div className="text-xs font-semibold text-white">Pluggable Settlement Rails</div>
              <div className="text-[11px] text-slate-400 leading-normal">
                PayPal Sandbox Payouts API paired with clean domestic banking abstractions.
              </div>
            </div>
          </div>
        </div>

        {/* Footer Meta */}
        <div className="text-[11px] text-slate-500 font-mono tracking-tight">
          BUILD 2026.11 // PAYPAL AI HACKATHON
        </div>
      </div>

      {/* PASS 2 & 3: Right Form Panel (Asymmetric 7/12 width) */}
      <div className="flex-1 flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-md space-y-8">
          <div>
            {/* Mobile Header */}
            <div className="flex items-center gap-3 lg:hidden mb-6">
              <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center font-bold text-white text-base">
                W
              </div>
              <span className="font-extrabold text-white text-base tracking-tight">
                WorkforceAI
              </span>
            </div>

            <h2 className="text-2xl font-bold tracking-tight text-white">
              Sign in to your organization
            </h2>
            <p className="text-xs text-slate-400 mt-1.5 tracking-normal">
              Enter your corporate credentials to access the management portal.
            </p>
          </div>

          {error && (
            <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs font-medium leading-relaxed">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-xs font-semibold tracking-wide text-slate-300 uppercase mb-2">
                Work Email
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-500 absolute left-3.5 top-3.5" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="admin@workforce.io"
                  className="w-full bg-slate-900 border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded-xl pl-10 pr-4 py-2.5 text-sm text-slate-100 placeholder-slate-600 outline-none transition"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-xs font-semibold tracking-wide text-slate-300 uppercase">
                  Password
                </label>
              </div>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-500 absolute left-3.5 top-3.5" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-slate-900 border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded-xl pl-10 pr-4 py-2.5 text-sm text-slate-100 placeholder-slate-600 outline-none transition"
                />
              </div>
            </div>

            {/* PASS 4: Action Button with Crisp Micro-interactions */}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-indigo-600 hover:bg-indigo-500 active:scale-[0.99] disabled:opacity-50 text-white font-semibold text-sm py-2.5 rounded-xl transition flex items-center justify-center gap-2 cursor-pointer shadow-none"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Authenticating...</span>
                </>
              ) : (
                <>
                  <span>Sign In</span>
                  <ArrowRight className="w-4 h-4 text-indigo-200" />
                </>
              )}
            </button>
          </form>

          {/* Quick Demo Credentials Panel */}
          <div className="pt-6 border-t border-slate-800">
            <div className="flex items-center justify-between mb-3">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Demo Credentials
              </span>
              <span className="text-[10px] text-slate-500 font-mono">Click to autofill</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
              <button
                type="button"
                onClick={() => fillQuickLogin("admin@workforce.io")}
                className="p-3 bg-slate-900 hover:bg-slate-800/80 border border-slate-800 hover:border-slate-700 rounded-xl text-left transition flex items-center justify-between group"
              >
                <div>
                  <div className="font-semibold text-white group-hover:text-indigo-400 transition">
                    Administrator
                  </div>
                  <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                    admin@workforce.io
                  </div>
                </div>
                <ShieldCheck className="w-4 h-4 text-slate-500 group-hover:text-indigo-400 transition" />
              </button>

              <button
                type="button"
                onClick={() => fillQuickLogin("aarav.sharma@workforce.io")}
                className="p-3 bg-slate-900 hover:bg-slate-800/80 border border-slate-800 hover:border-slate-700 rounded-xl text-left transition flex items-center justify-between group"
              >
                <div>
                  <div className="font-semibold text-white group-hover:text-indigo-400 transition">
                    Lead Architect
                  </div>
                  <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                    aarav.sharma@workforce.io
                  </div>
                </div>
                <ShieldCheck className="w-4 h-4 text-slate-500 group-hover:text-indigo-400 transition" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
