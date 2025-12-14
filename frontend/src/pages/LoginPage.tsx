/**
 * Login page component - Claude/ChatGPT inspired design with Tailwind CSS.
 */
import { useState, type FormEvent } from "react";
import { useAuth } from "../context/AuthContext";
import logo from "../assets/logo.png";

interface LoginPageProps {
  onSwitchToRegister: () => void;
  onForgotPassword: () => void;
  onSuccess: () => void;
}

export function LoginPage({
  onSwitchToRegister,
  onForgotPassword,
  onSuccess,
}: LoginPageProps) {
  const { login, error: authError } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await login(email, password);
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-neutral-100 dark:bg-[#242424] transition-colors">
      <div className="w-full max-w-md px-6">
        {/* Logo/Brand */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-xl bg-gradient-to-br from-[#0d9488] to-[#0f766e] mb-4">
            <img src={logo} alt="Querious" className="w-10 h-10" />
          </div>
          <h1 className="text-2xl font-semibold text-[#1a1a1a] dark:text-[#ececec]">
            Welcome back
          </h1>
          <p className="text-[#a3a3a3] dark:text-[#a0a0a0] mt-1">
            Sign in to Querious
          </p>
        </div>

        {/* Error Message */}
        {(error || authError) && (
          <div className="mb-6 px-4 py-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 text-sm">
            {error || authError}
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="email"
              className="block text-sm font-medium text-neutral-700 dark:text-zinc-300 mb-1.5"
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              autoFocus
              className="w-full px-4 py-3 rounded-xl border border-zinc-300 dark:border-[#3a3a3a] 
                         bg-[#f8f8f8] dark:bg-[#242424] text-[#1a1a1a] dark:text-[#ececec]
                         placeholder:text-[#a0a0a0] dark:placeholder:text-[#a3a3a3]
                         focus:ring-2 focus:ring-[#0d9488] focus:border-transparent
                         transition-all outline-none"
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="block text-sm font-medium text-neutral-700 dark:text-zinc-300 mb-1.5"
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              className="w-full px-4 py-3 rounded-xl border border-zinc-300 dark:border-[#3a3a3a] 
                         bg-[#f8f8f8] dark:bg-[#242424] text-[#1a1a1a] dark:text-[#ececec]
                         placeholder:text-[#a0a0a0] dark:placeholder:text-[#a3a3a3]
                         focus:ring-2 focus:ring-[#0d9488] focus:border-transparent
                         transition-all outline-none"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 px-4 rounded-xl font-medium
                       bg-neutral-800 dark:bg-[#f8f8f8] text-white dark:text-[#1a1a1a]
                       hover:bg-neutral-700 dark:hover:bg-neutral-200
                       disabled:opacity-50 disabled:cursor-not-allowed
                       transition-colors duration-200"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                    fill="none"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                Signing in...
              </span>
            ) : (
              "Sign in"
            )}
          </button>
        </form>

        {/* Forgot Password */}
        <button
          type="button"
          onClick={onForgotPassword}
          className="w-full mt-4 text-sm text-[#a3a3a3] dark:text-[#a0a0a0] hover:text-[#0d9488] dark:hover:text-[#5eead4] transition-colors"
        >
          Forgot password?
        </button>

        {/* Divider */}
        <div className="relative my-8">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-[#e8e8e8] dark:border-[#3a3a3a]" />
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-4 bg-neutral-100 dark:bg-[#242424] text-[#a3a3a3]">
              or continue with
            </span>
          </div>
        </div>

        {/* Google Sign-In Button */}
        <button
          type="button"
          onClick={() => (window.location.href = "/api/auth/google")}
          className="w-full flex items-center justify-center gap-3 py-3 px-4 rounded-xl
                     border border-zinc-300 dark:border-[#3a3a3a] 
                     bg-[#f8f8f8] dark:bg-[#242424] 
                     text-neutral-700 dark:text-zinc-300
                     hover:bg-zinc-50 dark:hover:bg-neutral-800
                     transition-all"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24">
            <path
              fill="#4285F4"
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            />
            <path
              fill="#34A853"
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            />
            <path
              fill="#FBBC05"
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
            />
            <path
              fill="#EA4335"
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
            />
          </svg>
          Continue with Google
        </button>

        {/* Switch to Register */}
        <p className="text-center text-sm text-[#a3a3a3] dark:text-[#a0a0a0] mt-6">
          Don't have an account?{" "}
          <button
            type="button"
            onClick={onSwitchToRegister}
            className="font-medium text-[#0d9488] hover:text-[#0f766e] dark:hover:text-[#5eead4] transition-colors"
          >
            Sign up
          </button>
        </p>
      </div>
    </div>
  );
}
