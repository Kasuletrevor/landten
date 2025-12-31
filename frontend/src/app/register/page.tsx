"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { Building2, Mail, Lock, User, Phone, AlertCircle, Check } from "lucide-react";

export default function RegisterPage() {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
    phone: "",
  });
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const { register } = useAuth();
  const router = useRouter();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (formData.password !== formData.confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    if (formData.password.length < 6) {
      setError("Password must be at least 6 characters");
      return;
    }

    setIsLoading(true);

    try {
      await register({
        name: formData.name,
        email: formData.email,
        password: formData.password,
        phone: formData.phone || undefined,
      });
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
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
            Create your account
          </h1>
          <p className="text-[var(--text-secondary)] mb-8">
            Start managing your properties in minutes.
          </p>

          {error && (
            <div className="flex items-center gap-2 p-3 mb-6 bg-[var(--error-light)] text-[var(--error)] rounded-lg text-sm animate-slide-down">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="name" className="label">
                Full name
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
                <input
                  id="name"
                  name="name"
                  type="text"
                  value={formData.name}
                  onChange={handleChange}
                  className="input pl-10"
                  placeholder="John Doe"
                  required
                />
              </div>
            </div>

            <div>
              <label htmlFor="email" className="label">
                Email address
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
                <input
                  id="email"
                  name="email"
                  type="email"
                  value={formData.email}
                  onChange={handleChange}
                  className="input pl-10"
                  placeholder="you@example.com"
                  required
                />
              </div>
            </div>

            <div>
              <label htmlFor="phone" className="label">
                Phone number <span className="text-[var(--text-muted)]">(optional)</span>
              </label>
              <div className="relative">
                <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
                <input
                  id="phone"
                  name="phone"
                  type="tel"
                  value={formData.phone}
                  onChange={handleChange}
                  className="input pl-10"
                  placeholder="+1 (555) 123-4567"
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="label">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
                <input
                  id="password"
                  name="password"
                  type="password"
                  value={formData.password}
                  onChange={handleChange}
                  className="input pl-10"
                  placeholder="Create a password"
                  required
                />
              </div>
            </div>

            <div>
              <label htmlFor="confirmPassword" className="label">
                Confirm password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
                <input
                  id="confirmPassword"
                  name="confirmPassword"
                  type="password"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  className="input pl-10"
                  placeholder="Confirm your password"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="btn btn-primary w-full py-3 mt-2"
            >
              {isLoading ? (
                <>
                  <div className="spinner" />
                  Creating account...
                </>
              ) : (
                "Create account"
              )}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-[var(--text-secondary)]">
            Already have an account?{" "}
            <Link href="/login" className="font-medium text-[var(--primary-600)] hover:text-[var(--primary-700)]">
              Sign in
            </Link>
          </p>
        </div>
      </div>

      {/* Right side - Benefits */}
      <div className="hidden lg:flex flex-1 items-center justify-center bg-gradient-to-br from-[var(--primary-500)] to-[var(--primary-800)] p-12">
        <div className="max-w-md text-white">
          <h2
            className="text-3xl font-bold mb-4"
            style={{ fontFamily: "var(--font-outfit)" }}
          >
            Start your free trial today
          </h2>
          <p className="text-[var(--primary-100)] mb-8">
            Join thousands of landlords who use LandTen to streamline their
            property management workflow.
          </p>
          <div className="space-y-4">
            {[
              "Track all your rental payments in one place",
              "Set up automated payment reminders",
              "Manage multiple properties and tenants",
              "Get real-time notifications and reports",
              "Free 14-day trial, no credit card required",
            ].map((benefit) => (
              <div
                key={benefit}
                className="flex items-start gap-3 text-sm text-white"
              >
                <div className="w-5 h-5 rounded-full bg-white/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Check className="w-3 h-3" />
                </div>
                {benefit}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
