import { create } from "zustand";

export interface UserProfile {
  id: string;
  email: string;
  role:
    | "super_admin"
    | "admin"
    | "ir_manager"
    | "hr"
    | "hr_manager"
    | "manager"
    | "employee";
  company_id: string;
  employee_id?: string | null;
  is_active: boolean;
  created_at: string;
}

interface AuthState {
  token: string | null;
  refreshToken: string | null;
  user: UserProfile | null;
  isAuthenticated: boolean;
  setAuth: (token: string, refreshToken: string, user: UserProfile) => void;
  updateUser: (user: UserProfile) => void;
  logout: () => void;
}

const getInitialUser = (): UserProfile | null => {
  try {
    const stored = localStorage.getItem("user_profile");
    if (!stored || stored === "undefined" || stored === "null") return null;
    return JSON.parse(stored);
  } catch {
    localStorage.removeItem("user_profile");
    return null;
  }
};

export const useAuthStore = create<AuthState>((set) => {
  const initialUser = getInitialUser();
  const storedToken = initialUser ? localStorage.getItem("access_token") : null;
  const storedRefreshToken = initialUser ? localStorage.getItem("refresh_token") : null;

  return {
    token: storedToken,
    refreshToken: storedRefreshToken,
    user: initialUser,
    isAuthenticated: !!storedToken && !!initialUser,

    setAuth: (token, refreshToken, user) => {
      localStorage.setItem("access_token", token);
      localStorage.setItem("refresh_token", refreshToken);
      if (user) {
        localStorage.setItem("user_profile", JSON.stringify(user));
      }
      set({ token, refreshToken, user, isAuthenticated: !!token && !!user });
    },

    updateUser: (user) => {
      localStorage.setItem("user_profile", JSON.stringify(user));
      set({ user });
    },

    logout: () => {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("user_profile");
      set({ token: null, refreshToken: null, user: null, isAuthenticated: false });
    },
  };
});
