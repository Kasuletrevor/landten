"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { Building2, Mail, Lock, AlertCircle } from "lucide-react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex bg-[var(--background)]">
      {/* Left side - Form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-md animate-fade-in">
          <Link href="/" className="flex items-center gap-2 mb-8">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[var(--primary-500)] to-[var(--primary-700)] flex items-center justify-center">
              <Building2 className="w-4 h-4 text-white" />
            </div>
            <span className="font-semibold text-lg" style={{ fontFamily: "var(--font-outfit)" }}>
              LandTen
            </span>
          </Link>

          <h1
            className="text-3xl font-bold mb-2"
            style={{ fontFamily: "var(--font-outfit)" }}
          >
            Welcome back
          </h1>
          <p className="text-[var(--text-secondary)] mb-8">
            Sign in to your account to continue managing your properties.
          </p>

          {error && (
            <div className="flex items-center gap-2 p-3 mb-6 bg-[var(--error-light)] text-[var(--error)] rounded-lg text-sm animate-slide-down">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label htmlFor="email" className="label">
                Email address
              </label>
              <div className="relative">
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[var(--text-muted)] pointer-events-none" />
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input pl-12"
                  placeholder="you@example.com"
                  required
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="label">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[var(--text-muted)] pointer-events-none" />
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input pl-12"
                  placeholder="Enter your password"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="btn btn-primary w-full py-3"
            >
              {isLoading ? (
                <>
                  <div className="spinner" />
                  Signing in...
                </>
              ) : (
                "Sign in"
              )}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-[var(--text-secondary)]">
            Don&apos;t have an account?{" "}
            <Link href="/register" className="font-medium text-[var(--primary-600)] hover:text-[var(--primary-700)]">
              Create one
            </Link>
          </p>
        </div>
      </div>

      {/* Right side - Image/Pattern */}
      <div className="hidden lg:flex flex-1 items-center justify-center bg-gradient-to-br from-[var(--primary-500)] to-[var(--primary-800)] p-12">
        <div className="max-w-md text-white">
          <h2
            className="text-3xl font-bold mb-4"
            style={{ fontFamily: "var(--font-outfit)" }}
          >
            Manage your properties with ease
          </h2>
          <p className="text-[var(--primary-100)] mb-8">
            Track payments, manage tenants, and stay organized with LandTen&apos;s
            intuitive property management platform.
          </p>
          <div className="grid grid-cols-2 gap-4">
            {[
              "Payment tracking",
              "Tenant management",
              "Multi-property support",
              "Real-time notifications",
            ].map((feature) => (
              <div
                key={feature}
                className="flex items-center gap-2 text-sm text-[var(--primary-100)]"
              >
                <div className="w-1.5 h-1.5 rounded-full bg-white" />
                {feature}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
