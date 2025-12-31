"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import api, { TenantWithDetails, Payment, PaymentStatus } from "@/lib/api";
import {
  User,
  ArrowLeft,
  Mail,
  Phone,
  Calendar,
  Home,
  CreditCard,
  Clock,
  CheckCircle,
  AlertTriangle,
  Ban,
  Pencil,
  UserMinus,
  X,
  AlertCircle,
  DollarSign,
  Settings,
} from "lucide-react";

export default function TenantDetailPage() {
  const params = useParams();
  const router = useRouter();
  const tenantId = params.id as string;

  const [tenant, setTenant] = useState<TenantWithDetails | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  // Modals
  const [showEditTenant, setShowEditTenant] = useState(false);
  const [showEditSchedule, setShowEditSchedule] = useState(false);
  const [showMoveOut, setShowMoveOut] = useState(false);
  const [markPaidPayment, setMarkPaidPayment] = useState<Payment | null>(null);

  useEffect(() => {
    loadData();
  }, [tenantId]);

  const loadData = async () => {
    try {
      const res = await api.getTenant(tenantId);
      setTenant(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load tenant");
    } finally {
      setIsLoading(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
    }).format(amount);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const statusConfig: Record<PaymentStatus, { class: string; label: string; icon: typeof Clock }> = {
    UPCOMING: { class: "badge-info", label: "Upcoming", icon: Clock },
    PENDING: { class: "badge-warning", label: "Pending", icon: Clock },
    ON_TIME: { class: "badge-success", label: "Paid", icon: CheckCircle },
    LATE: { class: "badge-warning", label: "Late", icon: AlertTriangle },
    OVERDUE: { class: "badge-error", label: "Overdue", icon: AlertTriangle },
    WAIVED: { class: "badge-neutral", label: "Waived", icon: Ban },
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="spinner" />
      </div>
    );
  }

  if (error || !tenant) {
    return (
      <div className="animate-fade-in">
        <Link
          href="/dashboard/tenants"
          className="inline-flex items-center gap-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Tenants
        </Link>
        <div className="card p-8 text-center">
          <AlertCircle className="w-12 h-12 text-[var(--error)] mx-auto mb-4" />
          <h2 className="text-xl font-semibold mb-2">Tenant Not Found</h2>
          <p className="text-[var(--text-secondary)]">{error || "The tenant you're looking for doesn't exist."}</p>
        </div>
      </div>
    );
  }

  // Calculate payment stats
  const paidPayments = tenant.payments.filter((p) => p.status === "ON_TIME" || p.status === "LATE").length;
  const overduePayments = tenant.payments.filter((p) => p.status === "OVERDUE").length;
  const totalPaid = tenant.payments
    .filter((p) => p.status === "ON_TIME" || p.status === "LATE")
    .reduce((sum, p) => sum + p.amount_due, 0);

  return (
    <div className="animate-fade-in">
      {/* Back Link */}
      <Link
        href="/dashboard/tenants"
        className="inline-flex items-center gap-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] mb-6 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Tenants
      </Link>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Tenant Info */}
        <div className="lg:col-span-1 space-y-6">
          {/* Tenant Card */}
          <div className="card animate-slide-up">
            <div className="p-6">
              <div className="flex items-center gap-4 mb-6">
                <div className="avatar avatar-lg avatar-primary">
                  {tenant.name.charAt(0).toUpperCase()}
                </div>
                <div className="flex-1">
                  <h1
                    className="text-xl font-bold"
                    style={{ fontFamily: "var(--font-outfit)" }}
                  >
                    {tenant.name}
                  </h1>
                  <span
                    className={`badge ${tenant.is_active ? "badge-success" : "badge-neutral"}`}
                  >
                    {tenant.is_active ? "Active" : "Inactive"}
                  </span>
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-[var(--surface-inset)] flex items-center justify-center">
                    <Mail className="w-4 h-4 text-[var(--text-muted)]" />
                  </div>
                  <div>
                    <p className="text-xs text-[var(--text-muted)]">Email</p>
                    <p className="text-sm">{tenant.email || "Not provided"}</p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-[var(--surface-inset)] flex items-center justify-center">
                    <Phone className="w-4 h-4 text-[var(--text-muted)]" />
                  </div>
                  <div>
                    <p className="text-xs text-[var(--text-muted)]">Phone</p>
                    <p className="text-sm">{tenant.phone || "Not provided"}</p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-[var(--surface-inset)] flex items-center justify-center">
                    <Calendar className="w-4 h-4 text-[var(--text-muted)]" />
                  </div>
                  <div>
                    <p className="text-xs text-[var(--text-muted)]">Move-in Date</p>
                    <p className="text-sm">{formatDate(tenant.move_in_date)}</p>
                  </div>
                </div>

                {tenant.move_out_date && (
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-[var(--error-light)] flex items-center justify-center">
                      <UserMinus className="w-4 h-4 text-[var(--error)]" />
                    </div>
                    <div>
                      <p className="text-xs text-[var(--text-muted)]">Move-out Date</p>
                      <p className="text-sm">{formatDate(tenant.move_out_date)}</p>
                    </div>
                  </div>
                )}
              </div>

              <div className="divider" />

              <div className="flex gap-2">
                <button
                  onClick={() => setShowEditTenant(true)}
                  className="btn btn-secondary flex-1"
                >
                  <Pencil className="w-4 h-4" />
                  Edit
                </button>
                {tenant.is_active && (
                  <button
                    onClick={() => setShowMoveOut(true)}
                    className="btn btn-ghost text-[var(--error)]"
                  >
                    <UserMinus className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Property & Room */}
          <div className="card animate-slide-up stagger-1">
            <div className="p-5">
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                <Home className="w-4 h-4 text-[var(--text-muted)]" />
                Property & Room
              </h3>
              <Link
                href={`/dashboard/properties/${tenant.property?.id}`}
                className="block p-4 bg-[var(--surface-inset)] rounded-xl hover:bg-[var(--neutral-200)] transition-colors"
              >
                <p className="font-medium">{tenant.property?.name}</p>
                <p className="text-sm text-[var(--text-muted)]">
                  {tenant.property?.address}
                </p>
                <div className="mt-2 pt-2 border-t border-[var(--border)] flex items-center justify-between">
                  <span className="text-sm text-[var(--text-secondary)]">
                    {tenant.room?.name}
                  </span>
                  <span className="text-sm font-medium">
                    {formatCurrency(tenant.room?.rent_amount || 0)}/mo
                  </span>
                </div>
              </Link>
            </div>
          </div>

          {/* Payment Schedule */}
          {tenant.payment_schedule && (
            <div className="card animate-slide-up stagger-2">
              <div className="p-5">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold flex items-center gap-2">
                    <Settings className="w-4 h-4 text-[var(--text-muted)]" />
                    Payment Schedule
                  </h3>
                  <button
                    onClick={() => setShowEditSchedule(true)}
                    className="btn btn-ghost btn-sm"
                  >
                    <Pencil className="w-3 h-3" />
                  </button>
                </div>
                <div className="space-y-3">
                  <div className="flex justify-between text-sm">
                    <span className="text-[var(--text-muted)]">Amount</span>
                    <span className="font-medium">
                      {formatCurrency(tenant.payment_schedule.amount)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-[var(--text-muted)]">Frequency</span>
                    <span className="font-medium">
                      {tenant.payment_schedule.frequency.replace("_", "-")}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-[var(--text-muted)]">Due Day</span>
                    <span className="font-medium">
                      {tenant.payment_schedule.due_day}
                      {getOrdinalSuffix(tenant.payment_schedule.due_day)} of month
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-[var(--text-muted)]">Grace Period</span>
                    <span className="font-medium">
                      {tenant.payment_schedule.window_days} days
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Column - Payments */}
        <div className="lg:col-span-2 space-y-6">
          {/* Stats */}
          <div className="grid grid-cols-3 gap-4">
            {[
              {
                label: "Total Paid",
                value: formatCurrency(totalPaid),
                icon: DollarSign,
                color: "success",
              },
              {
                label: "Payments Made",
                value: paidPayments,
                icon: CheckCircle,
                color: "primary",
              },
              {
                label: "Overdue",
                value: overduePayments,
                icon: AlertTriangle,
                color: overduePayments > 0 ? "error" : "neutral",
              },
            ].map((stat, i) => (
              <div
                key={stat.label}
                className="card stat-card animate-slide-up"
                style={{ animationDelay: `${i * 0.05}s` }}
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                      stat.color === "success"
                        ? "bg-[var(--success-light)]"
                        : stat.color === "primary"
                        ? "bg-[var(--primary-100)]"
                        : stat.color === "error"
                        ? "bg-[var(--error-light)]"
                        : "bg-[var(--surface-inset)]"
                    }`}
                  >
                    <stat.icon
                      className={`w-5 h-5 ${
                        stat.color === "success"
                          ? "text-[var(--success)]"
                          : stat.color === "primary"
                          ? "text-[var(--primary-600)]"
                          : stat.color === "error"
                          ? "text-[var(--error)]"
                          : "text-[var(--text-muted)]"
                      }`}
                    />
                  </div>
                  <div>
                    <p className="stat-label">{stat.label}</p>
                    <p className="stat-value text-lg">{stat.value}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Payment History */}
          <div className="card animate-slide-up stagger-3">
            <div className="p-5 border-b border-[var(--border)]">
              <h3
                className="font-semibold"
                style={{ fontFamily: "var(--font-outfit)" }}
              >
                Payment History
              </h3>
            </div>
            {tenant.payments.length === 0 ? (
              <div className="p-8 text-center">
                <CreditCard className="w-12 h-12 text-[var(--text-muted)] mx-auto mb-3 opacity-50" />
                <p className="text-[var(--text-secondary)]">No payments yet</p>
              </div>
            ) : (
              <div className="divide-y divide-[var(--border)]">
                {tenant.payments.map((payment, i) => {
                  const status = statusConfig[payment.status];
                  const isPending = ["UPCOMING", "PENDING", "OVERDUE"].includes(payment.status);

                  return (
                    <div
                      key={payment.id}
                      className="p-4 hover:bg-[var(--surface-inset)] transition-colors animate-fade-in"
                      style={{ animationDelay: `${i * 0.03}s` }}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <div
                            className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                              payment.status === "ON_TIME" || payment.status === "LATE"
                                ? "bg-[var(--success-light)]"
                                : payment.status === "OVERDUE"
                                ? "bg-[var(--error-light)]"
                                : payment.status === "WAIVED"
                                ? "bg-[var(--surface-inset)]"
                                : "bg-[var(--warning-light)]"
                            }`}
                          >
                            <status.icon
                              className={`w-5 h-5 ${
                                payment.status === "ON_TIME" || payment.status === "LATE"
                                  ? "text-[var(--success)]"
                                  : payment.status === "OVERDUE"
                                  ? "text-[var(--error)]"
                                  : payment.status === "WAIVED"
                                  ? "text-[var(--text-muted)]"
                                  : "text-[var(--warning)]"
                              }`}
                            />
                          </div>
                          <div>
                            <p className="font-medium">
                              {formatDate(payment.period_start)} - {formatDate(payment.period_end)}
                            </p>
                            <p className="text-sm text-[var(--text-muted)]">
                              Due: {formatDate(payment.due_date)}
                              {payment.paid_date && ` | Paid: ${formatDate(payment.paid_date)}`}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-4">
                          <div className="text-right">
                            <p className="font-semibold">
                              {formatCurrency(payment.amount_due)}
                            </p>
                            <span className={`badge ${status.class}`}>
                              {status.label}
                            </span>
                          </div>
                          {isPending && (
                            <button
                              onClick={() => setMarkPaidPayment(payment)}
                              className="btn btn-sm btn-ghost text-[var(--success)]"
                              title="Mark as Paid"
                            >
                              <CheckCircle className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                      </div>
                      {payment.payment_reference && (
                        <p className="text-xs text-[var(--text-muted)] mt-2 ml-14">
                          Ref: {payment.payment_reference}
                        </p>
                      )}
                      {payment.notes && (
                        <p className="text-xs text-[var(--text-muted)] mt-1 ml-14">
                          Note: {payment.notes}
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Edit Tenant Modal */}
      {showEditTenant && (
        <EditTenantModal
          tenant={tenant}
          onClose={() => setShowEditTenant(false)}
          onSave={() => {
            loadData();
            setShowEditTenant(false);
          }}
        />
      )}

      {/* Edit Schedule Modal */}
      {showEditSchedule && tenant.payment_schedule && (
        <EditScheduleModal
          tenantId={tenant.id}
          schedule={tenant.payment_schedule}
          onClose={() => setShowEditSchedule(false)}
          onSave={() => {
            loadData();
            setShowEditSchedule(false);
          }}
        />
      )}

      {/* Move Out Modal */}
      {showMoveOut && (
        <MoveOutModal
          tenant={tenant}
          onClose={() => setShowMoveOut(false)}
          onSave={() => {
            loadData();
            setShowMoveOut(false);
          }}
        />
      )}

      {/* Mark Paid Modal */}
      {markPaidPayment && (
        <MarkPaidModal
          payment={markPaidPayment}
          tenantName={tenant.name}
          onClose={() => setMarkPaidPayment(null)}
          onSave={() => {
            loadData();
            setMarkPaidPayment(null);
          }}
        />
      )}
    </div>
  );
}

function getOrdinalSuffix(n: number): string {
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return s[(v - 20) % 10] || s[v] || s[0];
}

function EditTenantModal({
  tenant,
  onClose,
  onSave,
}: {
  tenant: TenantWithDetails;
  onClose: () => void;
  onSave: () => void;
}) {
  const [formData, setFormData] = useState({
    name: tenant.name,
    email: tenant.email || "",
    phone: tenant.phone || "",
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      await api.updateTenant(tenant.id, formData);
      onSave();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update tenant");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header flex items-center justify-between">
          <h2 className="text-xl font-semibold" style={{ fontFamily: "var(--font-outfit)" }}>
            Edit Tenant
          </h2>
          <button onClick={onClose} className="btn btn-ghost p-2">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body space-y-4">
            {error && (
              <div className="p-3 bg-[var(--error-light)] text-[var(--error)] rounded-lg text-sm">
                {error}
              </div>
            )}

            <div>
              <label className="label">Full Name</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))}
                className="input"
                required
              />
            </div>

            <div>
              <label className="label">Email</label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData((prev) => ({ ...prev, email: e.target.value }))}
                className="input"
              />
            </div>

            <div>
              <label className="label">Phone</label>
              <input
                type="tel"
                value={formData.phone}
                onChange={(e) => setFormData((prev) => ({ ...prev, phone: e.target.value }))}
                className="input"
              />
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" onClick={onClose} className="btn btn-secondary">
              Cancel
            </button>
            <button type="submit" disabled={isLoading} className="btn btn-primary">
              {isLoading ? (
                <>
                  <div className="spinner" />
                  Saving...
                </>
              ) : (
                "Save Changes"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function EditScheduleModal({
  tenantId,
  schedule,
  onClose,
  onSave,
}: {
  tenantId: string;
  schedule: TenantWithDetails["payment_schedule"];
  onClose: () => void;
  onSave: () => void;
}) {
  const [formData, setFormData] = useState<{
    amount: number;
    frequency: "MONTHLY" | "BI_MONTHLY" | "QUARTERLY";
    due_day: number;
    window_days: number;
  }>({
    amount: schedule?.amount || 0,
    frequency: schedule?.frequency || "MONTHLY",
    due_day: schedule?.due_day || 1,
    window_days: schedule?.window_days || 5,
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      await api.updatePaymentSchedule(tenantId, formData);
      onSave();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update schedule");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header flex items-center justify-between">
          <h2 className="text-xl font-semibold" style={{ fontFamily: "var(--font-outfit)" }}>
            Edit Payment Schedule
          </h2>
          <button onClick={onClose} className="btn btn-ghost p-2">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body space-y-4">
            {error && (
              <div className="p-3 bg-[var(--error-light)] text-[var(--error)] rounded-lg text-sm">
                {error}
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">Rent Amount</label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]">
                    $
                  </span>
                  <input
                    type="number"
                    value={formData.amount}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, amount: parseFloat(e.target.value) || 0 }))
                    }
                    className="input pl-8"
                    min="0"
                    required
                  />
                </div>
              </div>
              <div>
                <label className="label">Frequency</label>
                <select
                  value={formData.frequency}
                  onChange={(e) => setFormData((prev) => ({ ...prev, frequency: e.target.value as "MONTHLY" | "BI_MONTHLY" | "QUARTERLY" }))}
                  className="input"
                >
                  <option value="MONTHLY">Monthly</option>
                  <option value="BI_MONTHLY">Bi-Monthly</option>
                  <option value="QUARTERLY">Quarterly</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">Due Day</label>
                <input
                  type="number"
                  value={formData.due_day}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, due_day: parseInt(e.target.value) || 1 }))
                  }
                  className="input"
                  min="1"
                  max="28"
                  required
                />
              </div>
              <div>
                <label className="label">Grace Period (days)</label>
                <input
                  type="number"
                  value={formData.window_days}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, window_days: parseInt(e.target.value) || 0 }))
                  }
                  className="input"
                  min="0"
                  max="15"
                />
              </div>
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" onClick={onClose} className="btn btn-secondary">
              Cancel
            </button>
            <button type="submit" disabled={isLoading} className="btn btn-primary">
              {isLoading ? (
                <>
                  <div className="spinner" />
                  Saving...
                </>
              ) : (
                "Save Changes"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function MoveOutModal({
  tenant,
  onClose,
  onSave,
}: {
  tenant: TenantWithDetails;
  onClose: () => void;
  onSave: () => void;
}) {
  const [moveOutDate, setMoveOutDate] = useState(new Date().toISOString().split("T")[0]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      await api.moveOutTenant(tenant.id, moveOutDate);
      onSave();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to process move-out");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header flex items-center justify-between">
          <h2 className="text-xl font-semibold" style={{ fontFamily: "var(--font-outfit)" }}>
            Tenant Move-Out
          </h2>
          <button onClick={onClose} className="btn btn-ghost p-2">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {error && (
              <div className="p-3 mb-4 bg-[var(--error-light)] text-[var(--error)] rounded-lg text-sm">
                {error}
              </div>
            )}

            <div className="p-4 bg-[var(--warning-light)] rounded-xl mb-6">
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-[var(--warning)] flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-[var(--warning)]">
                    This will mark the tenant as inactive
                  </p>
                  <p className="text-sm text-[var(--text-secondary)] mt-1">
                    <strong>{tenant.name}</strong> will be moved out from{" "}
                    <strong>{tenant.room?.name}</strong>. The room will become available for new
                    tenants.
                  </p>
                </div>
              </div>
            </div>

            <div>
              <label className="label">Move-Out Date</label>
              <input
                type="date"
                value={moveOutDate}
                onChange={(e) => setMoveOutDate(e.target.value)}
                className="input"
                required
              />
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" onClick={onClose} className="btn btn-secondary">
              Cancel
            </button>
            <button type="submit" disabled={isLoading} className="btn btn-danger">
              {isLoading ? (
                <>
                  <div className="spinner" />
                  Processing...
                </>
              ) : (
                <>
                  <UserMinus className="w-4 h-4" />
                  Confirm Move-Out
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function MarkPaidModal({
  payment,
  tenantName,
  onClose,
  onSave,
}: {
  payment: Payment;
  tenantName: string;
  onClose: () => void;
  onSave: () => void;
}) {
  const [formData, setFormData] = useState({
    payment_reference: "",
    notes: "",
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.payment_reference.trim()) {
      setError("Payment reference is required");
      return;
    }

    setError("");
    setIsLoading(true);

    try {
      await api.markPaymentPaid(payment.id, {
        payment_reference: formData.payment_reference,
        notes: formData.notes || undefined,
      });
      onSave();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to mark as paid");
    } finally {
      setIsLoading(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
    }).format(amount);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header flex items-center justify-between">
          <h2 className="text-xl font-semibold" style={{ fontFamily: "var(--font-outfit)" }}>
            Record Payment
          </h2>
          <button onClick={onClose} className="btn btn-ghost p-2">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {error && (
              <div className="p-3 mb-4 bg-[var(--error-light)] text-[var(--error)] rounded-lg text-sm">
                {error}
              </div>
            )}

            <div className="p-4 bg-[var(--surface-inset)] rounded-xl mb-6">
              <div className="flex items-center justify-between">
                <span className="text-[var(--text-secondary)]">{tenantName}</span>
                <span className="text-xl font-bold" style={{ fontFamily: "var(--font-outfit)" }}>
                  {formatCurrency(payment.amount_due)}
                </span>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="label">
                  Payment Reference <span className="text-[var(--error)]">*</span>
                </label>
                <input
                  type="text"
                  value={formData.payment_reference}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, payment_reference: e.target.value }))
                  }
                  className="input"
                  placeholder="e.g., Bank transfer #12345"
                  required
                />
              </div>

              <div>
                <label className="label">Notes</label>
                <textarea
                  value={formData.notes}
                  onChange={(e) => setFormData((prev) => ({ ...prev, notes: e.target.value }))}
                  className="input min-h-[80px]"
                  placeholder="Optional notes..."
                />
              </div>
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" onClick={onClose} className="btn btn-secondary">
              Cancel
            </button>
            <button type="submit" disabled={isLoading} className="btn btn-primary">
              {isLoading ? (
                <>
                  <div className="spinner" />
                  Recording...
                </>
              ) : (
                <>
                  <CheckCircle className="w-4 h-4" />
                  Mark as Paid
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
