import { useState, useEffect, useRef, useMemo } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  CalendarDays,
  MessageSquareQuote,
  CheckSquare,
  Users,
  BookOpen,
  CreditCard,
  LogOut,
  Menu,
  X,
  Bell,
  Shield,
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

export default function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout, updateUser } = useAuthStore();
  const [mobileOpen, setMobileOpen] = useState(false);

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

  const fetchNotifications = async () => {
    try {
      setLoadingNotifs(true);
      const res = await api.get("/notifications/?limit=10");
      setNotifications(res.data);
    } catch (err) {
      // quiet fail on background polling
    } finally {
      setLoadingNotifs(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 25000);
    return () => clearInterval(interval);
  }, []);

  // Close notification popover on outside click
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

  const role = user?.role || "employee";
  const isCeo = role === "ceo" || role === "super_admin";

  const canAccessPayroll =
    isCeo ||
    role === "ir_manager" ||
    role === "finance_manager" ||
    role === "hr" ||
    role === "hr_manager" ||
    !!user?.permissions?.can_run_payroll ||
    !!user?.permissions?.can_handle_paypal;

  const canAccessEmployees =
    isCeo ||
    role === "admin" ||
    role === "hr" ||
    role === "hr_manager" ||
    role === "finance_manager" ||
    !!user?.permissions?.can_manage_roster;

  const canAccessApprovals =
    isCeo ||
    role === "hr" ||
    role === "hr_manager" ||
    role === "manager" ||
    role === "ir_manager" ||
    role === "admin" ||
    !!user?.permissions?.can_approve_leaves;

  const canAccessPolicies =
    isCeo ||
    role === "content_manager" ||
    role === "admin" ||
    role === "hr" ||
    role === "hr_manager" ||
    !!user?.permissions?.can_manage_policies;

  const unreadNotifs = notifications.filter(
    (n) => n.processing_status === "pending" || n.processing_status === "unread"
  );

  const navItems = [
    {
      label: "Dashboard",
      path: "/dashboard",
      icon: LayoutDashboard,
      badge: null,
    },
    {
      label: "My Leaves",
      path: "/leaves",
      icon: CalendarDays,
      badge: null,
    },
    {
      label: "Talk with Company",
      path: "/company-chat",
      icon: MessageSquareQuote,
      badge: "Copilot",
      special: true,
    },
  ];

  const adminNavItems = [
    ...(canAccessApprovals
      ? [
          {
            label: "Approval Cockpit",
            path: "/approvals",
            icon: CheckSquare,
            badge: null,
          },
        ]
      : []),
    ...(canAccessEmployees
      ? [
          {
            label: "Employee Directory",
            path: "/employees",
            icon: Users,
            badge: null,
          },
        ]
      : []),
    ...(canAccessPolicies
      ? [
          {
            label: "Policy Knowledge",
            path: "/policies",
            icon: BookOpen,
            badge: null,
          },
        ]
      : []),
    ...(canAccessPayroll
      ? [
          {
            label: "Payroll Disbursal",
            path: "/payroll",
            icon: CreditCard,
            badge: "PayPal",
          },
        ]
      : []),
  ];

  return (
    <>
      {/* Mobile Top Header (h-14, sticky) */}
      <header className="md:hidden fixed top-0 left-0 right-0 h-14 bg-[#120f0d] border-b border-stone-800 z-40 px-4 flex items-center justify-between">
        <Link to="/dashboard" className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-orange-600 flex items-center justify-center font-bold text-white text-base shadow-sm">
            L
          </div>
          <span className="font-extrabold text-white text-base tracking-tight">Leavify.ai</span>
        </Link>

        <div className="flex items-center gap-2">
          {/* Notifications Trigger for Mobile */}
          <button
            onClick={() => setShowNotifMenu(!showNotifMenu)}
            className="p-2 rounded-lg text-stone-400 hover:text-white hover:bg-stone-800 relative cursor-pointer"
            aria-label="Notifications"
          >
            <Bell className="w-4 h-4" />
            {unreadNotifs.length > 0 && (
              <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-orange-500 animate-pulse" />
            )}
          </button>

          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            className="p-2 rounded-lg text-stone-400 hover:text-white hover:bg-stone-800 cursor-pointer"
            aria-label="Toggle navigation menu"
          >
            {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </header>

      {/* Mobile Backdrop */}
      {mobileOpen && (
        <div
          onClick={() => setMobileOpen(false)}
          className="md:hidden fixed inset-0 bg-black/60 z-40 backdrop-blur-xs"
        />
      )}

      {/* Vertical Sidebar: Fixed Left on Desktop, Slide-over on Mobile */}
      <aside
        className={`fixed top-0 bottom-0 left-0 w-64 bg-[#120f0d] border-r border-stone-800 z-50 flex flex-col justify-between transition-transform duration-200 ease-in-out md:translate-x-0 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Top Brand Section */}
        <div>
          <div className="p-4 border-b border-stone-800 flex items-center justify-between">
            <Link to="/dashboard" className="flex items-center gap-3 group">
              <div className="w-9 h-9 rounded-xl bg-orange-600 flex items-center justify-center font-bold text-white text-lg shadow-sm group-hover:scale-105 transition-transform">
                L
              </div>
              <div>
                <div className="font-extrabold text-white text-base tracking-tight leading-none">
                  Leavify.ai
                </div>
                <div className="text-[11px] text-stone-400 mt-1 flex items-center gap-1 font-mono">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                  <span className="truncate max-w-[120px]">{displayOrgName}</span>
                </div>
              </div>
            </Link>

            <button
              onClick={() => setMobileOpen(false)}
              className="md:hidden p-1.5 rounded-lg text-stone-400 hover:text-white hover:bg-stone-800"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Nav Links */}
          <nav className="p-3.5 space-y-6 overflow-y-auto max-h-[calc(100vh-210px)] no-scrollbar">
            {/* Core Workflows */}
            <div>
              <div className="px-3 mb-2 text-[11px] font-mono uppercase tracking-wider text-stone-500">
                Core Workflows
              </div>
              <div className="space-y-1">
                {navItems.map((item) => {
                  const isActive = location.pathname === item.path;
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.path}
                      to={item.path}
                      onClick={() => setMobileOpen(false)}
                      className={`group flex items-center justify-between px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                        isActive
                          ? item.special
                            ? "bg-orange-600 text-white shadow-md font-semibold"
                            : "bg-[#201c18] text-white border border-stone-800 shadow-sm font-semibold"
                          : item.special
                          ? "text-orange-400 hover:text-orange-300 hover:bg-orange-950/30"
                          : "text-stone-300 hover:text-white hover:bg-[#1a1714]"
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <Icon
                          className={`w-4 h-4 shrink-0 transition-transform group-hover:scale-105 ${
                            isActive
                              ? item.special
                                ? "text-white"
                                : "text-orange-400"
                              : item.special
                              ? "text-orange-400"
                              : "text-stone-400 group-hover:text-stone-200"
                          }`}
                        />
                        <span>{item.label}</span>
                      </div>
                      {item.badge && (
                        <span
                          className={`text-[10px] font-mono px-2 py-0.5 rounded-md ${
                            isActive && item.special
                              ? "bg-white/20 text-white font-bold"
                              : item.special
                              ? "bg-orange-950/60 text-orange-400 border border-orange-500/30 font-semibold"
                              : "bg-stone-800 text-stone-400 font-medium"
                          }`}
                        >
                          {item.badge}
                        </span>
                      )}
                    </Link>
                  );
                })}
              </div>
            </div>

            {/* Leadership & Admin Section */}
            {adminNavItems.length > 0 && (
              <div>
                <div className="px-3 mb-2 text-[11px] font-mono uppercase tracking-wider text-stone-500 flex items-center gap-1.5">
                  <Shield className="w-3 h-3 text-orange-400/80" />
                  <span>Management</span>
                </div>
                <div className="space-y-1">
                  {adminNavItems.map((item) => {
                    const isActive = location.pathname === item.path;
                    const Icon = item.icon;
                    return (
                      <Link
                        key={item.path}
                        to={item.path}
                        onClick={() => setMobileOpen(false)}
                        className={`group flex items-center justify-between px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                          isActive
                            ? "bg-[#201c18] text-white border border-stone-800 shadow-sm font-semibold"
                            : "text-stone-300 hover:text-white hover:bg-[#1a1714]"
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <Icon
                            className={`w-4 h-4 shrink-0 transition-transform group-hover:scale-105 ${
                              isActive ? "text-orange-400" : "text-stone-400 group-hover:text-stone-200"
                            }`}
                          />
                          <span>{item.label}</span>
                        </div>
                        {item.badge && (
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-stone-800 text-stone-400">
                            {item.badge}
                          </span>
                        )}
                      </Link>
                    );
                  })}
                </div>
              </div>
            )}
          </nav>
        </div>

        {/* Bottom Profile & Notifications Section */}
        <div className="p-3.5 border-t border-stone-800 bg-[#0e0c0a] space-y-2">
          {/* Notifications Trigger Button */}
          <div className="relative" ref={notifRef}>
            <button
              onClick={() => setShowNotifMenu(!showNotifMenu)}
              className="w-full flex items-center justify-between px-3 py-2 rounded-xl bg-[#161311] hover:bg-[#1e1a16] border border-stone-800/80 text-stone-300 hover:text-white text-xs transition cursor-pointer"
            >
              <div className="flex items-center gap-2">
                <Bell className="w-3.5 h-3.5 text-stone-400" />
                <span>Notifications</span>
              </div>
              {unreadNotifs.length > 0 ? (
                <span className="px-1.5 py-0.5 rounded-full bg-orange-600 text-white font-mono text-[10px] font-bold">
                  {unreadNotifs.length}
                </span>
              ) : (
                <span className="text-[10px] font-mono text-stone-500">0 unread</span>
              )}
            </button>

            {/* Notification Drawer Modal */}
            {showNotifMenu && (
              <div className="absolute bottom-full left-0 right-0 mb-2 bg-[#181512] border border-stone-800 rounded-2xl shadow-2xl overflow-hidden z-50">
                <div className="p-3 border-b border-stone-800 flex items-center justify-between">
                  <span className="text-xs font-semibold text-white">Notifications</span>
                  <span className="text-[10px] text-stone-400 font-mono">
                    {unreadNotifs.length} pending
                  </span>
                </div>
                <div className="max-h-60 overflow-y-auto divide-y divide-stone-800/60 no-scrollbar">
                  {loadingNotifs && (
                    <div className="p-4 text-center text-xs text-stone-400">
                      <Loader2 className="w-4 h-4 animate-spin mx-auto mb-1 text-orange-500" />
                      Loading notifications…
                    </div>
                  )}
                  {!loadingNotifs && notifications.length === 0 && (
                    <div className="p-4 text-center text-xs text-stone-500">
                      No notifications yet.
                    </div>
                  )}
                  {!loadingNotifs &&
                    notifications.map((n) => (
                      <div key={n.id} className="p-3 hover:bg-stone-900/50 transition">
                        <div className="text-xs font-medium text-stone-200 line-clamp-1">
                          {n.subject || "HR System Alert"}
                        </div>
                        <div className="text-[11px] text-stone-400 line-clamp-2 mt-0.5">
                          {n.body || "No details provided."}
                        </div>
                        <div className="text-[10px] font-mono text-stone-500 mt-1">
                          {new Date(n.created_at).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </div>
                      </div>
                    ))}
                </div>
              </div>
            )}
          </div>

          {/* User Details & Sign Out */}
          <div className="flex items-center justify-between gap-2 p-2 rounded-xl bg-[#161311] border border-stone-800/80">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-8 h-8 rounded-lg bg-orange-950/60 border border-orange-500/30 text-orange-400 flex items-center justify-center font-bold text-xs shrink-0">
                {(user?.email?.[0] || "U").toUpperCase()}
              </div>
              <div className="min-w-0">
                <div className="text-xs font-semibold text-white truncate leading-tight">
                  {user?.email}
                </div>
                <div className="text-[10px] text-orange-400 capitalize font-mono mt-0.5 truncate">
                  {role.replace("_", " ")}
                </div>
              </div>
            </div>

            <button
              onClick={handleLogout}
              title="Sign Out"
              className="p-1.5 text-stone-400 hover:text-rose-400 hover:bg-rose-950/30 rounded-lg transition-colors cursor-pointer shrink-0"
              aria-label="Sign Out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}
