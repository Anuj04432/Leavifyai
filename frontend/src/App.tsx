import { Routes, Route, Navigate } from "react-router-dom";
import LoginPage from "./pages/auth/LoginPage";
import EmployeeDirectory from "./pages/employees/EmployeeDirectory";
import LeaveManagement from "./pages/leaves/LeaveManagement";
import ProtectedRoute from "./components/auth/ProtectedRoute";

export default function App() {
  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/login" element={<LoginPage />} />

      {/* Protected Routes */}
      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<Navigate to="/employees" replace />} />
        <Route path="/employees" element={<EmployeeDirectory />} />
        <Route path="/leaves" element={<LeaveManagement />} />
      </Route>

      {/* 404 Catch-All */}
      <Route path="*" element={<Navigate to="/employees" replace />} />
    </Routes>
  );
}
