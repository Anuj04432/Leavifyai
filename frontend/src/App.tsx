import { Routes, Route, Navigate } from "react-router-dom";
import LoginPage from "./pages/auth/LoginPage";
import EmployeeDirectory from "./pages/employees/EmployeeDirectory";
import LeaveManagement from "./pages/leaves/LeaveManagement";
import Dashboard from "./pages/dashboard/Dashboard";
import ApprovalCockpit from "./pages/hr/ApprovalCockpit";
import PayrollExecution from "./pages/payroll/PayrollExecution";
import ProtectedRoute from "./components/auth/ProtectedRoute";

export default function App() {
  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/login" element={<LoginPage />} />

      {/* Protected Routes */}
      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/employees" element={<EmployeeDirectory />} />
        <Route path="/leaves" element={<LeaveManagement />} />
        <Route path="/approvals" element={<ApprovalCockpit />} />
        <Route path="/payroll" element={<PayrollExecution />} />
      </Route>

      {/* 404 Catch-All */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
