import { useEffect, useState } from "react";
import axios from "axios";
import { CheckCircle2, XCircle, Activity, Server, Database, ShieldCheck, ArrowRight } from "lucide-react";

interface HealthStatus {
  status: string;
  database: string;
  redis: string;
  environment: string;
}

export default function App() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const apiBase = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        setLoading(true);
        const res = await axios.get<HealthStatus>(`${apiBase}/health`);
        setHealth(res.data);
        setError(null);
      } catch (err: any) {
        setError(err.message || "Failed to reach backend API gateway");
      } finally {
        setLoading(false);
      }
    };

    fetchHealth();
    const interval = setInterval(fetchHealth, 10000);
    return () => clearInterval(interval);
  }, [apiBase]);

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col justify-between">
      {/* Top Navigation */}
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center font-bold text-xl text-white shadow-lg shadow-indigo-500/30">
            W
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight">WorkforceAI</h1>
            <p className="text-xs text-slate-400">Agentic Workforce Management & Payroll Automation</p>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noreferrer"
            className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded-lg border border-slate-700 transition"
          >
            FastAPI OpenAPI Docs ↗
          </a>
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-900/60 text-indigo-300 border border-indigo-700/50">
            Phase 1: Foundation Active
          </span>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-5xl mx-auto px-6 py-12 flex-1 w-full flex flex-col items-center justify-center">
        <div className="text-center max-w-2xl mb-10">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-slate-800/80 border border-slate-700 text-indigo-400 text-xs font-semibold uppercase tracking-wider mb-4">
            <Activity className="w-3.5 h-3.5" />
            <span>Infrastructure Health Telemetry</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white mb-3">
            System Foundation Initialized
          </h2>
          <p className="text-slate-400 text-sm sm:text-base">
            WorkforceAI containerized foundation is live. All 18 relational entities, PostgreSQL with pgvector, and FastAPI services are operational.
          </p>
        </div>

        {/* Telemetry Status Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full max-w-3xl mb-10">
          {/* API Gateway */}
          <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-5 flex items-start space-x-4">
            <div className="p-2.5 rounded-lg bg-indigo-950/80 text-indigo-400 border border-indigo-800/40">
              <Server className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs text-slate-400 font-medium">FastAPI Gateway</p>
              <div className="flex items-center space-x-1.5 mt-1">
                {loading ? (
                  <span className="text-sm text-slate-400">Checking...</span>
                ) : !error ? (
                  <>
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <span className="text-sm font-semibold text-emerald-300">Operational</span>
                  </>
                ) : (
                  <>
                    <XCircle className="w-4 h-4 text-rose-400" />
                    <span className="text-sm font-semibold text-rose-300">Offline</span>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* PostgreSQL */}
          <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-5 flex items-start space-x-4">
            <div className="p-2.5 rounded-lg bg-emerald-950/80 text-emerald-400 border border-emerald-800/40">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs text-slate-400 font-medium">PostgreSQL 16 (pgvector)</p>
              <div className="flex items-center space-x-1.5 mt-1">
                {health?.database === "connected" ? (
                  <>
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <span className="text-sm font-semibold text-emerald-300">Connected</span>
                  </>
                ) : (
                  <>
                    <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span>
                    <span className="text-sm font-semibold text-amber-300">Standby (Docker)</span>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Redis Cache */}
          <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-5 flex items-start space-x-4">
            <div className="p-2.5 rounded-lg bg-amber-950/80 text-amber-400 border border-amber-800/40">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs text-slate-400 font-medium">Redis 7 State Cache</p>
              <div className="flex items-center space-x-1.5 mt-1">
                {health?.redis === "connected" ? (
                  <>
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <span className="text-sm font-semibold text-emerald-300">Connected</span>
                  </>
                ) : (
                  <>
                    <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span>
                    <span className="text-sm font-semibold text-amber-300">Standby (Docker)</span>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Phase Transition Call to Action */}
        <div className="w-full max-w-3xl bg-indigo-950/30 border border-indigo-800/40 rounded-2xl p-6 text-center">
          <h3 className="text-base font-bold text-indigo-200 mb-1">Ready for Phase 2: Authentication & Employee Roster</h3>
          <p className="text-slate-400 text-xs sm:text-sm mb-4">
            JWT session engine, RBAC permission guards, employee directory CRUD, and bulk CSV ingestion.
          </p>
          <div className="inline-flex items-center space-x-2 text-xs font-semibold text-indigo-400 bg-indigo-900/40 px-4 py-2 rounded-lg border border-indigo-700/50">
            <span>Next Milestone: Auth & Roster</span>
            <ArrowRight className="w-4 h-4" />
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 px-6 py-4 text-center text-xs text-slate-500">
        WorkforceAI Architecture • PayPal AI Hackathon 2026 • Target Deadline: Nov 12, 2026
      </footer>
    </div>
  );
}
