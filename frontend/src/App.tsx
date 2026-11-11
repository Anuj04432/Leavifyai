import { lazy, Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import LandingPage from "./pages/public/LandingPage";
import ProtectedRoute from "./components/auth/ProtectedRoute";
import { Loader2 } from "lucide-react";

// Lazy-load dashboard and application routes to minimize initial bundle size and maximize speed
const EmployeeDirectory = lazy(() => import("./pages/employees/EmployeeDirectory"));
const LeaveManagement = lazy(() => import("./pages/leaves/LeaveManagement"));
const Dashboard = lazy(() => import("./pages/dashboard/Dashboard"));
const ApprovalCockpit = lazy(() => import("./pages/hr/ApprovalCockpit"));
const PayrollExecution = lazy(() => import("./pages/payroll/PayrollExecution"));
const PolicyKnowledge = lazy(() => import("./pages/policies/PolicyKnowledge"));
const CompanyChatPage = lazy(() => import("./pages/chat/CompanyChatPage"));

function RouteLoadingFallback() {
  return (
    <div className="min-h-screen bg-[#0c0a09] flex flex-col items-center justify-center gap-3 text-stone-400">
      <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
      <span className="text-xs font-mono tracking-wider uppercase">Loading Workspace…</span>
    </div>
  );
}

export default function App() {
  return (
    <Suspense fallback={<RouteLoadingFallback />}>
      <Routes>
        {/* Public Routes: Modern Landing Page with Integrated Auth Console */}
        <Route path="/" element={<LandingPage defaultTab="login" />} />
        <Route path="/login" element={<LandingPage defaultTab="login" />} />
        <Route path="/register" element={<LandingPage defaultTab="register" />} />

        {/* Protected Routes: General (All authenticated employees) */}
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/leaves" element={<LeaveManagement />} />
          <Route path="/company-chat" element={<CompanyChatPage />} />
        </Route>

        {/* Protected Routes: Personnel Directory & Management */}
        <Route
          element={
            <ProtectedRoute
              allowedRoles={["super_admin", "admin", "hr", "hr_manager", "ir_manager", "manager"]}
            />
          }
        >
          <Route path="/employees" element={<EmployeeDirectory />} />
          <Route path="/approvals" element={<ApprovalCockpit />} />
          <Route path="/policies" element={<PolicyKnowledge />} />
        </Route>

        {/* Protected Routes: Restricted Payroll & Payout Operations */}
        <Route
          element={
            <ProtectedRoute
              allowedRoles={["super_admin", "ir_manager", "hr", "hr_manager"]}
            />
          }
        >
          <Route path="/payroll" element={<PayrollExecution />} />
        </Route>

        {/* 404 Catch-All */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}
