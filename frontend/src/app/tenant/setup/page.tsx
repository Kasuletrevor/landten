"use client";

import { useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import api from "@/lib/api";
import { Building2, Key, Lock, AlertCircle, CheckCircle, ArrowRight } from "lucide-react";

function TenantSetupContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) {
      setError("Invalid or missing invite token.");
      return;
    }

    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setError("");
    setIsLoading(true);

    try {
      const res = await api.tenantSetupPassword(token, password);
      // Automatically store token if returned, or handle login redirect
      // The backend response for setup-password returns the TenantPortalResponse (profile)
      // but NOT a fresh access token for login. The user needs to log in explicitly.
      setSuccess(true);
      setTimeout(() => {
        router.push("/tenant/login");
      }, 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to set up password.");
    } finally {
      setIsLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="card p-8 text-center max-w-md w-full animate-fade-in">
        <AlertCircle className="w-12 h-12 text-[var(--error)] mx-auto mb-4" />
        <h2 className="text-xl font-semibold mb-2">Invalid Link</h2>
        <p className="text-[var(--text-secondary)] mb-6">
          This invite link is invalid or has expired. Please ask your landlord for a new one.
        </p>
        <Link href="/" className="btn btn-secondary w-full justify-center">
          Go Home
        </Link>
      </div>
    );
  }

  if (success) {
    return (
      <div className="card p-8 text-center max-w-md w-full animate-fade-in">
        <div className="w-16 h-16 bg-[var(--success-light)] rounded-full flex items-center justify-center mx-auto mb-6">
          <CheckCircle className="w-8 h-8 text-[var(--success)]" />
        </div>
        <h2 className="text-2xl font-bold mb-2">All Set!</h2>
        <p className="text-[var(--text-secondary)] mb-6">
          Your password has been created successfully. You can now log in to your tenant portal.
        </p>
        <Link href="/tenant/login" className="btn btn-primary w-full justify-center group">
          Go to Login
          <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
        </Link>
      </div>
    );
  }

  return (
    <div className="card max-w-md w-full p-8 animate-slide-up">
      <div className="text-center mb-8">
        <div className="w-12 h-12 bg-gradient-to-br from-[var(--primary-500)] to-[var(--primary-700)] rounded-xl flex items-center justify-center mx-auto mb-4 shadow-lg shadow-[var(--primary-500)]/20">
          <Key className="w-6 h-6 text-white" />
        </div>
        <h1
          className="text-2xl font-bold mb-2"
          style={{ fontFamily: "var(--font-outfit)" }}
        >
          Setup Your Account
        </h1>
        <p className="text-[var(--text-secondary)]">
          Create a password to access your tenant portal
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="p-3 bg-[var(--error-light)] text-[var(--error)] text-sm rounded-lg flex items-start gap-2 animate-fade-in">
            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <div>
          <label className="label">Create Password</label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]">
              <Lock className="w-5 h-5" />
            </span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input pl-10"
              placeholder="••••••••"
              required
              minLength={6}
            />
          </div>
        </div>

        <div>
          <label className="label">Confirm Password</label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]">
              <Lock className="w-5 h-5" />
            </span>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="input pl-10"
              placeholder="••••••••"
              required
              minLength={6}
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="btn btn-primary w-full justify-center mt-6"
        >
          {isLoading ? (
            <>
              <div className="spinner" />
              Setting up...
            </>
          ) : (
            "Create Account"
          )}
        </button>
      </form>
    </div>
  );
}

export default function TenantSetupPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-4 bg-[var(--background)]">
      <Suspense
        fallback={
          <div className="flex items-center justify-center">
            <div className="spinner" />
          </div>
        }
      >
        <TenantSetupContent />
      </Suspense>
    </div>
  );
}
