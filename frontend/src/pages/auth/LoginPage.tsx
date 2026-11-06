import { useState, FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import {
  ShieldCheck,
  Lock,
  Mail,
  Loader2,
  Cpu,
  CheckCircle2,
  ArrowRight,
  Building2,
  CreditCard,
} from "lucide-react";
import { api } from "../../lib/api";
import { useAuthStore } from "../../store/authStore";

export default function LoginPage() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);

  const [activeTab, setActiveTab] = useState<"login" | "register">("login");

  // Sign In Form State
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  // Register Organization / CEO Form State
  const [regData, setRegData] = useState({
    company_name: "",
    ceo_first_name: "",
    ceo_last_name: "",
    password: "",
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Live corporate email preview computation
  const previewDomain =
    regData.company_name.toLowerCase().replace(/[^a-z0-9]+/g, "") || "company";
  const previewUser = `${
    regData.ceo_first_name.toLowerCase().replace(/[^a-z0-9]+/g, "") || "firstname"
  }.${
    regData.ceo_last_name.toLowerCase().replace(/[^a-z0-9]+/g, "") || "lastname"
  }`;
  const previewEmail = `${previewUser}@${previewDomain}.workforce.io`;

  const handleLoginSubmit = async (e: FormEvent) => {
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
      navigate("/dashboard");
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

  const handleRegisterSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      // Register company & CEO account with auto-provisioned WorkforceAI corporate email
      const res = await api.post("/auth/register-company", {
        company_name: regData.company_name.trim(),
        ceo_first_name: regData.ceo_first_name.trim(),
        ceo_last_name: regData.ceo_last_name.trim(),
        password: regData.password,
      });

      const { access_token, refresh_token, user } = res.data;
      if (user) {
        setAuth(access_token, refresh_token, user);
      } else {
        const meRes = await api.get("/auth/me", {
          headers: { Authorization: `Bearer ${access_token}` },
        });
        setAuth(access_token, refresh_token, meRes.data);
      }

      setSuccessMsg(
        `Welcome CEO! Corporate email assigned: ${user?.email || previewEmail}`
      );
      setTimeout(() => navigate("/dashboard"), 700);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : "Company registration failed. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  const fillQuickLogin = (roleEmail: string) => {
    setActiveTab("login");
    setEmail(roleEmail);
    setPassword("Password123!");
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex font-sans antialiased">
      {/* PASS 1: Asymmetric Left Architecture Panel (Hidden on small screens) */}
      <div className="hidden lg:flex lg:w-5/12 bg-slate-900 border-r border-slate-800 flex-col justify-between p-12 relative overflow-hidden">
        {/* Subtle dot pattern */}
        <div className="absolute inset-0 pointer-events-none [background-image:radial-gradient(var(--surface-grid)_1px,transparent_1px)] [background-size:16px_16px]" />

        <div>
          {/* Logo & Product Identity */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center font-bold text-lg text-white shadow-sm">
              W
            </div>
            <div>
              <span className="font-extrabold text-white text-lg tracking-tight block">
                WorkforceAI
              </span>
              <span className="text-xs font-medium text-slate-400 block -mt-0.5">
                Enterprise Payroll OS
              </span>
            </div>
          </div>

          {/* Value Prop Headline */}
          <div className="mt-14 space-y-4">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              Neon Postgres 18.6 Live
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight text-white leading-tight">
              Agentic AI workforce & automated payroll operations.
            </h1>
            <p className="text-xs text-slate-400 leading-relaxed">
              Autonomous workforce engine with LangGraph supervisors, deterministic leave reconciliation, and PayPal Payouts integration.
            </p>
          </div>
        </div>

        {/* Telemetry Architecture Cards */}
        <div className="space-y-3.5 pt-8 border-t border-slate-800/80">
          <div className="flex items-start gap-3">
            <Cpu className="w-4 h-4 text-indigo-400 mt-1 shrink-0" />
            <div>
              <div className="text-xs font-semibold text-white">LangGraph AI Policy Supervisor</div>
              <div className="text-[11px] text-slate-400 leading-normal">
                Natural language parsing, SQL balance verification, and transparent rule citations.
              </div>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <CreditCard className="w-4 h-4 text-indigo-400 mt-1 shrink-0" />
            <div>
              <div className="text-xs font-semibold text-white">Deterministic Payroll Engine</div>
              <div className="text-[11px] text-slate-400 leading-normal">
                Reconciles unpaid leave deductions using Python Decimal zero-float precision.
              </div>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <CheckCircle2 className="w-4 h-4 text-indigo-400 mt-1 shrink-0" />
            <div>
              <div className="text-xs font-semibold text-white">PayPal Sandbox Disbursements</div>
              <div className="text-[11px] text-slate-400 leading-normal">
                Automated batch payouts with sender idempotency and cryptographic webhook audits.
              </div>
            </div>
          </div>
        </div>

        {/* Footer Meta */}
        <div className="text-xs text-slate-500 tracking-tight pt-4">
          PayPal AI Hackathon 2026 · Build Production
        </div>
      </div>

      {/* PASS 2 & 3: Right Form Viewport (Asymmetric 7/12 width) */}
      <div className="flex-1 flex items-center justify-center p-6 sm:p-12 overflow-y-auto">
        <div className="w-full max-w-md space-y-6">
          {/* Mobile Header */}
          <div className="flex items-center gap-3 lg:hidden">
            <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center font-bold text-white text-base">
              W
            </div>
            <span className="font-extrabold text-white text-base tracking-tight">
              WorkforceAI
            </span>
          </div>

          {/* Tab Selector: Sign In vs Register Organization */}
          <div className="bg-slate-900 p-1 rounded-xl border border-slate-800 flex items-center gap-1">
            <button
              type="button"
              onClick={() => {
                setActiveTab("login");
                setError(null);
              }}
              className={`flex-1 py-2 text-xs font-semibold rounded-lg transition cursor-pointer text-center ${
                activeTab === "login"
                  ? "bg-slate-800 text-white border border-slate-700 shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => {
                setActiveTab("register");
                setError(null);
              }}
              className={`flex-1 py-2 text-xs font-semibold rounded-lg transition cursor-pointer text-center ${
                activeTab === "register"
                  ? "bg-slate-800 text-white border border-slate-700 shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Register as Company CEO
            </button>
          </div>

          {/* Form Header */}
          <div>
            <h2 className="text-xl font-bold tracking-tight text-white">
              {activeTab === "login" ? "Sign in to your organization" : "Register company as CEO"}
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              {activeTab === "login"
                ? "Enter your provisioned WorkforceAI corporate email and password (CEO, HR, Finance, or Employee)."
                : "Register as Company CEO. Team members and employees should use 'Sign In' with credentials issued by their company."}
            </p>
          </div>

          {/* Alerts */}
          {error && (
            <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs font-medium leading-relaxed">
              {error}
            </div>
          )}

          {successMsg && (
            <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs font-medium leading-relaxed flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
              <span>{successMsg}</span>
            </div>
          )}

          {/* SIGN IN FORM */}
          {activeTab === "login" ? (
            <form onSubmit={handleLoginSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Work Email
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="admin@workforce.io"
                    className="w-full bg-slate-900 border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded-xl pl-10 pr-4 py-2 text-xs text-slate-100 placeholder-slate-600 outline-none transition"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full bg-slate-900 border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded-xl pl-10 pr-4 py-2 text-xs text-slate-100 placeholder-slate-600 outline-none transition"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-indigo-600 hover:bg-indigo-500 active:scale-[0.99] disabled:opacity-50 text-white font-semibold text-xs py-2.5 rounded-xl transition flex items-center justify-center gap-2 cursor-pointer shadow-sm"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Authenticating...</span>
                  </>
                ) : (
                  <>
                    <span>Sign In</span>
                    <ArrowRight className="w-3.5 h-3.5 text-indigo-200" />
                  </>
                )}
              </button>
            </form>
          ) : (
            /* REGISTER AS COMPANY CEO FORM */
            <form onSubmit={handleRegisterSubmit} className="space-y-3.5">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Organization / Company Name
                </label>
                <div className="relative">
                  <Building2 className="w-4 h-4 text-slate-500 absolute left-3.5 top-2.5" />
                  <input
                    type="text"
                    required
                    value={regData.company_name}
                    onChange={(e) =>
                      setRegData({ ...regData, company_name: e.target.value })
                    }
                    placeholder="Acme Global Inc"
                    className="w-full bg-slate-900 border border-slate-800 focus:border-indigo-500 rounded-xl pl-10 pr-4 py-2 text-xs text-slate-100 placeholder-slate-600 outline-none transition"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    CEO First Name
                  </label>
                  <input
                    type="text"
                    required
                    value={regData.ceo_first_name}
                    onChange={(e) =>
                      setRegData({ ...regData, ceo_first_name: e.target.value })
                    }
                    placeholder="Jane"
                    className="w-full bg-slate-900 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-100 placeholder-slate-600 outline-none transition"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    CEO Last Name
                  </label>
                  <input
                    type="text"
                    required
                    value={regData.ceo_last_name}
                    onChange={(e) =>
                      setRegData({ ...regData, ceo_last_name: e.target.value })
                    }
                    placeholder="Doe"
                    className="w-full bg-slate-900 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-100 placeholder-slate-600 outline-none transition"
                  />
                </div>
              </div>

              {/* Live Auto-Provisioned Antigravity WorkforceAI Email Display */}
              <div className="p-3 bg-slate-900 rounded-xl border border-indigo-500/30 text-xs space-y-1.5">
                <div className="flex items-center gap-1.5 text-indigo-400 font-semibold text-[11px]">
                  <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Provisioned WorkforceAI Corporate Email</span>
                </div>
                <div className="font-mono text-white text-xs bg-slate-950 px-2.5 py-1.5 rounded-lg border border-slate-800 break-all select-all">
                  {previewEmail}
                </div>
                <div className="text-[10px] text-slate-400 leading-tight">
                  No personal email required. As CEO and for every team member, WorkforceAI issues a unique corporate login.
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  CEO Master Password (min 8 characters)
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-500 absolute left-3.5 top-2.5" />
                  <input
                    type="password"
                    required
                    minLength={8}
                    value={regData.password}
                    onChange={(e) =>
                      setRegData({ ...regData, password: e.target.value })
                    }
                    placeholder="••••••••"
                    className="w-full bg-slate-900 border border-slate-800 focus:border-indigo-500 rounded-xl pl-10 pr-4 py-2 text-xs text-slate-100 placeholder-slate-600 outline-none transition"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-indigo-600 hover:bg-indigo-500 active:scale-[0.99] disabled:opacity-50 text-white font-semibold text-xs py-2.5 rounded-xl transition flex items-center justify-center gap-2 cursor-pointer shadow-sm mt-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Registering Company as CEO...</span>
                  </>
                ) : (
                  <>
                    <span>Register Company & Launch as CEO</span>
                    <ArrowRight className="w-3.5 h-3.5 text-indigo-200" />
                  </>
                )}
              </button>
            </form>
          )}

          {/* Quick Demo Credentials Panel */}
          <div className="pt-5 border-t border-slate-800/80">
            <div className="flex items-center justify-between mb-2.5">
              <span className="text-xs font-semibold text-slate-400">
                Demo Credentials
              </span>
              <span className="text-xs text-slate-500">1-click autofill</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
              <button
                type="button"
                onClick={() => fillQuickLogin("admin@workforce.io")}
                className="p-2.5 bg-slate-900 hover:bg-slate-800/80 border border-slate-800 hover:border-slate-700 rounded-xl text-left transition flex items-center justify-between group cursor-pointer"
              >
                <div>
                  <div className="font-semibold text-white group-hover:text-indigo-400 transition text-xs">
                    Administrator
                  </div>
                  <div className="text-[10px] text-slate-400 font-mono mt-0.5">
                    admin@workforce.io
                  </div>
                </div>
                <ShieldCheck className="w-3.5 h-3.5 text-slate-500 group-hover:text-indigo-400 transition" />
              </button>

              <button
                type="button"
                onClick={() => fillQuickLogin("aarav.sharma@workforce.io")}
                className="p-2.5 bg-slate-900 hover:bg-slate-800/80 border border-slate-800 hover:border-slate-700 rounded-xl text-left transition flex items-center justify-between group cursor-pointer"
              >
                <div>
                  <div className="font-semibold text-white group-hover:text-indigo-400 transition text-xs">
                    Lead Architect
                  </div>
                  <div className="text-[10px] text-slate-400 font-mono mt-0.5">
                    aarav.sharma@workforce.io
                  </div>
                </div>
                <ShieldCheck className="w-3.5 h-3.5 text-slate-500 group-hover:text-indigo-400 transition" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
