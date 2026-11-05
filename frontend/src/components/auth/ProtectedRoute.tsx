import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "../../store/authStore";
import HRAssistantWidget from "../chat/HRAssistantWidget";

interface ProtectedRouteProps {
  allowedRoles?: Array<"admin" | "hr" | "manager" | "employee">;
}

export default function ProtectedRoute({ allowedRoles }: ProtectedRouteProps) {
  const { isAuthenticated, user } = useAuthStore();

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return (
      <div className="min-h-screen bg-slate-900 text-slate-100 flex items-center justify-center p-6">
        <div className="max-w-md w-full bg-slate-800/80 border border-rose-800/60 rounded-2xl p-8 text-center shadow-xl">
          <div className="w-12 h-12 rounded-full bg-rose-950 text-rose-400 mx-auto flex items-center justify-center mb-4">
            ⚠️
          </div>
          <h2 className="text-xl font-bold text-white mb-2">Access Restricted</h2>
          <p className="text-slate-400 text-sm mb-6">
            Your role (<strong className="text-indigo-400 uppercase">{user.role}</strong>) does not have permission to view this page. Required role: {allowedRoles.join(" or ")}.
          </p>
          <a
            href="/"
            className="inline-block bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm px-5 py-2.5 rounded-xl transition shadow"
          >
            Return to Dashboard
          </a>
        </div>
      </div>
    );
  }

  return (
    <>
      <Outlet />
      <HRAssistantWidget />
    </>
  );
}
