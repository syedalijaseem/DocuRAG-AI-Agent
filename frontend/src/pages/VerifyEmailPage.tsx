/**
 * Email verification page - handles verification token from email link.
 */
import { useState, useEffect, useRef } from "react";

interface VerifyEmailPageProps {
  token: string;
  onSuccess: () => void;
  onError: () => void;
}

export function VerifyEmailPage({
  token,
  onSuccess,
  onError,
}: VerifyEmailPageProps) {
  const [status, setStatus] = useState<"verifying" | "success" | "error">(
    "verifying"
  );
  const [message, setMessage] = useState("");
  const hasVerified = useRef(false);

  useEffect(() => {
    // Clear token from URL immediately for security
    window.history.replaceState({}, "", "/");

    // Prevent double-call from React strict mode or re-renders
    if (hasVerified.current) return;
    hasVerified.current = true;

    verifyEmail();
  }, [token]);

  async function verifyEmail() {
    try {
      const response = await fetch(`/api/auth/verify-email?token=${token}`, {
        method: "GET",
        credentials: "include",
      });

      if (response.ok) {
        setStatus("success");
        setMessage("Your email has been verified successfully!");
        // Wait a moment before redirecting
        setTimeout(onSuccess, 2000);
      } else {
        const data = await response.json().catch(() => ({}));
        const errorDetail = data.detail || "";

        // If token is invalid/expired, the email might already be verified
        // Show a helpful message and allow login
        if (
          errorDetail.includes("Invalid") ||
          errorDetail.includes("expired")
        ) {
          setStatus("error");
          setMessage(
            "This verification link has already been used or expired. If you've already verified, try logging in."
          );
        } else {
          setStatus("error");
          setMessage(errorDetail || "Verification failed. Please try again.");
        }
      }
    } catch (err) {
      setStatus("error");
      setMessage("Failed to verify email. Please try again.");
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-zinc-100 dark:bg-zinc-950 transition-colors">
      <div className="w-full max-w-md px-6 text-center">
        {status === "verifying" && (
          <>
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-zinc-200 dark:bg-zinc-800 mb-6">
              <svg
                className="animate-spin w-8 h-8 text-zinc-600 dark:text-zinc-400"
                viewBox="0 0 24 24"
              >
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
            </div>
            <h2 className="text-2xl font-semibold text-zinc-900 dark:text-white mb-2">
              Verifying your email...
            </h2>
            <p className="text-zinc-500 dark:text-zinc-400">
              Please wait while we verify your email address.
            </p>
          </>
        )}

        {status === "success" && (
          <>
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-100 dark:bg-green-900/30 mb-6">
              <svg
                className="w-8 h-8 text-green-600 dark:text-green-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
            <h2 className="text-2xl font-semibold text-zinc-900 dark:text-white mb-2">
              Email verified!
            </h2>
            <p className="text-zinc-500 dark:text-zinc-400">{message}</p>
            <p className="text-zinc-400 dark:text-zinc-500 text-sm mt-4">
              Redirecting to login...
            </p>
          </>
        )}

        {status === "error" && (
          <>
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-red-100 dark:bg-red-900/30 mb-6">
              <svg
                className="w-8 h-8 text-red-600 dark:text-red-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </div>
            <h2 className="text-2xl font-semibold text-zinc-900 dark:text-white mb-2">
              Verification failed
            </h2>
            <p className="text-zinc-500 dark:text-zinc-400 mb-6">{message}</p>
            <button
              onClick={onError}
              className="py-3 px-6 rounded-xl font-medium
                         bg-zinc-900 dark:bg-white text-white dark:text-zinc-900
                         hover:bg-zinc-800 dark:hover:bg-zinc-100
                         transition-all"
            >
              Back to login
            </button>
          </>
        )}
      </div>
    </div>
  );
}
