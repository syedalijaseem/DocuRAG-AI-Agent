/**
 * Authentication context for managing user state.
 */
import {
  createContext,
  useContext,
  useState,
  useEffect,
  type ReactNode,
} from "react";
import type { User } from "../types";
import * as api from "../api";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Check auth status on mount
  useEffect(() => {
    checkAuth();
  }, []);

  async function checkAuth() {
    setLoading(true);
    try {
      const { user } = await api.getCurrentUser();
      setUser(user);
      setError(null);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }

  async function login(email: string, password: string) {
    setError(null);
    try {
      const response = await api.login({ email, password });
      setUser(response.user);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Login failed";
      setError(message);
      throw err;
    }
  }

  async function register(email: string, password: string, name: string) {
    setError(null);
    try {
      await api.register({ email, password, name });
      // Don't auto-login - user needs to verify email
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Registration failed";
      setError(message);
      throw err;
    }
  }

  async function logout() {
    try {
      await api.logout();
    } catch {
      // Ignore logout errors
    } finally {
      setUser(null);
    }
  }

  async function refreshUser() {
    await checkAuth();
  }

  return (
    <AuthContext.Provider
      value={{ user, loading, error, login, register, logout, refreshUser }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
