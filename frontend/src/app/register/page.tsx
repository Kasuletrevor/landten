"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { AuthSplitLayout } from "@/components/auth/AuthSplitLayout";
import {
  Mail,
  Lock,
  User,
  AlertCircle,
  Eye,
  EyeOff,
  ChevronDown,
} from "lucide-react";

const countryCodes = [
  { code: "+256", country: "UG", flag: "🇺🇬", name: "Uganda" },
  { code: "+254", country: "KE", flag: "🇰🇪", name: "Kenya" },
  { code: "+255", country: "TZ", flag: "🇹🇿", name: "Tanzania" },
  { code: "+250", country: "RW", flag: "🇷🇼", name: "Rwanda" },
  { code: "+211", country: "SS", flag: "🇸🇸", name: "South Sudan" },
  { code: "+243", country: "CD", flag: "🇨🇩", name: "DR Congo" },
  { code: "+234", country: "NG", flag: "🇳🇬", name: "Nigeria" },
  { code: "+233", country: "GH", flag: "🇬🇭", name: "Ghana" },
  { code: "+27", country: "ZA", flag: "🇿🇦", name: "South Africa" },
  { code: "+1", country: "US", flag: "🇺🇸", name: "United States" },
  { code: "+44", country: "GB", flag: "🇬🇧", name: "United Kingdom" },
];

export default function RegisterPage() {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
    phone: "",
  });
  const [countryCode, setCountryCode] = useState(countryCodes[0]);
  const [showCountryDropdown, setShowCountryDropdown] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
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
        phone: formData.phone ? `${countryCode.code}${formData.phone}` : undefined,
      });
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthSplitLayout
      footer={
        <>
          By creating an account, you agree to our{" "}
          <Link href="#" className="text-[var(--primary-400)] hover:underline">
            Terms of Service
          </Link>{" "}
          and{" "}
          <Link href="#" className="text-[var(--primary-400)] hover:underline">
            Privacy Policy
          </Link>
          .
        </>
      }
    >
      <div className="text-center">
        <div className="w-14 h-14 mx-auto mb-5 rounded-full bg-white/5 border border-white/10 flex items-center justify-center">
          <User className="w-6 h-6 text-[var(--primary-400)]" />
        </div>
        <h1
          className="text-3xl font-bold text-white mb-2"
          style={{ fontFamily: "var(--font-outfit)" }}
        >
          Create your account
        </h1>
        <p className="text-[var(--text-secondary)] text-sm">
          Start managing your properties in minutes.
        </p>
      </div>

      {error && (
        <div className="mt-6 flex items-center gap-2 p-3 bg-[var(--error)]/10 border border-[var(--error)]/20 text-[var(--error)] rounded-xl text-sm animate-slide-down">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="mt-8 space-y-5">
        <div>
          <label htmlFor="name" className="block text-sm font-medium text-[var(--text-secondary)] mb-2">
            Full name
          </label>
          <div className="relative">
            <User className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[var(--text-muted)] pointer-events-none" />
            <input
              id="name"
              name="name"
              type="text"
              value={formData.name}
              onChange={handleChange}
              className="w-full bg-white/5 border border-white/10 rounded-xl py-3 pl-13 pr-4 text-white placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--primary-500)] focus:ring-1 focus:ring-[var(--primary-500)] transition-all"
              placeholder="John Doe"
              required
              autoComplete="name"
            />
          </div>
        </div>

        <div>
          <label htmlFor="email" className="block text-sm font-medium text-[var(--text-secondary)] mb-2">
            Email address
          </label>
          <div className="relative">
            <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[var(--text-muted)] pointer-events-none" />
            <input
              id="email"
              name="email"
              type="email"
              value={formData.email}
              onChange={handleChange}
              className="w-full bg-white/5 border border-white/10 rounded-xl py-3 pl-13 pr-4 text-white placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--primary-500)] focus:ring-1 focus:ring-[var(--primary-500)] transition-all"
              placeholder="you@example.com"
              required
              autoComplete="email"
            />
          </div>
        </div>

        <div>
          <label htmlFor="phone" className="block text-sm font-medium text-[var(--text-secondary)] mb-2">
            Phone number <span className="text-[var(--text-muted)]">(optional)</span>
          </label>
          <div className="relative flex">
            <div className="relative">
              <button
                type="button"
                onClick={() => setShowCountryDropdown(!showCountryDropdown)}
                className="flex items-center gap-1 h-full px-3 border border-r-0 border-white/10 rounded-l-xl bg-white/5 hover:bg-white/10 transition-colors text-white"
              >
                <span className="text-lg">{countryCode.flag}</span>
                <span className="text-sm font-medium text-[var(--text-secondary)]">{countryCode.code}</span>
                <ChevronDown className="w-4 h-4 text-[var(--text-muted)]" />
              </button>
              {showCountryDropdown && (
                <div className="absolute top-full left-0 mt-1 w-56 max-h-60 overflow-y-auto bg-[var(--neutral-900)] border border-white/10 rounded-xl shadow-lg z-50">
                  {countryCodes.map((country) => (
                    <button
                      key={country.code}
                      type="button"
                      onClick={() => {
                        setCountryCode(country);
                        setShowCountryDropdown(false);
                      }}
                      className={`w-full flex items-center gap-3 px-4 py-2.5 hover:bg-white/5 transition-colors text-left ${
                        countryCode.code === country.code ? "bg-[var(--primary-600)]/20" : ""
                      }`}
                    >
                      <span className="text-lg">{country.flag}</span>
                      <span className="text-sm font-medium text-white">{country.name}</span>
                      <span className="text-sm text-[var(--text-muted)] ml-auto">{country.code}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
            <div className="relative flex-1">
              <input
                id="phone"
                name="phone"
                type="tel"
                value={formData.phone}
                onChange={handleChange}
                className="w-full bg-white/5 border border-white/10 rounded-r-xl py-3 px-4 text-white placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--primary-500)] focus:ring-1 focus:ring-[var(--primary-500)] transition-all"
                placeholder="712345678"
              />
            </div>
          </div>
        </div>

        <div>
          <label htmlFor="password" className="block text-sm font-medium text-[var(--text-secondary)] mb-2">
            Password
          </label>
          <div className="relative">
            <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[var(--text-muted)] pointer-events-none" />
            <input
              id="password"
              name="password"
              type={showPassword ? "text" : "password"}
              value={formData.password}
              onChange={handleChange}
              className="w-full bg-white/5 border border-white/10 rounded-xl py-3 pl-13 pr-12 text-white placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--primary-500)] focus:ring-1 focus:ring-[var(--primary-500)] transition-all"
              placeholder="Create a password"
              required
              autoComplete="new-password"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-4 top-1/2 -translate-y-1/2 text-[var(--text-muted)] hover:text-white transition-colors"
            >
              {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
            </button>
          </div>
        </div>

        <div>
          <label htmlFor="confirmPassword" className="block text-sm font-medium text-[var(--text-secondary)] mb-2">
            Confirm password
          </label>
          <div className="relative">
            <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[var(--text-muted)] pointer-events-none" />
            <input
              id="confirmPassword"
              name="confirmPassword"
              type={showConfirmPassword ? "text" : "password"}
              value={formData.confirmPassword}
              onChange={handleChange}
              className="w-full bg-white/5 border border-white/10 rounded-xl py-3 pl-13 pr-12 text-white placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--primary-500)] focus:ring-1 focus:ring-[var(--primary-500)] transition-all"
              placeholder="Confirm your password"
              required
              autoComplete="new-password"
            />
            <button
              type="button"
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
              className="absolute right-4 top-1/2 -translate-y-1/2 text-[var(--text-muted)] hover:text-white transition-colors"
            >
              {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
            </button>
          </div>
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-[var(--primary-500)] to-[var(--primary-600)] text-white font-medium flex items-center justify-center gap-2 hover:from-[var(--primary-400)] hover:to-[var(--primary-500)] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? (
            <>
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Creating account...
            </>
          ) : (
            "Create account"
          )}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-[var(--text-secondary)]">
        Already have an account?{" "}
        <Link href="/login" className="font-medium text-[var(--primary-400)] hover:text-[var(--primary-300)] transition-colors">
          Sign in
        </Link>
      </p>
    </AuthSplitLayout>
  );
}
