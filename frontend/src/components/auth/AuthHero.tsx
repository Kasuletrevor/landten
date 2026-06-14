"use client";

import {
  BarChart3,
  Bell,
  Building2,
  LayoutDashboard,
  Users,
} from "lucide-react";

const FEATURES = [
  {
    icon: BarChart3,
    title: "Rent tracking",
    description: "Track payments, due dates, and financial performance in one place.",
  },
  {
    icon: Users,
    title: "Tenant management",
    description: "Store tenant details, leases, and communication history securely.",
  },
  {
    icon: Building2,
    title: "Multiple properties",
    description: "Manage all your properties and units from a single, powerful dashboard.",
  },
  {
    icon: Bell,
    title: "Real-time notifications",
    description: "Stay updated with instant alerts on payments and important events.",
  },
];

const TRUST_MARKS = [
  "Urban Nest",
  "Pinecrest",
  "Summit",
  "Horizon",
];

export function AuthHero() {
  return (
    <div className="hidden lg:flex flex-1 relative overflow-hidden bg-gradient-to-br from-[var(--primary-500)] via-[var(--primary-600)] to-[var(--primary-800)]">
      {/* Property photo background with warm overlay */}
      <div
        className="absolute inset-0 bg-cover bg-center"
        style={{ backgroundImage: "url('/images/property.png')" }}
      />
      <div className="absolute inset-0 bg-gradient-to-br from-[var(--primary-500)]/92 via-[var(--primary-600)]/88 to-[var(--primary-800)]/90" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(255,255,255,0.10),transparent_45%)]" />

      {/* Content */}
      <div className="relative z-10 flex flex-col justify-between h-full p-12 xl:p-16">
        <div className="max-w-lg">
          <h2
            className="text-4xl xl:text-5xl font-bold text-white leading-tight mb-4"
            style={{ fontFamily: "var(--font-outfit)" }}
          >
            Manage your properties with ease
          </h2>
          <p className="text-[var(--primary-100)] text-base xl:text-lg leading-relaxed">
            LandTen helps you stay organized, collect rent on time, and build better
            relationships with your tenants.
          </p>
        </div>

        {/* Feature list */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 max-w-xl">
          {FEATURES.map(({ icon: Icon, title, description }) => (
            <div key={title} className="flex gap-4">
              <div className="flex-shrink-0 w-11 h-11 rounded-xl bg-white/10 backdrop-blur-sm flex items-center justify-center">
                <Icon className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="font-semibold text-white text-sm">{title}</h3>
                <p className="text-[var(--primary-100)] text-xs leading-relaxed mt-0.5">
                  {description}
                </p>
              </div>
            </div>
          ))}
        </div>

        {/* Dashboard mockup */}
        <div className="relative max-w-xl w-full hidden xl:block">
          <div className="rounded-2xl border border-white/15 bg-white/10 backdrop-blur-md shadow-2xl overflow-hidden">
            <div className="flex h-64">
              {/* Sidebar */}
              <div className="w-40 bg-[var(--neutral-900)]/80 p-4 flex flex-col gap-3">
                <div className="flex items-center gap-2 text-white font-semibold text-xs mb-2">
                  <div className="w-5 h-5 rounded bg-gradient-to-br from-[var(--primary-500)] to-[var(--primary-700)] flex items-center justify-center">
                    <Building2 className="w-3 h-3 text-white" />
                  </div>
                  LandTen
                </div>
                {["Overview", "Properties", "Tenants", "Payments", "Maintenance"].map(
                  (item, i) => (
                    <div
                      key={item}
                      className={`flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs ${
                        i === 0
                          ? "bg-[var(--primary-600)]/50 text-white"
                          : "text-[var(--text-muted)]"
                      }`}
                    >
                      <div className="w-3.5 h-3.5 rounded bg-white/10" />
                      {item}
                    </div>
                  )
                )}
              </div>

              {/* Main panel */}
              <div className="flex-1 bg-[var(--surface)]/95 p-5">
                <h4 className="text-[var(--text-primary)] font-semibold text-sm mb-4">
                  Overview
                </h4>
                <div className="grid grid-cols-3 gap-3 mb-4">
                  {[
                    { label: "Total Properties", value: "24" },
                    { label: "Total Tenants", value: "156" },
                    { label: "Monthly Revenue", value: "$45,320" },
                  ].map(({ label, value }) => (
                    <div
                      key={label}
                      className="rounded-xl bg-[var(--surface-inset)] p-3"
                    >
                      <p className="text-[var(--text-muted)] text-[10px] uppercase tracking-wide">
                        {label}
                      </p>
                      <p className="text-[var(--text-primary)] font-bold text-lg mt-1">
                        {value}
                      </p>
                    </div>
                  ))}
                </div>
                <div className="flex gap-4">
                  <div className="flex-1 rounded-xl bg-[var(--surface-inset)] p-3 h-20">
                    <div className="flex items-center gap-2 mb-2">
                      <LayoutDashboard className="w-3.5 h-3.5 text-[var(--primary-500)]" />
                      <span className="text-[var(--text-primary)] text-xs font-medium">
                        Recent Payments
                      </span>
                    </div>
                    <div className="space-y-1.5">
                      {[1, 2].map((i) => (
                        <div key={i} className="flex items-center justify-between">
                          <div className="w-16 h-1.5 rounded-full bg-[var(--border)]" />
                          <div className="w-8 h-1.5 rounded-full bg-[var(--success)]" />
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="w-28 rounded-xl bg-[var(--surface-inset)] p-3 h-20 flex flex-col items-center justify-center">
                    <div className="w-12 h-12 rounded-full border-4 border-[var(--primary-500)] flex items-center justify-center">
                      <span className="text-[var(--text-primary)] text-[10px] font-bold">
                        80%
                      </span>
                    </div>
                    <span className="text-[var(--text-muted)] text-[10px] mt-1">
                      Collected
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Trust badges */}
        <div className="max-w-xl">
          <p className="text-[var(--primary-100)] text-xs mb-4">
            Trusted by property managers worldwide
          </p>
          <div className="flex items-center gap-6 opacity-80">
            {TRUST_MARKS.map((name) => (
              <div key={name} className="flex items-center gap-1.5 text-white/90">
                <Building2 className="w-4 h-4" />
                <span className="text-xs font-medium tracking-wide">{name}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
