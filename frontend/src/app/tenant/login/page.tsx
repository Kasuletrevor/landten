"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import api from "@/lib/api";
import { Building2, Mail, Lock, AlertCircle, ArrowRight, Eye, EyeOff } from "lucide-react";

export default function TenantLoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      const res = await api.tenantLogin(email, password);
      // We manually set the token here since our AuthContext is primarily for Landlords
      // A more robust solution would be to update AuthContext to handle both user types
      // For now, we'll store it and redirect to the tenant dashboard
      api.setToken(res.access_token);
      router.push("/tenant/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to login");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-[var(--background)]">
      <div className="card max-w-md w-full p-8 animate-slide-up">
        <div className="text-center mb-8">
          <div className="w-12 h-12 bg-gradient-to-br from-[var(--primary-500)] to-[var(--primary-700)] rounded-xl flex items-center justify-center mx-auto mb-4 shadow-lg shadow-[var(--primary-500)]/20">
            <Building2 className="w-6 h-6 text-white" />
          </div>
          <h1
            className="text-2xl font-bold mb-2"
            style={{ fontFamily: "var(--font-outfit)" }}
          >
            Tenant Portal
          </h1>
          <p className="text-[var(--text-secondary)]">
            Sign in to view your payments and history
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
            <label className="label">Email</label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]">
                <Mail className="w-5 h-5" />
              </span>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input pl-10"
                placeholder="you@example.com"
                required
              />
            </div>
          </div>

          <div>
            <label className="label">Password</label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]">
                <Lock className="w-5 h-5" />
              </span>
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input pl-10 pr-10"
                placeholder="••••••••"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)] hover:text-[var(--text-secondary)] transition-colors"
              >
                {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="btn btn-primary w-full justify-center mt-6 group"
          >
            {isLoading ? (
              <>
                <div className="spinner" />
                Signing in...
              </>
            ) : (
              <>
                Sign In
                <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
              </>
            )}
          </button>
        </form>

        <div className="mt-8 pt-6 border-t border-[var(--border)] text-center text-sm text-[var(--text-muted)]">
          <p>Don&apos;t have an account?</p>
          <p className="mt-1">
            Ask your landlord for an invite link to set up your access.
          </p>
        </div>
      </div>
    </div>
  );
}
