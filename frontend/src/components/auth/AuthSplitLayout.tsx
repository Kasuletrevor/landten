"use client";

import Link from "next/link";
import { Building2 } from "lucide-react";
import { AuthHero } from "./AuthHero";

interface AuthSplitLayoutProps {
  children: React.ReactNode;
  footer?: React.ReactNode;
}

export function AuthSplitLayout({ children, footer }: AuthSplitLayoutProps) {
  return (
    <div className="min-h-screen flex bg-[var(--neutral-950)]">
      {/* Left side — dark form panel */}
      <div className="relative flex-1 flex flex-col min-h-screen">
        <Link
          href="/"
          className="absolute top-6 left-6 sm:top-8 sm:left-8 flex items-center gap-2 z-10"
        >
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[var(--primary-500)] to-[var(--primary-700)] flex items-center justify-center">
            <Building2 className="w-4 h-4 text-white" />
          </div>
          <span
            className="font-semibold text-lg text-white"
            style={{ fontFamily: "var(--font-outfit)" }}
          >
            LandTen
          </span>
        </Link>

        <div className="flex-1 flex items-center justify-center p-6 sm:p-8">
          <div className="w-full max-w-md animate-fade-in">{children}</div>
        </div>

        {footer && (
          <div className="px-6 pb-6 sm:px-8 sm:pb-8 text-center text-xs text-[var(--text-muted)]">
            {footer}
          </div>
        )}
      </div>

      {/* Right side — hero panel */}
      <AuthHero />
    </div>
  );
}
