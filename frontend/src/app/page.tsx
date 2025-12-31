"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import {
  Building2,
  Users,
  CreditCard,
  Bell,
  ChevronRight,
  Shield,
  Clock,
  LineChart,
} from "lucide-react";

export default function LandingPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.push("/dashboard");
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--background)]">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-[var(--surface)]/80 backdrop-blur-md border-b border-[var(--border)]">
        <div className="container flex items-center justify-between h-16">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[var(--primary-500)] to-[var(--primary-700)] flex items-center justify-center">
              <Building2 className="w-4 h-4 text-white" />
            </div>
            <span className="font-semibold text-lg" style={{ fontFamily: "var(--font-outfit)" }}>
              LandTen
            </span>
          </div>
          <nav className="flex items-center gap-4">
            <Link
              href="/login"
              className="btn btn-ghost"
            >
              Sign In
            </Link>
            <Link
              href="/register"
              className="btn btn-primary"
            >
              Get Started
              <ChevronRight className="w-4 h-4" />
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="pt-32 pb-20">
        <div className="container">
          <div className="max-w-3xl mx-auto text-center">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-[var(--primary-100)] text-[var(--primary-700)] rounded-full text-sm font-medium mb-6 animate-fade-in">
              <Shield className="w-4 h-4" />
              Trusted by property managers
            </div>
            <h1
              className="text-5xl md:text-6xl font-bold mb-6 animate-slide-up"
              style={{ fontFamily: "var(--font-outfit)", lineHeight: 1.1 }}
            >
              Property management,{" "}
              <span className="bg-gradient-to-r from-[var(--primary-500)] to-[var(--primary-700)] bg-clip-text text-transparent">
                simplified
              </span>
            </h1>
            <p className="text-lg text-[var(--text-secondary)] mb-8 animate-slide-up stagger-1">
              Track rent payments, manage tenants, and stay on top of your property portfolio
              with LandTen&apos;s intuitive reconciliation platform.
            </p>
            <div className="flex items-center justify-center gap-4 animate-slide-up stagger-2">
              <Link href="/register" className="btn btn-primary text-base px-6 py-3">
                Start Free Trial
                <ChevronRight className="w-5 h-5" />
              </Link>
              <Link href="/tenant/login" className="btn btn-secondary text-base px-6 py-3">
                Tenant Portal
              </Link>
            </div>
          </div>

          {/* Dashboard Preview */}
          <div className="mt-16 relative animate-slide-up stagger-3">
            <div className="absolute inset-0 bg-gradient-to-t from-[var(--background)] to-transparent z-10 pointer-events-none h-32 bottom-0 top-auto" />
            <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] shadow-lg overflow-hidden">
              <div className="h-8 bg-[var(--neutral-100)] flex items-center gap-2 px-4 border-b border-[var(--border)]">
                <div className="w-3 h-3 rounded-full bg-[var(--error)]" />
                <div className="w-3 h-3 rounded-full bg-[var(--warning)]" />
                <div className="w-3 h-3 rounded-full bg-[var(--success)]" />
              </div>
              <div className="p-6 grid grid-cols-1 md:grid-cols-4 gap-4">
                {[
                  { label: "Total Properties", value: "12", icon: Building2 },
                  { label: "Active Tenants", value: "48", icon: Users },
                  { label: "Monthly Income", value: "$24,500", icon: CreditCard },
                  { label: "Pending Payments", value: "3", icon: Clock },
                ].map((stat, i) => (
                  <div
                    key={stat.label}
                    className="card p-4 animate-slide-up"
                    style={{ animationDelay: `${0.4 + i * 0.1}s` }}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-[var(--primary-100)] flex items-center justify-center">
                        <stat.icon className="w-5 h-5 text-[var(--primary-600)]" />
                      </div>
                      <div>
                        <p className="text-sm text-[var(--text-muted)]">{stat.label}</p>
                        <p className="text-xl font-semibold" style={{ fontFamily: "var(--font-outfit)" }}>
                          {stat.value}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 bg-[var(--surface)]">
        <div className="container">
          <div className="text-center mb-12">
            <h2
              className="text-3xl font-bold mb-4"
              style={{ fontFamily: "var(--font-outfit)" }}
            >
              Everything you need to manage properties
            </h2>
            <p className="text-[var(--text-secondary)] max-w-2xl mx-auto">
              From payment tracking to tenant management, LandTen provides all the tools you need
              to run your rental business efficiently.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                icon: CreditCard,
                title: "Payment Tracking",
                description:
                  "Record and reconcile rent payments with receipt references. Track on-time, late, and overdue payments at a glance.",
              },
              {
                icon: Users,
                title: "Tenant Management",
                description:
                  "Keep tenant information organized with move-in dates, contact details, and payment schedules all in one place.",
              },
              {
                icon: Building2,
                title: "Multi-Property Support",
                description:
                  "Manage multiple properties and rooms from a single dashboard. See occupancy and income across your portfolio.",
              },
              {
                icon: Clock,
                title: "Flexible Schedules",
                description:
                  "Set up monthly, bi-monthly, or quarterly payment schedules with customizable due dates and grace periods.",
              },
              {
                icon: Bell,
                title: "Smart Notifications",
                description:
                  "Get real-time alerts for upcoming payments, overdue rents, and tenant updates via email and in-app notifications.",
              },
              {
                icon: LineChart,
                title: "Financial Overview",
                description:
                  "View summaries of expected vs received payments, outstanding balances, and collection rates.",
              },
            ].map((feature, i) => (
              <div
                key={feature.title}
                className="card p-6 animate-slide-up"
                style={{ animationDelay: `${i * 0.1}s` }}
              >
                <div className="w-12 h-12 rounded-xl bg-[var(--primary-100)] flex items-center justify-center mb-4">
                  <feature.icon className="w-6 h-6 text-[var(--primary-600)]" />
                </div>
                <h3 className="text-lg font-semibold mb-2" style={{ fontFamily: "var(--font-outfit)" }}>
                  {feature.title}
                </h3>
                <p className="text-sm text-[var(--text-secondary)]">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20">
        <div className="container">
          <div className="card p-12 text-center bg-gradient-to-br from-[var(--primary-600)] to-[var(--primary-800)]">
            <h2
              className="text-3xl font-bold text-white mb-4"
              style={{ fontFamily: "var(--font-outfit)" }}
            >
              Ready to streamline your property management?
            </h2>
            <p className="text-[var(--primary-100)] mb-8 max-w-xl mx-auto">
              Join landlords who trust LandTen to keep their rental business organized and payments on track.
            </p>
            <Link
              href="/register"
              className="btn bg-white text-[var(--primary-700)] hover:bg-[var(--primary-50)] text-base px-8 py-3"
            >
              Get Started for Free
              <ChevronRight className="w-5 h-5" />
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 border-t border-[var(--border)]">
        <div className="container flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-gradient-to-br from-[var(--primary-500)] to-[var(--primary-700)] flex items-center justify-center">
              <Building2 className="w-3 h-3 text-white" />
            </div>
            <span className="text-sm text-[var(--text-secondary)]">
              LandTen &copy; {new Date().getFullYear()}
            </span>
          </div>
          <p className="text-sm text-[var(--text-muted)]">
            Property management made simple.
          </p>
        </div>
      </footer>
    </div>
  );
}
