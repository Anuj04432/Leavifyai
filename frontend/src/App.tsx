import { Routes, Route, Navigate } from "react-router-dom";
import LoginPage from "./pages/auth/LoginPage";
import EmployeeDirectory from "./pages/employees/EmployeeDirectory";
import LeaveManagement from "./pages/leaves/LeaveManagement";
import Dashboard from "./pages/dashboard/Dashboard";
import ApprovalCockpit from "./pages/hr/ApprovalCockpit";
import PayrollExecution from "./pages/payroll/PayrollExecution";
import PolicyKnowledge from "./pages/policies/PolicyKnowledge";
import CompanyChatPage from "./pages/chat/CompanyChatPage";
import ProtectedRoute from "./components/auth/ProtectedRoute";

export default function App() {
  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/login" element={<LoginPage />} />

      {/* Protected Routes: General (All authenticated employees) */}
      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
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
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
