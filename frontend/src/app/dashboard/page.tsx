"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import api, {
  PropertyListResponse,
  PaymentSummary,
  PaymentWithTenant,
} from "@/lib/api";
import {
  Building2,
  Users,
  CreditCard,
  Clock,
  AlertTriangle,
  ArrowUpRight,
  ArrowDownRight,
  ChevronRight,
  TrendingUp,
} from "lucide-react";

export default function DashboardPage() {
  const [properties, setProperties] = useState<PropertyListResponse | null>(null);
  const [summary, setSummary] = useState<PaymentSummary | null>(null);
  const [overduePayments, setOverduePayments] = useState<PaymentWithTenant[]>([]);
  const [upcomingPayments, setUpcomingPayments] = useState<PaymentWithTenant[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [propertiesRes, summaryRes, overdueRes, upcomingRes] = await Promise.all([
          api.getProperties(),
          api.getPaymentsSummary(),
          api.getOverduePayments(),
          api.getUpcomingPayments(7),
        ]);
        setProperties(propertiesRes);
        setSummary(summaryRes);
        setOverduePayments(overdueRes.payments);
        setUpcomingPayments(upcomingRes.payments);
      } catch (error) {
        console.error("Failed to load dashboard data:", error);
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="spinner" />
      </div>
    );
  }

  const totalTenants =
    properties?.properties.reduce((acc, p) => acc + p.total_tenants, 0) || 0;
  const monthlyIncome =
    properties?.properties.reduce((acc, p) => acc + p.monthly_expected_income, 0) ||
    0;
  const collectionRate =
    summary && summary.total_expected > 0
      ? ((summary.total_received / summary.total_expected) * 100).toFixed(0)
      : "0";

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    });
  };

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title" style={{ fontFamily: "var(--font-outfit)" }}>
            Dashboard
          </h1>
          <p className="page-subtitle">
            Welcome back! Here&apos;s an overview of your properties.
          </p>
        </div>
        <Link href="/dashboard/properties" className="btn btn-primary">
          Add Property
          <ChevronRight className="w-4 h-4" />
        </Link>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {[
          {
            label: "Total Properties",
            value: properties?.total || 0,
            icon: Building2,
            trend: null,
            color: "primary",
          },
          {
            label: "Active Tenants",
            value: totalTenants,
            icon: Users,
            trend: null,
            color: "info",
          },
          {
            label: "Monthly Income",
            value: formatCurrency(monthlyIncome),
            icon: CreditCard,
            trend: { value: 12, up: true },
            color: "success",
          },
          {
            label: "Collection Rate",
            value: `${collectionRate}%`,
            icon: TrendingUp,
            trend: null,
            color: "warning",
          },
        ].map((stat, i) => (
          <div
            key={stat.label}
            className="card stat-card animate-slide-up"
            style={{ animationDelay: `${i * 0.05}s` }}
          >
            <div className="flex items-center justify-between mb-3">
              <div
                className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                  stat.color === "primary"
                    ? "bg-[var(--primary-100)] text-[var(--primary-600)]"
                    : stat.color === "info"
                    ? "bg-[var(--info-light)] text-[var(--info)]"
                    : stat.color === "success"
                    ? "bg-[var(--success-light)] text-[var(--success)]"
                    : "bg-[var(--warning-light)] text-[var(--warning)]"
                }`}
              >
                <stat.icon className="w-5 h-5" />
              </div>
              {stat.trend && (
                <div
                  className={`stat-trend ${
                    stat.trend.up ? "stat-trend-up" : "stat-trend-down"
                  }`}
                >
                  {stat.trend.up ? (
                    <ArrowUpRight className="w-3 h-3" />
                  ) : (
                    <ArrowDownRight className="w-3 h-3" />
                  )}
                  {stat.trend.value}%
                </div>
              )}
            </div>
            <p className="stat-label">{stat.label}</p>
            <p className="stat-value">{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Overdue Payments */}
        <div className="card animate-slide-up stagger-2">
          <div className="p-4 border-b border-[var(--border)] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-[var(--error)]" />
              <h3
                className="font-semibold"
                style={{ fontFamily: "var(--font-outfit)" }}
              >
                Overdue Payments
              </h3>
              {overduePayments.length > 0 && (
                <span className="badge badge-error">{overduePayments.length}</span>
              )}
            </div>
            <Link
              href="/dashboard/payments?status=OVERDUE"
              className="text-sm text-[var(--primary-600)] hover:text-[var(--primary-700)] font-medium"
            >
              View all
            </Link>
          </div>
          {overduePayments.length === 0 ? (
            <div className="p-8 text-center">
              <div className="w-12 h-12 rounded-full bg-[var(--success-light)] flex items-center justify-center mx-auto mb-3">
                <CreditCard className="w-6 h-6 text-[var(--success)]" />
              </div>
              <p className="text-sm text-[var(--text-secondary)]">
                No overdue payments! Great job keeping up.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-[var(--border)]">
              {overduePayments.slice(0, 4).map((payment) => (
                <div key={payment.id} className="p-4 flex items-center gap-4">
                  <div className="w-10 h-10 rounded-full bg-[var(--error-light)] flex items-center justify-center">
                    <span className="text-sm font-medium text-[var(--error)]">
                      {payment.tenant?.name?.charAt(0).toUpperCase() || "?"}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm truncate">
                      {payment.tenant?.name || "Unknown"}
                    </p>
                    <p className="text-xs text-[var(--text-muted)]">
                      {payment.property?.name} · Due {formatDate(payment.due_date)}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold text-[var(--error)]">
                      {formatCurrency(payment.amount_due)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Upcoming Payments */}
        <div className="card animate-slide-up stagger-3">
          <div className="p-4 border-b border-[var(--border)] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-[var(--primary-600)]" />
              <h3
                className="font-semibold"
                style={{ fontFamily: "var(--font-outfit)" }}
              >
                Upcoming (7 days)
              </h3>
              {upcomingPayments.length > 0 && (
                <span className="badge badge-info">{upcomingPayments.length}</span>
              )}
            </div>
            <Link
              href="/dashboard/payments?status=UPCOMING"
              className="text-sm text-[var(--primary-600)] hover:text-[var(--primary-700)] font-medium"
            >
              View all
            </Link>
          </div>
          {upcomingPayments.length === 0 ? (
            <div className="p-8 text-center">
              <div className="w-12 h-12 rounded-full bg-[var(--neutral-100)] flex items-center justify-center mx-auto mb-3">
                <Clock className="w-6 h-6 text-[var(--text-muted)]" />
              </div>
              <p className="text-sm text-[var(--text-secondary)]">
                No payments due in the next 7 days.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-[var(--border)]">
              {upcomingPayments.slice(0, 4).map((payment) => (
                <div key={payment.id} className="p-4 flex items-center gap-4">
                  <div className="w-10 h-10 rounded-full bg-[var(--primary-100)] flex items-center justify-center">
                    <span className="text-sm font-medium text-[var(--primary-600)]">
                      {payment.tenant?.name?.charAt(0).toUpperCase() || "?"}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm truncate">
                      {payment.tenant?.name || "Unknown"}
                    </p>
                    <p className="text-xs text-[var(--text-muted)]">
                      {payment.property?.name} · Due {formatDate(payment.due_date)}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold">{formatCurrency(payment.amount_due)}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Properties Overview */}
        <div className="card lg:col-span-2 animate-slide-up stagger-4">
          <div className="p-4 border-b border-[var(--border)] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Building2 className="w-5 h-5 text-[var(--primary-600)]" />
              <h3
                className="font-semibold"
                style={{ fontFamily: "var(--font-outfit)" }}
              >
                Properties
              </h3>
            </div>
            <Link
              href="/dashboard/properties"
              className="text-sm text-[var(--primary-600)] hover:text-[var(--primary-700)] font-medium"
            >
              Manage properties
            </Link>
          </div>
          {!properties || properties.total === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">
                <Building2 className="w-full h-full" />
              </div>
              <p className="empty-state-title">No properties yet</p>
              <p className="empty-state-description">
                Add your first property to start tracking rent payments and managing
                tenants.
              </p>
              <Link href="/dashboard/properties" className="btn btn-primary">
                Add Property
              </Link>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="table">
                <thead>
                  <tr>
                    <th>Property</th>
                    <th>Rooms</th>
                    <th>Occupancy</th>
                    <th>Monthly Income</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {properties.properties.slice(0, 5).map((property) => (
                    <tr key={property.id}>
                      <td>
                        <div>
                          <p className="font-medium">{property.name}</p>
                          <p className="text-xs text-[var(--text-muted)]">
                            {property.address}
                          </p>
                        </div>
                      </td>
                      <td>{property.total_rooms}</td>
                      <td>
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-1.5 bg-[var(--neutral-200)] rounded-full overflow-hidden">
                            <div
                              className="h-full bg-[var(--success)] rounded-full"
                              style={{
                                width: `${
                                  property.total_rooms > 0
                                    ? (property.occupied_rooms / property.total_rooms) *
                                      100
                                    : 0
                                }%`,
                              }}
                            />
                          </div>
                          <span className="text-xs text-[var(--text-muted)]">
                            {property.occupied_rooms}/{property.total_rooms}
                          </span>
                        </div>
                      </td>
                      <td>{formatCurrency(property.monthly_expected_income)}</td>
                      <td>
                        <Link
                          href={`/dashboard/properties/${property.id}`}
                          className="btn btn-ghost btn-sm"
                        >
                          View
                          <ChevronRight className="w-4 h-4" />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
