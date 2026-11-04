import { useState, FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ShieldCheck, Lock, Mail, Loader2, Sparkles } from "lucide-react";
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
      setAuth(access_token, refresh_token, user);
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
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo and Brand */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 text-indigo-400 mb-4 shadow-lg shadow-indigo-500/10">
            <Sparkles className="w-7 h-7" />
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white">WorkforceAI</h1>
          <p className="text-slate-400 text-sm mt-1">
            Agentic AI Workforce & Payroll Operating System
          </p>
        </div>

        {/* Card */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-8 shadow-2xl backdrop-blur-sm">
          <h2 className="text-xl font-semibold text-white mb-2">Sign In</h2>
          <p className="text-xs text-slate-400 mb-6">
            Enter your organization credentials to access your portal.
          </p>

          {error && (
            <div className="mb-5 p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs font-medium">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Work Email
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="admin@workforceai.local"
                  className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded-xl pl-9 pr-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-600 outline-none transition"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded-xl pl-9 pr-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-600 outline-none transition"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium text-sm py-2.5 rounded-xl transition shadow-lg shadow-indigo-600/25 flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Authenticating...</span>
                </>
              ) : (
                <>
                  <ShieldCheck className="w-4 h-4" />
                  <span>Sign In</span>
                </>
              )}
            </button>
          </form>

          {/* Quick Demo Logins for Hackathon */}
          <div className="mt-6 pt-6 border-t border-slate-800/80">
            <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2">
              Demo Credentials (Click to prefill)
            </p>
            <div className="grid grid-cols-3 gap-2 text-xs">
              <button
                type="button"
                onClick={() => fillQuickLogin("admin@workforceai.local")}
                className="px-2.5 py-1.5 bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 rounded-lg text-slate-300 text-center transition"
              >
                Admin
              </button>
              <button
                type="button"
                onClick={() => fillQuickLogin("hr@workforceai.local")}
                className="px-2.5 py-1.5 bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 rounded-lg text-slate-300 text-center transition"
              >
                HR Lead
              </button>
              <button
                type="button"
                onClick={() => fillQuickLogin("rahul.sharma@workforceai.local")}
                className="px-2.5 py-1.5 bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 rounded-lg text-slate-300 text-center transition"
              >
                Employee
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
