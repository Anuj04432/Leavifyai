import { Navigate, Outlet } from "react-router-dom";
import { ShieldAlert } from "lucide-react";
import { useAuthStore } from "../../store/authStore";
import Sidebar from "../layout/Sidebar";
import HRAssistantWidget from "../chat/HRAssistantWidget";

interface ProtectedRouteProps {
  allowedRoles?: Array<
    | "ceo"
    | "super_admin"
    | "admin"
    | "ir_manager"
    | "finance_manager"
    | "hr"
    | "hr_manager"
    | "content_manager"
    | "manager"
    | "employee"
  >;
}

export default function ProtectedRoute({ allowedRoles }: ProtectedRouteProps) {
  const { isAuthenticated, user } = useAuthStore();

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />;
  }

  // CEO and Super Admin have universal authorization across all platform routes
  if (
    allowedRoles &&
    user.role !== "ceo" &&
    user.role !== "super_admin" &&
    !allowedRoles.includes(user.role)
  ) {
    return (
      <div className="min-h-screen bg-[#0c0a09] text-stone-100 flex items-center justify-center p-6 font-sans">
        <div className="max-w-md w-full bg-[#141210] border border-rose-900/40 rounded-2xl p-8 text-center shadow-xl">
          <div className="w-12 h-12 rounded-full bg-rose-950/60 border border-rose-800/40 text-rose-400 mx-auto flex items-center justify-center mb-4">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <h2 className="text-xl font-bold text-white mb-2">Access Restricted</h2>
          <p className="text-stone-400 text-sm mb-6 leading-relaxed">
            Your role (<strong className="text-orange-400 font-semibold capitalize">{user.role.replace("_", " ")}</strong>) does not have permission to view this page. Required role: {allowedRoles.join(" or ")}.
          </p>
          <a
            href="/dashboard"
            className="inline-block bg-orange-600 hover:bg-orange-500 text-white font-medium text-sm px-5 py-2.5 rounded-xl transition shadow cursor-pointer"
          >
            Return to Dashboard
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0c0a09] text-stone-100 font-sans antialiased">
      <Sidebar />
      <div className="md:pl-64 pt-14 md:pt-0 min-h-screen flex flex-col">
        <Outlet />
      </div>
      <HRAssistantWidget />
    </div>
  );
}
