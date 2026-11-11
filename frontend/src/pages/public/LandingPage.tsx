import { useState, useEffect, FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Lock,
  Mail,
  Loader2,
  CheckCircle2,
  ArrowRight,
  Building2,
  Sparkles,
  KeyRound,
  X,
  CreditCard,
  Zap,
  Check,
  AlertTriangle,
  Bot,
  Cpu,
  ChevronDown,
  ChevronUp,
  Inbox,
  Calendar,
  Layers,
  HelpCircle,
} from "lucide-react";
import { api } from "../../lib/api";
import { useAuthStore } from "../../store/authStore";

interface LandingPageProps {
  defaultTab?: "login" | "register";
}

export default function LandingPage({ defaultTab = "login" }: LandingPageProps) {
  const navigate = useNavigate();
  const { isAuthenticated, user, setAuth, logout } = useAuthStore();

  const [activeTab, setActiveTab] = useState<"login" | "register">(defaultTab);

  // Sign In State
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  // Register Organization State
  const [regData, setRegData] = useState({
    company_name: "",
    company_domain: "",
    organization_email: "",
    otp: "",
    ceo_first_name: "",
    ceo_last_name: "",
    password: "",
  });

  const [otpSent, setOtpSent] = useState(false);
  const [otpVerified, setOtpVerified] = useState(false);
  const [sendingOtp, setSendingOtp] = useState(false);
  const [verifyingOtp, setVerifyingOtp] = useState(false);
  const [otpCooldown, setOtpCooldown] = useState(0);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Forgot Password Modal State
  const [showForgotModal, setShowForgotModal] = useState(false);
  const [forgotEmail, setForgotEmail] = useState("");
  const [forgotOtp, setForgotOtp] = useState("");
  const [forgotNewPassword, setForgotNewPassword] = useState("");
  const [forgotStep, setForgotStep] = useState<"request" | "reset">("request");
  const [forgotLoading, setForgotLoading] = useState(false);
  const [forgotError, setForgotError] = useState<string | null>(null);
  const [forgotSuccess, setForgotSuccess] = useState<string | null>(null);

  // FAQ Accordion State
  const [openFaqIndex, setOpenFaqIndex] = useState<number | null>(0);

  const fillDemoAccount = (demoEmail: string, demoPass: string = "password123") => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setError(null);
    setSuccessMsg(null);
  };

  useEffect(() => {
    if (otpCooldown > 0) {
      const timer = setTimeout(() => setOtpCooldown((prev) => prev - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [otpCooldown]);

  const handleSendOtp = async () => {
    if (!regData.organization_email || !regData.organization_email.includes("@")) {
      setError("Please enter a valid organization Gmail address first.");
      return;
    }
    setError(null);
    setSendingOtp(true);
    try {
      await api.post("/auth/send-org-otp", { email: regData.organization_email.trim() });
      setOtpSent(true);
      setOtpCooldown(45);
      setSuccessMsg(
        `Verification code dispatched to ${regData.organization_email}! Please check your email inbox (and spam folder).`
      );
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Failed to send verification code.");
    } finally {
      setSendingOtp(false);
    }
  };

  const handleVerifyOtp = async () => {
    if (!regData.otp || regData.otp.trim().length !== 6) {
      setError("Please enter the 6-digit code received in your email.");
      return;
    }
    setError(null);
    setVerifyingOtp(true);
    try {
      await api.post("/auth/verify-org-otp", {
        email: regData.organization_email.trim(),
        otp: regData.otp.trim(),
      });
      setOtpVerified(true);
      setSuccessMsg("Organization email verified successfully!");
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Invalid or expired verification code.");
    } finally {
      setVerifyingOtp(false);
    }
  };

  const rawOrgSlug =
    regData.company_name.toLowerCase().replace(/[^a-z0-9]+/g, "") || "organization";
  const previewDomain =
    regData.company_domain.trim().toLowerCase().replace(/^@/, "") || `${rawOrgSlug}.com`;
  const previewUser = `${
    regData.ceo_first_name.toLowerCase().replace(/[^a-z0-9]+/g, "") || "firstname"
  }.${
    regData.ceo_last_name.toLowerCase().replace(/[^a-z0-9]+/g, "") || "lastname"
  }`;
  const previewEmail = `${previewUser}@${previewDomain}`;

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
    if (!otpVerified) {
      setError("You must verify your organization email with the 6-digit code before registering.");
      return;
    }
    setError(null);
    setLoading(true);

    try {
      const payload = {
        company_name: regData.company_name.trim(),
        organization_email: regData.organization_email.trim(),
        otp: regData.otp.trim(),
        company_domain: previewDomain,
        ceo_first_name: regData.ceo_first_name.trim(),
        ceo_last_name: regData.ceo_last_name.trim(),
        password: regData.password,
      };

      const res = await api.post("/auth/register-company", payload);
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
          : "Company registration failed. Please check your verification code and try again."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleForgotRequestOtp = async (e: FormEvent) => {
    e.preventDefault();
    if (!forgotEmail || !forgotEmail.includes("@")) {
      setForgotError("Please enter a valid account email address.");
      return;
    }
    setForgotError(null);
    setForgotLoading(true);
    try {
      await api.post("/auth/forgot-password/request", { email: forgotEmail.trim() });
      setForgotStep("reset");
      setForgotSuccess(`Verification code dispatched to ${forgotEmail}! Please check your email inbox (and spam folder).`);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setForgotError(typeof detail === "string" ? detail : "Failed to dispatch reset code.");
    } finally {
      setForgotLoading(false);
    }
  };

  const handleForgotResetPassword = async (e: FormEvent) => {
    e.preventDefault();
    if (!forgotOtp || forgotOtp.trim().length !== 6) {
      setForgotError("Please enter the 6-digit code received in your email.");
      return;
    }
    if (!forgotNewPassword || forgotNewPassword.length < 8) {
      setForgotError("New password must be at least 8 characters long.");
      return;
    }
    setForgotError(null);
    setForgotLoading(true);
    try {
      await api.post("/auth/forgot-password/reset", {
        email: forgotEmail.trim(),
        otp: forgotOtp.trim(),
        new_password: forgotNewPassword,
      });
      setShowForgotModal(false);
      setSuccessMsg("Password successfully reset! You can now sign in with your new password.");
      setEmail(forgotEmail);
      setPassword(forgotNewPassword);
      setForgotStep("request");
      setForgotOtp("");
      setForgotNewPassword("");
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setForgotError(typeof detail === "string" ? detail : "Failed to reset password.");
    } finally {
      setForgotLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0c0a09] text-[#FAF8F5] flex flex-col font-sans selection:bg-orange-500/30 selection:text-orange-200">
      {/* Top Navigation Header */}
      <header className="border-b border-stone-800/80 bg-[#0c0a09]/90 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-orange-600 flex items-center justify-center font-bold text-white shadow-lg shadow-orange-600/20">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-lg font-bold text-white tracking-tight">Leavify.ai</span>
                <span className="text-[11px] font-mono text-orange-400 bg-orange-950/60 border border-orange-500/30 px-2 py-0.5 rounded-full">
                  v1.0
                </span>
              </div>
            </div>
          </div>

          <nav className="hidden lg:flex items-center gap-6 text-xs text-stone-400 font-medium">
            <a href="#auth-console" className="hover:text-orange-400 transition">Console</a>
            <a href="#agents" className="hover:text-orange-400 transition">5 Autonomous Agents</a>
            <a href="#lifecycle" className="hover:text-orange-400 transition">Workflow</a>
            <a href="#faq" className="hover:text-orange-400 transition">FAQ</a>
          </nav>

          <div className="flex items-center gap-4">
            <div className="hidden md:flex items-center gap-2 text-xs font-mono text-stone-400 bg-[#141210] px-3 py-1.5 rounded-xl border border-stone-800">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span>System 1 & System 2 Online</span>
            </div>

            {isAuthenticated ? (
              <div className="flex items-center gap-3">
                <Link
                  to="/dashboard"
                  className="px-4 py-2 bg-orange-600 hover:bg-orange-500 text-white rounded-xl text-xs sm:text-sm font-semibold flex items-center gap-2 transition cursor-pointer shadow-sm"
                >
                  <span>Open Workspace</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>
                <button
                  onClick={logout}
                  className="text-xs text-stone-400 hover:text-white transition cursor-pointer"
                >
                  Sign Out
                </button>
              </div>
            ) : (
              <a
                href="#auth-console"
                className="px-4 py-2 bg-stone-900 hover:bg-stone-800 text-stone-200 hover:text-white border border-stone-800 rounded-xl text-xs sm:text-sm font-medium transition cursor-pointer"
              >
                Launch Console
              </a>
            )}
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 lg:py-16 space-y-16">
        {/* Hero Section */}
        <div className="text-center max-w-4xl mx-auto space-y-6">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-orange-950/40 border border-orange-500/30 text-orange-400 text-xs font-medium">
            <CreditCard className="w-3.5 h-3.5 text-orange-400" />
            <span>Powered by PayPal Developer Platform & Multi-Agent LLMs</span>
          </div>

          <h1 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white leading-[1.15]">
            Autonomous Leave Intelligence &{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-orange-400 to-amber-300">
              Deterministic Payroll Rails
            </span>
          </h1>

          <p className="text-base sm:text-xl text-stone-300 leading-relaxed max-w-3xl mx-auto">
            Stop losing 40+ hours every month chasing leave requests across email threads, arguing over policy quotas, and recalculating pro-rata salary cuts on spreadsheets.
          </p>

          <div className="flex flex-wrap items-center justify-center gap-4 pt-2 text-xs sm:text-sm text-stone-400">
            <div className="flex items-center gap-2 bg-[#141210] px-3.5 py-1.5 rounded-xl border border-stone-800">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>Zero Policy Hallucinations</span>
            </div>
            <div className="flex items-center gap-2 bg-[#141210] px-3.5 py-1.5 rounded-xl border border-stone-800">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>Deterministic Loss-of-Pay Math</span>
            </div>
            <div className="flex items-center gap-2 bg-[#141210] px-3.5 py-1.5 rounded-xl border border-stone-800">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>One-Click PayPal Batch Payouts</span>
            </div>
          </div>
        </div>

        {/* Centerpiece: Interactive Auth Console */}
        <div id="auth-console" className="max-w-xl mx-auto w-full">
          {isAuthenticated && user ? (
            <div className="p-8 rounded-3xl bg-[#141210] border border-orange-500/30 text-center space-y-6 shadow-2xl">
              <div className="w-16 h-16 rounded-2xl bg-orange-600/20 border border-orange-500/40 text-orange-400 flex items-center justify-center mx-auto">
                <Building2 className="w-8 h-8" />
              </div>
              <div className="space-y-2">
                <span className="text-xs font-mono uppercase tracking-wider text-orange-400 bg-orange-950/60 px-2.5 py-1 rounded-md border border-orange-500/20">
                  Active Session Detected
                </span>
                <h3 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
                  Welcome back, {user.email}
                </h3>
                <p className="text-xs sm:text-sm text-stone-400">
                  Role: <span className="font-mono text-stone-200 font-semibold">{user.role.toUpperCase()}</span> · Organization:{" "}
                  <span className="text-white font-medium">{user.company_name || "Enterprise Workspace"}</span>
                </p>
              </div>

              <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3">
                <Link
                  to="/dashboard"
                  className="w-full sm:w-auto px-6 py-3.5 bg-orange-600 hover:bg-orange-500 active:bg-orange-700 text-white font-semibold rounded-xl text-sm flex items-center justify-center gap-2 transition cursor-pointer shadow-lg shadow-orange-600/20"
                >
                  <span>Continue to Workspace Dashboard</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>
                <button
                  type="button"
                  onClick={logout}
                  className="w-full sm:w-auto px-4 py-3.5 bg-stone-900 hover:bg-stone-800 text-stone-300 hover:text-white rounded-xl text-sm border border-stone-800 transition cursor-pointer"
                >
                  Switch Account
                </button>
              </div>
            </div>
          ) : (
            <div className="bg-[#141210] border border-stone-800 rounded-3xl p-6 sm:p-8 space-y-6 shadow-2xl">
              {/* Tab Selector */}
              <div className="flex rounded-xl bg-stone-900/90 p-1 border border-stone-800">
                <button
                  type="button"
                  onClick={() => {
                    setActiveTab("login");
                    setError(null);
                    setSuccessMsg(null);
                  }}
                  className={`flex-1 py-2.5 text-xs sm:text-sm font-semibold rounded-lg transition-all cursor-pointer ${
                    activeTab === "login"
                      ? "bg-stone-800 text-white shadow-sm"
                      : "text-stone-400 hover:text-stone-200"
                  }`}
                >
                  Sign In
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setActiveTab("register");
                    setError(null);
                    setSuccessMsg(null);
                  }}
                  className={`flex-1 py-2.5 text-xs sm:text-sm font-semibold rounded-lg transition-all cursor-pointer ${
                    activeTab === "register"
                      ? "bg-orange-600 text-white shadow-sm"
                      : "text-stone-400 hover:text-stone-200"
                  }`}
                >
                  Register Organization
                </button>
              </div>

              {/* Feedback Banners */}
              {error && (
                <div className="p-3.5 rounded-xl bg-rose-950/60 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-rose-400 shrink-0"></span>
                  <span>{error}</span>
                </div>
              )}
              {successMsg && (
                <div className="p-3.5 rounded-xl bg-emerald-950/60 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>{successMsg}</span>
                </div>
              )}

              {/* SIGN IN TAB */}
              {activeTab === "login" ? (
                <form onSubmit={handleLoginSubmit} className="space-y-4">
                  {/* Quick Evaluation Demo Logins */}
                  <div className="p-3 rounded-2xl bg-[#1c1917] border border-stone-800 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-mono uppercase tracking-wider text-orange-400 font-semibold flex items-center gap-1.5">
                        <Sparkles className="w-3.5 h-3.5 text-orange-400" />
                        <span>Instant Demo Evaluation</span>
                      </span>
                      <span className="text-[10px] text-stone-500">Click to autofill credentials</span>
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                      <button
                        type="button"
                        onClick={() => fillDemoAccount("anujwagmore835@gmail.com", "password123")}
                        className="p-2 rounded-xl bg-[#141210] hover:bg-stone-800 text-stone-300 hover:text-white border border-stone-800 text-left transition cursor-pointer group"
                      >
                        <div className="text-[11px] font-bold text-white group-hover:text-orange-400 transition">CEO / Admin</div>
                        <div className="text-[10px] text-stone-500 truncate">anujwagmore835@...</div>
                      </button>
                      <button
                        type="button"
                        onClick={() => fillDemoAccount("hr@leavify.ai", "password123")}
                        className="p-2 rounded-xl bg-[#141210] hover:bg-stone-800 text-stone-300 hover:text-white border border-stone-800 text-left transition cursor-pointer group"
                      >
                        <div className="text-[11px] font-bold text-white group-hover:text-orange-400 transition">HR Lead</div>
                        <div className="text-[10px] text-stone-500 truncate">hr@leavify.ai</div>
                      </button>
                      <button
                        type="button"
                        onClick={() => fillDemoAccount("employee@leavify.ai", "password123")}
                        className="p-2 rounded-xl bg-[#141210] hover:bg-stone-800 text-stone-300 hover:text-white border border-stone-800 text-left transition cursor-pointer group"
                      >
                        <div className="text-[11px] font-bold text-white group-hover:text-orange-400 transition">Employee</div>
                        <div className="text-[10px] text-stone-500 truncate">employee@...</div>
                      </button>
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-stone-300 mb-1.5">
                      Account Email
                    </label>
                    <div className="relative">
                      <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-stone-500" />
                      <input
                        type="email"
                        required
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="you@company.com"
                        className="w-full bg-[#1c1917] border border-stone-800 rounded-xl pl-10 pr-4 py-2.5 text-sm text-[#FAF8F5] placeholder-stone-500 focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500/30 transition"
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <label className="text-xs font-semibold text-stone-300">Password</label>
                      <button
                        type="button"
                        onClick={() => {
                          setShowForgotModal(true);
                          setForgotEmail(email);
                          setForgotError(null);
                          setForgotSuccess(null);
                        }}
                        className="text-xs text-orange-400 hover:underline cursor-pointer"
                      >
                        Forgot password?
                      </button>
                    </div>
                    <div className="relative">
                      <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-stone-500" />
                      <input
                        type="password"
                        required
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="••••••••"
                        className="w-full bg-[#1c1917] border border-stone-800 rounded-xl pl-10 pr-4 py-2.5 text-sm text-[#FAF8F5] placeholder-stone-500 focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500/30 transition"
                      />
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full py-3 bg-orange-600 hover:bg-orange-500 active:bg-orange-700 disabled:opacity-50 text-white font-semibold rounded-xl text-sm transition cursor-pointer shadow-sm flex items-center justify-center gap-2"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>Signing In…</span>
                      </>
                    ) : (
                      <>
                        <span>Enter Workspace</span>
                        <ArrowRight className="w-4 h-4" />
                      </>
                    )}
                  </button>
                </form>
              ) : (
                /* REGISTER ORGANIZATION TAB */
                <form onSubmit={handleRegisterSubmit} className="space-y-4">
                  <div>
                    <label className="block text-xs font-semibold text-stone-300 mb-1.5">
                      Company / Organization Name *
                    </label>
                    <div className="relative">
                      <Building2 className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-stone-500" />
                      <input
                        type="text"
                        required
                        value={regData.company_name}
                        onChange={(e) =>
                          setRegData({ ...regData, company_name: e.target.value })
                        }
                        placeholder="Acme Global Inc"
                        className="w-full bg-[#1c1917] border border-stone-800 rounded-xl pl-10 pr-4 py-2 text-sm text-[#FAF8F5] placeholder-stone-500 focus:outline-none focus:border-orange-500 transition"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-stone-300 mb-1.5">
                      Organization Official Email (Inbound Mailbox) *
                    </label>
                    <div className="flex gap-2">
                      <div className="relative flex-1">
                        <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-stone-500" />
                        <input
                          type="email"
                          required
                          value={regData.organization_email}
                          onChange={(e) =>
                            setRegData({ ...regData, organization_email: e.target.value })
                          }
                          placeholder="company@gmail.com"
                          className="w-full bg-[#1c1917] border border-stone-800 rounded-xl pl-10 pr-4 py-2 text-sm text-[#FAF8F5] placeholder-stone-500 focus:outline-none focus:border-orange-500 transition"
                        />
                      </div>
                      <button
                        type="button"
                        onClick={handleSendOtp}
                        disabled={sendingOtp || otpCooldown > 0}
                        className="px-4 py-2 bg-orange-600 hover:bg-orange-500 disabled:opacity-50 text-white rounded-xl text-xs font-semibold transition cursor-pointer shrink-0"
                      >
                        {sendingOtp ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : otpCooldown > 0 ? (
                          `${otpCooldown}s`
                        ) : (
                          "Send OTP"
                        )}
                      </button>
                    </div>
                  </div>

                  {/* OTP Verification Box */}
                  {otpSent && !otpVerified && (
                    <div className="p-3.5 rounded-xl bg-[#1c1917] border border-orange-500/30 space-y-2">
                      <label className="block text-xs font-semibold text-orange-400">
                        Enter 6-Digit Email Verification Code *
                      </label>
                      <div className="flex gap-2">
                        <input
                          type="text"
                          maxLength={6}
                          value={regData.otp}
                          onChange={(e) => setRegData({ ...regData, otp: e.target.value })}
                          placeholder="123456"
                          className="flex-1 bg-[#141210] border border-stone-800 rounded-lg px-3 py-1.5 text-center font-mono text-sm tracking-widest text-white focus:outline-none focus:border-orange-500"
                        />
                        <button
                          type="button"
                          onClick={handleVerifyOtp}
                          disabled={verifyingOtp || regData.otp.length !== 6}
                          className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold transition cursor-pointer"
                        >
                          {verifyingOtp ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : "Verify"}
                        </button>
                      </div>
                    </div>
                  )}

                  {otpVerified && (
                    <div className="flex items-center gap-2 p-2 rounded-lg bg-emerald-950/40 border border-emerald-500/30 text-emerald-400 text-xs">
                      <Check className="w-4 h-4" />
                      <span>Email address verified</span>
                    </div>
                  )}

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-stone-300 mb-1.5">
                        CEO First Name *
                      </label>
                      <input
                        type="text"
                        required
                        value={regData.ceo_first_name}
                        onChange={(e) =>
                          setRegData({ ...regData, ceo_first_name: e.target.value })
                        }
                        placeholder="Jane"
                        className="w-full bg-[#1c1917] border border-stone-800 rounded-xl px-3 py-2 text-sm text-[#FAF8F5] focus:outline-none focus:border-orange-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-stone-300 mb-1.5">
                        CEO Last Name *
                      </label>
                      <input
                        type="text"
                        required
                        value={regData.ceo_last_name}
                        onChange={(e) =>
                          setRegData({ ...regData, ceo_last_name: e.target.value })
                        }
                        placeholder="Doe"
                        className="w-full bg-[#1c1917] border border-stone-800 rounded-xl px-3 py-2 text-sm text-[#FAF8F5] focus:outline-none focus:border-orange-500"
                      />
                    </div>
                  </div>

                  {/* Corporate email preview */}
                  <div className="p-3 rounded-xl bg-[#1c1917] border border-stone-800 text-xs space-y-1">
                    <span className="text-stone-400">Primary CEO Work Login:</span>
                    <div className="font-mono text-orange-400 font-semibold">{previewEmail}</div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-stone-300 mb-1.5">
                      CEO Master Password (min 8 chars) *
                    </label>
                    <div className="relative">
                      <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-stone-500" />
                      <input
                        type="password"
                        required
                        minLength={8}
                        value={regData.password}
                        onChange={(e) => setRegData({ ...regData, password: e.target.value })}
                        placeholder="••••••••"
                        className="w-full bg-[#1c1917] border border-stone-800 rounded-xl pl-10 pr-4 py-2 text-sm text-[#FAF8F5] focus:outline-none focus:border-orange-500"
                      />
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={loading || !otpVerified}
                    className="w-full py-3 bg-orange-600 hover:bg-orange-500 active:bg-orange-700 disabled:opacity-50 text-white font-semibold rounded-xl text-sm transition cursor-pointer shadow-sm flex items-center justify-center gap-2"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>Provisioning Organization…</span>
                      </>
                    ) : (
                      <>
                        <span>Register Organization & Launch as CEO</span>
                        <ArrowRight className="w-4 h-4" />
                      </>
                    )}
                  </button>
                </form>
              )}
            </div>
          )}
        </div>

        {/* Problem vs Solution Bento Showcase */}
        <div className="space-y-8 pt-8">
          <div className="text-center space-y-2">
            <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Why Traditional Workforce Operations Fail
            </h2>
            <p className="text-sm sm:text-base text-stone-400 max-w-2xl mx-auto">
              How Leavify.ai bridges autonomous AI reasoning with zero-hallucination deterministic financial rails.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-stretch">
            {/* The Chaos Card */}
            <div className="md:col-span-6 p-6 sm:p-8 rounded-3xl bg-[#141210] border border-stone-800 space-y-4">
              <div className="flex items-center gap-2.5 text-rose-400">
                <div className="w-8 h-8 rounded-lg bg-rose-950/60 border border-rose-500/30 flex items-center justify-center">
                  <AlertTriangle className="w-4 h-4" />
                </div>
                <h3 className="text-lg font-bold text-white tracking-tight">The Old Way: Spreadsheet Chaos</h3>
              </div>
              <ul className="space-y-3 text-xs sm:text-sm text-stone-400">
                <li className="flex items-start gap-2">
                  <span className="text-rose-400 font-bold">✕</span>
                  <span>Employees chase managers across email, WhatsApp, and Slack for approval.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-rose-400 font-bold">✕</span>
                  <span>HR spends days manually recalculating unpaid leave salary deductions on spreadsheets.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-rose-400 font-bold">✕</span>
                  <span>Manual wire transfers cause payroll friction and delays for global teams.</span>
                </li>
              </ul>
            </div>

            {/* The Leavify Rails Card */}
            <div className="md:col-span-6 p-6 sm:p-8 rounded-3xl bg-[#141210] border border-orange-500/30 space-y-4">
              <div className="flex items-center gap-2.5 text-orange-400">
                <div className="w-8 h-8 rounded-lg bg-orange-950/60 border border-orange-500/30 flex items-center justify-center">
                  <Zap className="w-4 h-4 text-orange-400" />
                </div>
                <h3 className="text-lg font-bold text-white tracking-tight">The Leavify Way: Autonomous Rails</h3>
              </div>
              <ul className="space-y-3 text-xs sm:text-sm text-stone-300">
                <li className="flex items-start gap-2">
                  <Check className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span><strong>System 1 (Deterministic)</strong>: Exact mathematical deduction for unpaid leaves. Zero financial hallucinations.</span>
                </li>
                <li className="flex items-start gap-2">
                  <Check className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span><strong>System 2 (Conversational Copilot)</strong>: Natural language leave drafting & vector search across company handbooks.</span>
                </li>
                <li className="flex items-start gap-2">
                  <Check className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span><strong>PayPal Payouts REST API</strong>: Automated one-click batch disbursement with cryptographic idempotency keys.</span>
                </li>
              </ul>
            </div>
          </div>
        </div>

        {/* 5 Autonomous Specialized Agents Grid */}
        <div id="agents" className="space-y-8 pt-6">
          <div className="text-center space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-orange-950/40 border border-orange-500/20 text-orange-400 text-xs font-mono">
              <Bot className="w-3.5 h-3.5" />
              <span>Multi-Agent Architecture</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              5 Specialized Autonomous Agents Working In Concert
            </h2>
            <p className="text-sm sm:text-base text-stone-400 max-w-2xl mx-auto">
              Every workflow is decoupled into dedicated single-responsibility agents with dual-system guardrails.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
            {/* Agent 1: Supervisor */}
            <div className="md:col-span-7 p-6 sm:p-7 rounded-3xl bg-[#141210] border border-stone-800 space-y-3 relative overflow-hidden group hover:border-orange-500/40 transition">
              <div className="flex items-center justify-between">
                <div className="w-10 h-10 rounded-xl bg-orange-950/60 border border-orange-500/30 text-orange-400 flex items-center justify-center font-bold">
                  <Cpu className="w-5 h-5" />
                </div>
                <span className="text-[10px] font-mono uppercase tracking-wider text-orange-400 bg-orange-950/50 px-2.5 py-1 rounded-full border border-orange-500/20">
                  Agent 01 · Orchestrator
                </span>
              </div>
              <h3 className="text-base sm:text-lg font-bold text-white tracking-tight">
                Supervisor Agent (Orchestration & Dual-System Guardrail)
              </h3>
              <p className="text-xs sm:text-sm text-stone-400 leading-relaxed">
                Evaluates user intent and routes tasks. Enforces a strict separation between <strong>System 2 (conversational reasoning)</strong> and <strong>System 1 (deterministic financial math)</strong> so no generative model ever touches salary calculations.
              </p>
              <div className="pt-2 flex flex-wrap gap-2 text-[11px] font-mono text-stone-400">
                <span className="bg-[#1c1917] px-2.5 py-1 rounded-lg border border-stone-800">Intent Routing</span>
                <span className="bg-[#1c1917] px-2.5 py-1 rounded-lg border border-stone-800">Prompt Injection Guard</span>
                <span className="bg-[#1c1917] px-2.5 py-1 rounded-lg border border-stone-800">Zero Hallucination</span>
              </div>
            </div>

            {/* Agent 2: Inbound Email Worker */}
            <div className="md:col-span-5 p-6 sm:p-7 rounded-3xl bg-[#141210] border border-stone-800 space-y-3 relative overflow-hidden group hover:border-orange-500/40 transition">
              <div className="flex items-center justify-between">
                <div className="w-10 h-10 rounded-xl bg-amber-950/60 border border-amber-500/30 text-amber-400 flex items-center justify-center font-bold">
                  <Inbox className="w-5 h-5" />
                </div>
                <span className="text-[10px] font-mono uppercase tracking-wider text-amber-400 bg-amber-950/50 px-2.5 py-1 rounded-full border border-amber-500/20">
                  Agent 02 · Inbound
                </span>
              </div>
              <h3 className="text-base sm:text-lg font-bold text-white tracking-tight">
                Autonomous Inbound Mailbox Worker
              </h3>
              <p className="text-xs sm:text-sm text-stone-400 leading-relaxed">
                Background worker polling the company inbox every 60s. Authenticates sender against verified employee whitelists and files leave requests automatically.
              </p>
              <div className="pt-2 flex flex-wrap gap-2 text-[11px] font-mono text-stone-400">
                <span className="bg-[#1c1917] px-2.5 py-1 rounded-lg border border-stone-800">IMAP Polling</span>
                <span className="bg-[#1c1917] px-2.5 py-1 rounded-lg border border-stone-800">Whitelist Security</span>
              </div>
            </div>

            {/* Agent 3: Leave Intelligence */}
            <div className="md:col-span-4 p-6 sm:p-7 rounded-3xl bg-[#141210] border border-stone-800 space-y-3 relative overflow-hidden group hover:border-orange-500/40 transition">
              <div className="flex items-center justify-between">
                <div className="w-10 h-10 rounded-xl bg-emerald-950/60 border border-emerald-500/30 text-emerald-400 flex items-center justify-center font-bold">
                  <Calendar className="w-5 h-5" />
                </div>
                <span className="text-[10px] font-mono uppercase tracking-wider text-emerald-400 bg-emerald-950/50 px-2.5 py-1 rounded-full border border-emerald-500/20">
                  Agent 03
                </span>
              </div>
              <h3 className="text-base font-bold text-white tracking-tight">
                Leave Intelligence & Conflict Engine
              </h3>
              <p className="text-xs text-stone-400 leading-relaxed">
                Calculates remaining paid quotas, verifies multi-day bank holiday schedules, and detects team collision when critical roles overlap.
              </p>
            </div>

            {/* Agent 4: Loss-of-Pay Math */}
            <div className="md:col-span-4 p-6 sm:p-7 rounded-3xl bg-[#141210] border border-stone-800 space-y-3 relative overflow-hidden group hover:border-orange-500/40 transition">
              <div className="flex items-center justify-between">
                <div className="w-10 h-10 rounded-xl bg-cyan-950/60 border border-cyan-500/30 text-cyan-400 flex items-center justify-center font-bold">
                  <Layers className="w-5 h-5" />
                </div>
                <span className="text-[10px] font-mono uppercase tracking-wider text-cyan-400 bg-cyan-950/50 px-2.5 py-1 rounded-full border border-cyan-500/20">
                  Agent 04 · Math
                </span>
              </div>
              <h3 className="text-base font-bold text-white tracking-tight">
                Deterministic Loss-of-Pay (LOP) Rails
              </h3>
              <p className="text-xs text-stone-400 leading-relaxed">
                Computes daily wage baselines and pro-rata deductions for unpaid days. Deterministic Python execution with 0% chance of calculation drift.
              </p>
            </div>

            {/* Agent 5: PayPal Settlement */}
            <div className="md:col-span-4 p-6 sm:p-7 rounded-3xl bg-[#141210] border border-orange-500/30 space-y-3 relative overflow-hidden group hover:border-orange-500/60 transition">
              <div className="flex items-center justify-between">
                <div className="w-10 h-10 rounded-xl bg-orange-950/60 border border-orange-500/30 text-orange-400 flex items-center justify-center font-bold">
                  <CreditCard className="w-5 h-5" />
                </div>
                <span className="text-[10px] font-mono uppercase tracking-wider text-orange-400 bg-orange-950/50 px-2.5 py-1 rounded-full border border-orange-500/20">
                  Agent 05 · Rails
                </span>
              </div>
              <h3 className="text-base font-bold text-white tracking-tight">
                PayPal Payouts Settlement Engine
              </h3>
              <p className="text-xs text-stone-300 leading-relaxed">
                Connects directly to PayPal Payouts REST API. Executes global 1-click batch payouts with UUIDv4 cryptographic idempotency to prevent duplicate debits.
              </p>
            </div>
          </div>
        </div>

        {/* 3-Step Lifecycle Visual */}
        <div id="lifecycle" className="space-y-8 pt-6">
          <div className="text-center space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-stone-900 border border-stone-800 text-stone-400 text-xs font-mono">
              <Sparkles className="w-3.5 h-3.5 text-orange-400" />
              <span>End-to-End Automation</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              How a Leave Request Resolves in Under 2 Seconds
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="p-6 rounded-3xl bg-[#141210] border border-stone-800 space-y-3">
              <div className="w-8 h-8 rounded-lg bg-orange-600 text-white font-mono font-bold text-xs flex items-center justify-center">
                01
              </div>
              <h4 className="text-base font-bold text-white">Inbound Ingestion</h4>
              <p className="text-xs text-stone-400 leading-relaxed">
                Employee sends an email or asks the conversational assistant: <em>&ldquo;I need 3 days off next Tuesday for family travel.&rdquo;</em> The inbound parser extracts dates and reason.
              </p>
            </div>

            <div className="p-6 rounded-3xl bg-[#141210] border border-stone-800 space-y-3">
              <div className="w-8 h-8 rounded-lg bg-stone-800 text-stone-200 font-mono font-bold text-xs flex items-center justify-center">
                02
              </div>
              <h4 className="text-base font-bold text-white">Policy & Quota Audit</h4>
              <p className="text-xs text-stone-400 leading-relaxed">
                The agent checks remaining PTO, compares against department blackout dates, and automatically requests manager approval or auto-approves compliant leaves.
              </p>
            </div>

            <div className="p-6 rounded-3xl bg-[#141210] border border-stone-800 space-y-3">
              <div className="w-8 h-8 rounded-lg bg-emerald-600 text-white font-mono font-bold text-xs flex items-center justify-center">
                03
              </div>
              <h4 className="text-base font-bold text-white">Deterministic Payout</h4>
              <p className="text-xs text-stone-400 leading-relaxed">
                At payroll cutoff, unpaid leave deductions are calculated with exact math. HR reviews the batch and clicks once to disburse funds globally via PayPal.
              </p>
            </div>
          </div>
        </div>

        {/* Enterprise FAQ Accordion */}
        <div id="faq" className="space-y-8 pt-6 max-w-4xl mx-auto w-full">
          <div className="text-center space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-stone-900 border border-stone-800 text-stone-400 text-xs font-mono">
              <HelpCircle className="w-3.5 h-3.5 text-orange-400" />
              <span>Frequently Asked Questions</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Enterprise Architecture & FAQ
            </h2>
          </div>

          <div className="space-y-3">
            {[
              {
                q: "How does Leavify eliminate AI hallucinations on salary & financial calculations?",
                a: "Leavify enforces a strict dual-system architecture. Generative LLMs (System 2) only extract intent and summarize text. All mathematical computations—such as daily salary rate, pro-rata unpaid leave cuts, and PayPal batch amounts—are calculated by System 1 deterministic Python code with unit-tested math.",
              },
              {
                q: "How does the autonomous inbound email worker authenticate senders?",
                a: "The autonomous worker runs periodically in the background over IMAP. When an email arrives, it matches the sender's address against verified employee records. Unauthorized or spoofed emails are rejected immediately with no state change, preventing prompt injection or fraudulent leave submissions.",
              },
              {
                q: "How does PayPal batch payout integration prevent duplicate payouts?",
                a: "Each payroll run generates a cryptographically unique UUIDv4 idempotency key (header PayPal-Request-Id). Even if a network timeout occurs or the button is double-clicked, PayPal guarantees that payments are executed exactly once.",
              },
              {
                q: "Can organizations customize their own leave policies and company handbooks?",
                a: "Yes! Administrators can upload custom policy documents or create department-specific leave rules. Employees can ask natural-language questions in the chat assistant, and the system cites exact clauses from your company policy.",
              },
            ].map((item, idx) => (
              <div
                key={idx}
                className="rounded-2xl bg-[#141210] border border-stone-800 overflow-hidden transition"
              >
                <button
                  type="button"
                  onClick={() => setOpenFaqIndex(openFaqIndex === idx ? null : idx)}
                  className="w-full p-5 text-left flex items-center justify-between gap-4 cursor-pointer hover:bg-stone-900/40 transition"
                >
                  <span className="text-sm font-semibold text-stone-200">{item.q}</span>
                  {openFaqIndex === idx ? (
                    <ChevronUp className="w-4 h-4 text-orange-400 shrink-0" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-stone-500 shrink-0" />
                  )}
                </button>
                {openFaqIndex === idx && (
                  <div className="px-5 pb-5 pt-1 text-xs sm:text-sm text-stone-400 leading-relaxed border-t border-stone-800/60">
                    {item.a}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-stone-800/80 bg-[#0c0a09] py-8 text-xs text-stone-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="font-bold text-white">Leavify.ai</span>
            <span>• Autonomous Workforce Leave Intelligence & Payroll Settlement Platform</span>
          </div>
          <div className="flex items-center gap-4">
            <a href="https://developer.paypal.com" target="_blank" rel="noreferrer" className="hover:text-stone-300 transition">
              PayPal Developer Platform
            </a>
            <a href="/docs" target="_blank" rel="noreferrer" className="hover:text-stone-300 transition">
              API Docs
            </a>
          </div>
        </div>
      </footer>

      {/* Forgot Password Modal */}
      {showForgotModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-[#141210] border border-stone-800 rounded-3xl p-6 sm:p-7 space-y-5 shadow-2xl relative">
            <button
              onClick={() => setShowForgotModal(false)}
              className="absolute right-5 top-5 p-1 rounded-lg text-stone-400 hover:text-white hover:bg-stone-800 transition cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>

            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-orange-950/60 border border-orange-500/30 text-orange-400 flex items-center justify-center font-bold">
                <KeyRound className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white tracking-tight">Reset Account Password</h3>
                <p className="text-xs text-stone-400">Secure OTP verification</p>
              </div>
            </div>

            {forgotError && (
              <div className="p-3 rounded-xl bg-rose-950/50 border border-rose-500/30 text-rose-300 text-xs">
                {forgotError}
              </div>
            )}
            {forgotSuccess && (
              <div className="p-3 rounded-xl bg-emerald-950/50 border border-emerald-500/30 text-emerald-300 text-xs">
                {forgotSuccess}
              </div>
            )}

            {forgotStep === "request" ? (
              <form onSubmit={handleForgotRequestOtp} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-stone-300 mb-1.5">
                    Account Email Address
                  </label>
                  <input
                    type="email"
                    required
                    value={forgotEmail}
                    onChange={(e) => setForgotEmail(e.target.value)}
                    placeholder="you@company.com"
                    className="w-full bg-[#1c1917] border border-stone-800 rounded-xl px-3.5 py-2 text-sm text-[#FAF8F5] focus:outline-none focus:border-orange-500"
                  />
                </div>
                <button
                  type="submit"
                  disabled={forgotLoading}
                  className="w-full py-2.5 bg-orange-600 hover:bg-orange-500 active:bg-orange-700 disabled:opacity-50 text-white font-semibold rounded-xl text-sm transition cursor-pointer flex items-center justify-center gap-2"
                >
                  {forgotLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Send Password Reset Code"}
                </button>
              </form>
            ) : (
              <form onSubmit={handleForgotResetPassword} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-stone-300 mb-1.5">
                    6-Digit Verification Code
                  </label>
                  <input
                    type="text"
                    required
                    maxLength={6}
                    value={forgotOtp}
                    onChange={(e) => setForgotOtp(e.target.value)}
                    placeholder="123456"
                    className="w-full bg-[#1c1917] border border-stone-800 rounded-xl px-3.5 py-2 text-center font-mono text-sm tracking-widest text-[#FAF8F5] focus:outline-none focus:border-orange-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-stone-300 mb-1.5">
                    New Master Password (min 8 chars)
                  </label>
                  <input
                    type="password"
                    required
                    minLength={8}
                    value={forgotNewPassword}
                    onChange={(e) => setForgotNewPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full bg-[#1c1917] border border-stone-800 rounded-xl px-3.5 py-2 text-sm text-[#FAF8F5] focus:outline-none focus:border-orange-500"
                  />
                </div>
                <button
                  type="submit"
                  disabled={forgotLoading}
                  className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 disabled:opacity-50 text-white font-semibold rounded-xl text-sm transition cursor-pointer flex items-center justify-center gap-2"
                >
                  {forgotLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Confirm New Password"}
                </button>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
