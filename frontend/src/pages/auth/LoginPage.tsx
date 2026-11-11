import { useState, useEffect, FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import {
  ShieldCheck,
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

  // OTP resend cooldown timer
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
      setSuccessMsg(`Verification code sent to ${regData.organization_email}! Please check your Gmail inbox (and spam folder).`);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Failed to send verification code.");
    } finally {
      setSendingOtp(false);
    }
  };

  const handleVerifyOtp = async () => {
    if (!regData.otp || regData.otp.trim().length !== 6) {
      setError("Please enter the 6-digit code received in your Gmail.");
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

  // Live corporate email preview computation based on organization name
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
      setError("You must verify your organization Gmail address with the 6-digit code before registering.");
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
      setForgotError(typeof detail === "string" ? detail : "Failed to reset password. Please check your verification code.");
    } finally {
      setForgotLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0c0a09] text-stone-100 flex font-sans antialiased">
      {/* Left Architecture & Value Messaging Panel */}
      <div className="hidden lg:flex lg:w-5/12 bg-[#141210] border-r border-stone-800 flex-col justify-between p-12 relative overflow-hidden">
        {/* Subtle grid texture */}
        <div className="absolute inset-0 pointer-events-none [background-image:radial-gradient(var(--surface-grid)_1px,transparent_1px)] [background-size:16px_16px]" />

        <div>
          {/* Logo & Product Identity */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-orange-600 flex items-center justify-center font-bold text-xl text-white shadow-sm">
              L
            </div>
            <div>
              <span className="font-extrabold text-[#FFFDF8] text-xl tracking-tight block">
                Leavify.ai
              </span>
              <span className="text-xs font-medium text-stone-400 block -mt-0.5">
                Autonomous Leave & Workforce OS
              </span>
            </div>
          </div>

          {/* Value Prop Headline */}
          <div className="mt-14 space-y-4">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-orange-950/60 border border-orange-500/30 text-orange-400 text-xs font-mono font-medium">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              Enterprise Platform Live
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight text-[#FFFDF8] leading-tight">
              Autonomous leave intelligence & effortless workforce operations.
            </h1>
            <p className="text-sm text-stone-400 leading-relaxed">
              Empower high-performance teams with instant policy answers, deterministic quota verification, one-click approvals, and automated global settlements.
            </p>
          </div>
        </div>

        {/* Enterprise Value Cards */}
        <div className="space-y-4 pt-8 border-t border-stone-800/80">
          <div className="flex items-start gap-3.5">
            <div className="w-8 h-8 rounded-xl bg-[#1c1917] border border-stone-800 flex items-center justify-center shrink-0 text-orange-400">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <div>
              <div className="text-sm font-semibold text-white">Deterministic Policy Verification</div>
              <div className="text-xs text-stone-400 leading-normal mt-0.5">
                Instant qualification and conflict checking against organizational handbooks with zero quota overages.
              </div>
            </div>
          </div>

          <div className="flex items-start gap-3.5">
            <div className="w-8 h-8 rounded-xl bg-[#1c1917] border border-stone-800 flex items-center justify-center shrink-0 text-orange-400">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <div className="text-sm font-semibold text-white">Talk with Company Copilot</div>
              <div className="text-xs text-stone-400 leading-normal mt-0.5">
                Conversational leave staging, policy inquiries, and instant time-off drafts in plain English.
              </div>
            </div>
          </div>

          <div className="flex items-start gap-3.5">
            <div className="w-8 h-8 rounded-xl bg-[#1c1917] border border-stone-800 flex items-center justify-center shrink-0 text-orange-400">
              <CreditCard className="w-4 h-4" />
            </div>
            <div>
              <div className="text-sm font-semibold text-white">PayPal Automated Disbursements</div>
              <div className="text-xs text-stone-400 leading-normal mt-0.5">
                Direct cross-border settlement rails for monthly payroll and proration adjustments.
              </div>
            </div>
          </div>
        </div>

        {/* Footer Meta */}
        <div className="text-xs text-stone-500 tracking-tight pt-4 font-mono">
          Leavify.ai Enterprise Cloud · Multi-Tenant Architecture
        </div>
      </div>

      {/* Right Form Viewport */}
      <div className="flex-1 flex items-center justify-center p-6 sm:p-12 overflow-y-auto">
        <div className="w-full max-w-md space-y-6">
          {/* Mobile Header */}
          <div className="flex items-center gap-3 lg:hidden">
            <div className="w-9 h-9 rounded-xl bg-orange-600 flex items-center justify-center font-bold text-white text-lg">
              L
            </div>
            <span className="font-extrabold text-[#FFFDF8] text-lg tracking-tight">
              Leavify.ai
            </span>
          </div>

          {/* Heading */}
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-[#FFFDF8]">
              {activeTab === "login" ? "Sign in to your workspace" : "Register your Organization"}
            </h2>
            <p className="text-sm text-stone-400 mt-1">
              {activeTab === "login"
                ? "Enter your credentials to access your leave and payroll copilot."
                : "Create a verified company workspace and launch with automated leave rails."}
            </p>
          </div>

          {/* Segmented Mode Selector */}
          <div className="p-1 rounded-xl bg-[#141210] border border-stone-800 grid grid-cols-2 gap-1 text-sm">
            <button
              type="button"
              onClick={() => {
                setActiveTab("login");
                setError(null);
                setSuccessMsg(null);
              }}
              className={`py-2 rounded-lg font-medium transition cursor-pointer ${
                activeTab === "login"
                  ? "bg-[#201c18] text-[#FFFDF8] border border-stone-700 font-semibold shadow-sm"
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
              className={`py-2 rounded-lg font-medium transition cursor-pointer ${
                activeTab === "register"
                  ? "bg-[#201c18] text-[#FFFDF8] border border-stone-700 font-semibold shadow-sm"
                  : "text-stone-400 hover:text-stone-200"
              }`}
            >
              Register Company
            </button>
          </div>

          {/* Feedback Alerts */}
          {error && (
            <div className="p-3.5 rounded-xl bg-rose-950/40 border border-rose-500/30 text-rose-300 text-xs sm:text-sm flex items-start gap-2.5">
              <span className="w-1.5 h-1.5 rounded-full bg-rose-400 mt-2 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {successMsg && (
            <div className="p-3.5 rounded-xl bg-emerald-950/40 border border-emerald-500/30 text-emerald-300 text-xs sm:text-sm flex items-start gap-2.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
              <span>{successMsg}</span>
            </div>
          )}

          {/* SIGN IN FORM */}
          {activeTab === "login" ? (
            <form onSubmit={handleLoginSubmit} className="space-y-4">
              <div>
                <label className="block text-xs sm:text-sm font-medium text-stone-300 mb-1.5">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-stone-500 absolute left-3.5 top-3.5" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="name@company.com"
                    className="w-full bg-[#141210] border border-stone-800 focus:border-orange-500 focus:ring-1 focus:ring-orange-500/30 rounded-xl pl-10 pr-4 py-2.5 text-sm text-[#FFFDF8] placeholder-stone-500 outline-none transition"
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs sm:text-sm font-medium text-stone-300">
                    Password
                  </label>
                  <button
                    type="button"
                    onClick={() => {
                      setForgotEmail(email);
                      setForgotError(null);
                      setForgotSuccess(null);
                      setForgotStep("request");
                      setShowForgotModal(true);
                    }}
                    className="text-xs text-orange-400 hover:text-orange-300 font-medium transition cursor-pointer"
                  >
                    Forgot password?
                  </button>
                </div>
                <div className="relative">
                  <Lock className="w-4 h-4 text-stone-500 absolute left-3.5 top-3.5" />
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full bg-[#141210] border border-stone-800 focus:border-orange-500 focus:ring-1 focus:ring-orange-500/30 rounded-xl pl-10 pr-4 py-2.5 text-sm text-[#FFFDF8] placeholder-stone-500 outline-none transition"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-orange-600 hover:bg-orange-500 active:bg-orange-700 active:scale-[0.99] disabled:opacity-50 text-white font-semibold text-sm py-3 rounded-xl transition flex items-center justify-center gap-2 cursor-pointer shadow-md"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Signing in…</span>
                  </>
                ) : (
                  <>
                    <span>Sign In to Leavify</span>
                    <ArrowRight className="w-4 h-4 text-white" />
                  </>
                )}
              </button>
            </form>
          ) : (
            /* REGISTER COMPANY FORM */
            <form onSubmit={handleRegisterSubmit} className="space-y-3.5">
              <div>
                <label className="block text-xs sm:text-sm font-medium text-stone-300 mb-1">
                  Company / Organization Name *
                </label>
                <div className="relative">
                  <Building2 className="w-4 h-4 text-stone-500 absolute left-3.5 top-3" />
                  <input
                    type="text"
                    required
                    value={regData.company_name}
                    onChange={(e) =>
                      setRegData({ ...regData, company_name: e.target.value })
                    }
                    placeholder="Acme Global Inc"
                    className="w-full bg-[#141210] border border-stone-800 focus:border-orange-500 rounded-xl pl-10 pr-4 py-2 text-sm text-stone-100 placeholder-stone-600 outline-none transition"
                  />
                </div>
              </div>

              {/* Organization Gmail Address with OTP */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs sm:text-sm font-medium text-stone-300">
                    Organization Official Gmail (Inbound Mailbox) *
                  </label>
                  {otpVerified && (
                    <span className="flex items-center gap-1 text-xs text-emerald-400 font-semibold">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Verified
                    </span>
                  )}
                </div>
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <Mail className="w-4 h-4 text-stone-500 absolute left-3.5 top-3" />
                    <input
                      type="email"
                      required
                      value={regData.organization_email}
                      disabled={otpVerified}
                      onChange={(e) =>
                        setRegData({ ...regData, organization_email: e.target.value })
                      }
                      placeholder="e.g. company.leaves@gmail.com"
                      className="w-full bg-[#141210] border border-stone-800 focus:border-orange-500 disabled:opacity-75 rounded-xl pl-10 pr-4 py-2 text-sm text-stone-100 placeholder-stone-600 outline-none transition"
                    />
                  </div>
                  {!otpVerified && (
                    <button
                      type="button"
                      onClick={handleSendOtp}
                      disabled={sendingOtp || otpCooldown > 0}
                      className="px-4 py-2 bg-orange-600 hover:bg-orange-500 disabled:bg-stone-800 disabled:text-stone-500 text-white rounded-xl text-xs font-semibold cursor-pointer transition flex items-center gap-1.5 shrink-0"
                    >
                      {sendingOtp ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : otpCooldown > 0 ? (
                        <span>{otpCooldown}s</span>
                      ) : (
                        <span>{otpSent ? "Resend" : "Send OTP"}</span>
                      )}
                    </button>
                  )}
                </div>
                <p className="text-[11px] text-stone-500 mt-1">
                  We'll send a 6-digit verification code to confirm ownership of this Gmail address.
                </p>
              </div>

              {/* 6-Digit OTP */}
              {(otpSent || regData.otp) && !otpVerified && (
                <div className="p-3.5 bg-[#181512] border border-orange-500/40 rounded-xl space-y-2">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-medium text-orange-300">
                      Enter 6-Digit Verification Code
                    </label>
                    <span className="text-[11px] text-stone-400">Valid for 10 minutes</span>
                  </div>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      maxLength={6}
                      value={regData.otp}
                      onChange={(e) =>
                        setRegData({
                          ...regData,
                          otp: e.target.value.replace(/[^0-9]/g, ""),
                        })
                      }
                      placeholder="123456"
                      className="flex-1 bg-[#0c0a09] border border-stone-800 focus:border-orange-500 rounded-lg px-3 py-1.5 text-center font-mono text-base tracking-[6px] text-white outline-none"
                    />
                    <button
                      type="button"
                      onClick={handleVerifyOtp}
                      disabled={verifyingOtp || regData.otp.length !== 6}
                      className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold cursor-pointer transition flex items-center gap-1"
                    >
                      {verifyingOtp && <Loader2 className="w-3 h-3 animate-spin" />}
                      Verify
                    </button>
                  </div>
                </div>
              )}

              {/* CEO Names */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-stone-300 mb-1">
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
                    className="w-full bg-[#141210] border border-stone-800 focus:border-orange-500 rounded-xl px-3 py-2 text-sm text-stone-100 placeholder-stone-600 outline-none transition"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-stone-300 mb-1">
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
                    className="w-full bg-[#141210] border border-stone-800 focus:border-orange-500 rounded-xl px-3 py-2 text-sm text-stone-100 placeholder-stone-600 outline-none transition"
                  />
                </div>
              </div>

              <div className="p-2.5 rounded-xl bg-[#1c1917] border border-stone-800 text-xs text-stone-400">
                <span className="text-stone-500 block text-[11px]">Primary CEO Work Email:</span>
                <span className="font-mono text-orange-400">{previewEmail}</span>
              </div>

              <div>
                <label className="block text-xs font-medium text-stone-300 mb-1">
                  CEO Master Password (min 8 characters) *
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-stone-500 absolute left-3.5 top-3" />
                  <input
                    type="password"
                    required
                    minLength={8}
                    value={regData.password}
                    onChange={(e) =>
                      setRegData({ ...regData, password: e.target.value })
                    }
                    placeholder="••••••••"
                    className="w-full bg-[#141210] border border-stone-800 focus:border-orange-500 rounded-xl pl-10 pr-4 py-2 text-sm text-stone-100 placeholder-stone-600 outline-none transition"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-orange-600 hover:bg-orange-500 active:bg-orange-700 disabled:opacity-50 text-white font-semibold text-sm py-3 rounded-xl transition flex items-center justify-center gap-2 cursor-pointer shadow-md mt-3"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Registering Organization…</span>
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
      </div>

      {/* FORGOT PASSWORD MODAL */}
      {showForgotModal && (
        <div className="fixed inset-0 z-50 bg-[#0c0a09]/90 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#141210] border border-stone-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-stone-800">
              <h2 className="text-base font-bold text-[#FFFDF8] flex items-center gap-2">
                <KeyRound className="w-4 h-4 text-orange-400" />
                Reset Password
              </h2>
              <button
                onClick={() => setShowForgotModal(false)}
                className="text-stone-400 hover:text-white p-1 rounded-lg"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {forgotError && (
              <div className="p-3 bg-rose-950/40 border border-rose-500/30 rounded-xl text-xs text-rose-300">
                {forgotError}
              </div>
            )}

            {forgotSuccess && (
              <div className="p-3 bg-emerald-950/40 border border-emerald-500/30 rounded-xl text-xs text-emerald-300">
                {forgotSuccess}
              </div>
            )}

            {forgotStep === "request" ? (
              <form onSubmit={handleForgotRequestOtp} className="space-y-4">
                <p className="text-xs text-stone-400 leading-relaxed">
                  Enter your registered account email. We'll send a 6-digit verification code to reset your password.
                </p>
                <div>
                  <label className="block text-xs font-medium text-stone-300 mb-1">
                    Account Email Address
                  </label>
                  <input
                    type="email"
                    required
                    value={forgotEmail}
                    onChange={(e) => setForgotEmail(e.target.value)}
                    placeholder="name@company.com"
                    className="w-full bg-[#1c1917] border border-stone-800 focus:border-orange-500 rounded-xl px-3.5 py-2.5 text-sm text-stone-100 outline-none transition"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowForgotModal(false)}
                    className="px-4 py-2 bg-stone-900 hover:bg-stone-800 text-stone-300 rounded-xl text-xs font-medium cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={forgotLoading || !forgotEmail}
                    className="px-5 py-2.5 bg-orange-600 hover:bg-orange-500 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer disabled:opacity-50"
                  >
                    {forgotLoading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                    Send Reset Code
                  </button>
                </div>
              </form>
            ) : (
              <form onSubmit={handleForgotResetPassword} className="space-y-4">
                <p className="text-xs text-stone-400 leading-relaxed">
                  Enter the 6-digit verification code sent to <strong className="text-stone-200">{forgotEmail}</strong> and choose a new password.
                </p>

                <div>
                  <label className="block text-xs font-medium text-stone-300 mb-1">
                    6-Digit Verification Code
                  </label>
                  <input
                    type="text"
                    maxLength={6}
                    required
                    value={forgotOtp}
                    onChange={(e) => setForgotOtp(e.target.value.replace(/[^0-9]/g, ""))}
                    placeholder="123456"
                    className="w-full bg-[#1c1917] border border-stone-800 focus:border-orange-500 rounded-xl px-3 py-2 text-center font-mono text-base tracking-[6px] text-white outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-stone-300 mb-1">
                    New Password (min 8 characters)
                  </label>
                  <input
                    type="password"
                    required
                    minLength={8}
                    value={forgotNewPassword}
                    onChange={(e) => setForgotNewPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full bg-[#1c1917] border border-stone-800 focus:border-orange-500 rounded-xl px-3.5 py-2.5 text-sm text-stone-100 outline-none transition"
                  />
                </div>

                <div className="flex justify-between items-center gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setForgotStep("request")}
                    className="text-xs text-stone-400 hover:text-stone-200"
                  >
                    ← Change Email
                  </button>
                  <button
                    type="submit"
                    disabled={forgotLoading || forgotOtp.length !== 6 || forgotNewPassword.length < 8}
                    className="px-5 py-2.5 bg-orange-600 hover:bg-orange-500 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer disabled:opacity-50"
                  >
                    {forgotLoading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                    Reset Password & Sign In
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
