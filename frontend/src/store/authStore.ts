import { create } from "zustand";

export interface UserProfile {
  id: string;
  email: string;
  role: "admin" | "hr" | "manager" | "employee";
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

export const useAuthStore = create<AuthState>((set) => {
  // Load initial tokens from localStorage if present
  const storedToken = localStorage.getItem("access_token");
  const storedRefreshToken = localStorage.getItem("refresh_token");
  const storedUser = localStorage.getItem("user_profile");

  return {
    token: storedToken,
    refreshToken: storedRefreshToken,
    user: storedUser ? JSON.parse(storedUser) : null,
    isAuthenticated: !!storedToken,

    setAuth: (token, refreshToken, user) => {
      localStorage.setItem("access_token", token);
      localStorage.setItem("refresh_token", refreshToken);
      localStorage.setItem("user_profile", JSON.stringify(user));
      set({ token, refreshToken, user, isAuthenticated: true });
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
