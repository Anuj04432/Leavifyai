import { useState, useEffect, useRef, useMemo } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  Bell,
  LogOut,
  Calendar,
  Users,
  LayoutDashboard,
  CheckSquare,
  CreditCard,
  BookOpen,
  Loader2,
} from "lucide-react";
import { api } from "../../lib/api";
import { useAuthStore } from "../../store/authStore";

interface Notification {
  id: string;
  subject?: string;
  body?: string;
  processing_status: string;
  created_at: string;
  leave_request_id?: string;
}

export default function Navbar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout, updateUser } = useAuthStore();

  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [showNotifMenu, setShowNotifMenu] = useState(false);
  const [loadingNotifs, setLoadingNotifs] = useState(false);
  const notifRef = useRef<HTMLDivElement>(null);

  // Sync latest user profile with organization name from backend if missing
  useEffect(() => {
    if (!user?.company_name) {
      api
        .get("/auth/me")
        .then((res) => {
          if (res.data) {
            updateUser({ ...user, ...res.data });
          }
        })
        .catch(() => {});
    }
  }, [user?.company_name]);

  const displayOrgName = useMemo(() => {
    if (user?.company_name && user.company_name.trim()) {
      return user.company_name;
    }
    const domain =
      user?.company_domain || (user?.email?.includes("@") ? user.email.split("@")[1] : "");
    if (domain) {
      const cleanSlug = domain.split(".")[0];
      if (cleanSlug && cleanSlug !== "workforce" && cleanSlug !== "company") {
        return cleanSlug.charAt(0).toUpperCase() + cleanSlug.slice(1);
      }
    }
    return "Organization";
  }, [user?.company_name, user?.company_domain, user?.email]);

  const isCeo = user?.role === "ceo" || user?.role === "super_admin";

  const canAccessPayroll =
    isCeo ||
    user?.role === "ir_manager" ||
    user?.role === "finance_manager" ||
    user?.role === "hr" ||
    user?.role === "hr_manager" ||
    !!user?.permissions?.can_run_payroll ||
    !!user?.permissions?.can_handle_paypal;

  const canAccessEmployees =
    isCeo ||
    user?.role === "admin" ||
    user?.role === "hr" ||
    user?.role === "hr_manager" ||
    user?.role === "finance_manager" ||
    !!user?.permissions?.can_manage_roster;

  const canAccessApprovals =
    isCeo ||
    user?.role === "hr" ||
    user?.role === "hr_manager" ||
    user?.role === "manager" ||
    user?.role === "ir_manager" ||
    user?.role === "admin" ||
    !!user?.permissions?.can_approve_leaves;

  const canAccessPolicies =
    isCeo ||
    user?.role === "content_manager" ||
    user?.role === "admin" ||
    user?.role === "hr" ||
    user?.role === "hr_manager" ||
    !!user?.permissions?.can_manage_policies;

  const fetchNotifications = async () => {
    try {
      setLoadingNotifs(true);
      const res = await api.get("/notifications/?limit=10");
      setNotifications(res.data);
    } catch (err) {
      console.error("Failed to load notifications", err);
    } finally {
      setLoadingNotifs(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 20000);
    return () => clearInterval(interval);
  }, []);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setShowNotifMenu(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const markAsRead = async (id: string) => {
    try {
      await api.patch(`/notifications/${id}/read`);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, processing_status: "read" } : n))
      );
    } catch (err) {
      console.error("Failed to mark as read", err);
    }
  };

  const markAllAsRead = async () => {
    try {
      await api.post("/notifications/read-all");
      setNotifications((prev) =>
        prev.map((n) => ({ ...n, processing_status: "read" }))
      );
    } catch (err) {
      console.error("Failed to mark all read", err);
    }
  };

  const unreadCount = notifications.filter(
    (n) => n.processing_status === "unread"
  ).length;

  return (
    <header className="h-14 border-b border-slate-800 bg-slate-900 px-6 flex items-center justify-between sticky top-0 z-30 font-sans">
      {/* Brand & Primary Navigation */}
      <div className="flex items-center gap-6">
        <Link to="/dashboard" className="flex items-center gap-2.5 group">
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center font-black text-white text-sm shadow-sm group-hover:bg-indigo-500 transition">
            {displayOrgName.charAt(0).toUpperCase()}
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-1.5">
              <span className="font-bold text-white text-sm tracking-tight leading-tight max-w-[200px] sm:max-w-[280px] truncate">
                {displayOrgName}
              </span>
              <span className="px-1.5 py-0.2 rounded text-[9px] font-semibold tracking-wider uppercase bg-indigo-950/80 text-indigo-400 border border-indigo-800/60">
                Org
              </span>
            </div>
            <span className="text-[10px] text-slate-400 leading-none mt-0.5">
              WorkforceAI Workspace
            </span>
          </div>
        </Link>

        <nav className="hidden md:flex items-center gap-1 text-xs">
          <Link
            to="/dashboard"
            className={`px-3 py-1.5 rounded-lg transition flex items-center gap-1.5 ${
              location.pathname === "/dashboard"
                ? "text-white bg-slate-800 font-medium"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
            }`}
          >
            <LayoutDashboard className="w-3.5 h-3.5" />
            Dashboard
          </Link>

          {canAccessEmployees && (
            <Link
              to="/employees"
              className={`px-3 py-1.5 rounded-lg transition flex items-center gap-1.5 ${
                location.pathname === "/employees"
                  ? "text-white bg-slate-800 font-medium"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
              }`}
            >
              <Users className="w-3.5 h-3.5" />
              Employees
            </Link>
          )}

          <Link
            to="/leaves"
            className={`px-3 py-1.5 rounded-lg transition flex items-center gap-1.5 ${
              location.pathname === "/leaves"
                ? "text-white bg-slate-800 font-medium"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
            }`}
          >
            <Calendar className="w-3.5 h-3.5" />
            Leaves & Time-Off
          </Link>

          {canAccessApprovals && (
            <Link
              to="/approvals"
              className={`px-3 py-1.5 rounded-lg transition flex items-center gap-1.5 ${
                location.pathname === "/approvals"
                  ? "text-white bg-slate-800 font-medium"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
              }`}
            >
              <CheckSquare className="w-3.5 h-3.5" />
              Approval Cockpit
            </Link>
          )}

          {canAccessPayroll && (
            <Link
              to="/payroll"
              className={`px-3 py-1.5 rounded-lg transition flex items-center gap-1.5 ${
                location.pathname === "/payroll"
                  ? "text-white bg-slate-800 font-medium"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
              }`}
            >
              <CreditCard className="w-3.5 h-3.5" />
              Payroll
            </Link>
          )}

          {canAccessPolicies && (
            <Link
              to="/policies"
              className={`px-3 py-1.5 rounded-lg transition flex items-center gap-1.5 ${
                location.pathname === "/policies"
                  ? "text-white bg-slate-800 font-medium"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
              }`}
            >
              <BookOpen className="w-3.5 h-3.5" />
              Policies (OKF)
            </Link>
          )}
        </nav>
      </div>

      {/* User Actions & Notification Center */}
      <div className="flex items-center gap-3.5">
        {/* Notification Bell Menu */}
        <div className="relative" ref={notifRef}>
          <button
            onClick={() => {
              setShowNotifMenu(!showNotifMenu);
              if (!showNotifMenu) fetchNotifications();
            }}
            title="Notifications"
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition relative cursor-pointer"
          >
            <Bell className="w-4 h-4" />
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 w-4 h-4 bg-indigo-500 text-white rounded-full text-[9px] font-bold flex items-center justify-center animate-pulse">
                {unreadCount > 9 ? "9+" : unreadCount}
              </span>
            )}
          </button>

          {/* Dropdown Menu */}
          {showNotifMenu && (
            <div className="absolute right-0 mt-2 w-80 bg-slate-900 border border-slate-800 rounded-xl shadow-2xl p-3 space-y-3 z-50">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <span className="text-xs font-bold text-white flex items-center gap-1.5">
                  <Bell className="w-3.5 h-3.5 text-indigo-400" />
                  In-App Alerts
                </span>
                {unreadCount > 0 && (
                  <button
                    onClick={markAllAsRead}
                    className="text-[10px] text-indigo-400 hover:text-indigo-300 transition cursor-pointer"
                  >
                    Mark all read
                  </button>
                )}
              </div>

              {loadingNotifs && notifications.length === 0 ? (
                <div className="p-4 text-center">
                  <Loader2 className="w-4 h-4 animate-spin text-indigo-500 mx-auto" />
                </div>
              ) : notifications.length === 0 ? (
                <div className="p-4 text-center text-xs text-slate-500">
                  No notifications recorded.
                </div>
              ) : (
                <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                  {notifications.map((n) => (
                    <div
                      key={n.id}
                      onClick={() => markAsRead(n.id)}
                      className={`p-2.5 rounded-lg text-xs transition cursor-pointer ${
                        n.processing_status === "unread"
                          ? "bg-indigo-950/40 border border-indigo-500/30 text-white"
                          : "bg-slate-950/60 border border-slate-800/80 text-slate-300 hover:bg-slate-800/40"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-1">
                        <span className="font-semibold text-slate-200 text-[11px] truncate">
                          {n.subject || "Notification"}
                        </span>
                        {n.processing_status === "unread" && (
                          <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 shrink-0 mt-1" />
                        )}
                      </div>
                      <p className="text-[11px] text-slate-400 line-clamp-2 mt-0.5">
                        {n.body}
                      </p>
                      <span className="text-[9px] font-mono text-slate-500 block mt-1">
                        {new Date(n.created_at).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Profile Pill */}
        <div className="text-right hidden sm:block">
          <span className="text-xs font-medium text-slate-200 mr-2">{user?.email}</span>
          <span
            className={`px-2 py-0.5 rounded text-xs font-medium capitalize border ${
              user?.role === "ceo"
                ? "bg-amber-500/10 text-amber-300 border-amber-500/30 font-semibold"
                : user?.role === "finance_manager"
                ? "bg-blue-500/10 text-blue-300 border-blue-500/30"
                : "bg-indigo-500/10 text-indigo-400 border-indigo-500/20"
            }`}
          >
            {user?.role?.replace("_", " ")}
          </span>
        </div>

        {/* Sign Out Button */}
        <button
          onClick={handleLogout}
          title="Sign out"
          className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition cursor-pointer"
        >
          <LogOut className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
}
