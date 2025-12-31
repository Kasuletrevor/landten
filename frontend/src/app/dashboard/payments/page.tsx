"use client";

import { useEffect, useState } from "react";
import api, {
  PaymentWithTenant,
  PaymentSummary,
  PropertyWithStats,
  PaymentStatus,
} from "@/lib/api";
import {
  CreditCard,
  DollarSign,
  Clock,
  AlertTriangle,
  CheckCircle,
  Search,
  Filter,
  Calendar,
  ChevronDown,
  X,
  Send,
  Ban,
  Receipt,
  Home,
  User,
} from "lucide-react";

export default function PaymentsPage() {
  const [payments, setPayments] = useState<PaymentWithTenant[]>([]);
  const [summary, setSummary] = useState<PaymentSummary | null>(null);
  const [properties, setProperties] = useState<PropertyWithStats[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Filters
  const [filterProperty, setFilterProperty] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [dateRange, setDateRange] = useState({ start: "", end: "" });

  // Modals
  const [markPaidPayment, setMarkPaidPayment] = useState<PaymentWithTenant | null>(null);
  const [waivePayment, setWaivePayment] = useState<PaymentWithTenant | null>(null);
  const [sendReminderPayment, setSendReminderPayment] = useState<PaymentWithTenant | null>(null);

  useEffect(() => {
    loadData();
  }, [filterProperty, filterStatus, dateRange]);

  const loadData = async () => {
    try {
      const [paymentsRes, summaryRes, propertiesRes] = await Promise.all([
        api.getPayments({
          property_id: filterProperty || undefined,
          status: filterStatus || undefined,
          start_date: dateRange.start || undefined,
          end_date: dateRange.end || undefined,
        }),
        api.getPaymentsSummary(filterProperty || undefined),
        api.getProperties(),
      ]);
      setPayments(paymentsRes.payments);
      setSummary(summaryRes);
      setProperties(propertiesRes.properties);
    } catch (error) {
      console.error("Failed to load payments:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const filteredPayments = payments.filter(
    (payment) =>
      payment.tenant?.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      payment.property?.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      payment.room?.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

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

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title" style={{ fontFamily: "var(--font-outfit)" }}>
            Payments
          </h1>
          <p className="page-subtitle">Track and manage rent payments.</p>
        </div>
      </div>

      {/* Summary Stats */}
      {summary && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {[
            {
              label: "Expected",
              value: formatCurrency(summary.total_expected),
              icon: DollarSign,
              color: "primary",
            },
            {
              label: "Received",
              value: formatCurrency(summary.total_received),
              icon: CheckCircle,
              color: "success",
            },
            {
              label: "Outstanding",
              value: formatCurrency(summary.total_outstanding),
              icon: Clock,
              color: "warning",
            },
            {
              label: "Overdue",
              value: formatCurrency(summary.total_overdue),
              icon: AlertTriangle,
              color: "error",
              count: summary.overdue_count,
            },
          ].map((stat, i) => (
            <div
              key={stat.label}
              className="card stat-card animate-slide-up"
              style={{ animationDelay: `${i * 0.05}s` }}
            >
              <div className="flex items-center gap-4">
                <div
                  className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                    stat.color === "primary"
                      ? "bg-[var(--primary-100)]"
                      : stat.color === "success"
                      ? "bg-[var(--success-light)]"
                      : stat.color === "warning"
                      ? "bg-[var(--warning-light)]"
                      : "bg-[var(--error-light)]"
                  }`}
                >
                  <stat.icon
                    className={`w-6 h-6 ${
                      stat.color === "primary"
                        ? "text-[var(--primary-600)]"
                        : stat.color === "success"
                        ? "text-[var(--success)]"
                        : stat.color === "warning"
                        ? "text-[var(--warning)]"
                        : "text-[var(--error)]"
                    }`}
                  />
                </div>
                <div>
                  <p className="stat-label">{stat.label}</p>
                  <p className="stat-value text-xl">{stat.value}</p>
                  {stat.count !== undefined && stat.count > 0 && (
                    <p className="text-xs text-[var(--error)] mt-0.5">
                      {stat.count} payment{stat.count !== 1 ? "s" : ""}
                    </p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Quick Stats Row */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        {[
          { label: "Upcoming", count: summary?.upcoming_count || 0, status: "UPCOMING" },
          { label: "Pending", count: summary?.pending_count || 0, status: "PENDING" },
          { label: "Overdue", count: summary?.overdue_count || 0, status: "OVERDUE" },
          { label: "Paid", count: summary?.paid_count || 0, status: "ON_TIME" },
        ].map((item) => (
          <button
            key={item.label}
            onClick={() => setFilterStatus(filterStatus === item.status ? "" : item.status)}
            className={`card p-4 text-center transition-all ${
              filterStatus === item.status
                ? "ring-2 ring-[var(--primary-500)] border-[var(--primary-500)]"
                : "hover:border-[var(--border-strong)]"
            }`}
          >
            <p className="text-2xl font-bold" style={{ fontFamily: "var(--font-outfit)" }}>
              {item.count}
            </p>
            <p className="text-sm text-[var(--text-muted)]">{item.label}</p>
          </button>
        ))}
      </div>

      {/* Filters */}
      <div className="card p-4 mb-6 animate-slide-up stagger-2">
        <div className="flex flex-col lg:flex-row gap-4">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by tenant, property, or room..."
              className="input pl-10"
            />
          </div>

          {/* Property Filter */}
          <div className="w-full lg:w-48">
            <div className="select-wrapper">
              <select
                value={filterProperty}
                onChange={(e) => setFilterProperty(e.target.value)}
                className="input appearance-none cursor-pointer"
              >
                <option value="">All Properties</option>
                {properties.map((prop) => (
                  <option key={prop.id} value={prop.id}>
                    {prop.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Status Filter */}
          <div className="w-full lg:w-40">
            <div className="select-wrapper">
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="input appearance-none cursor-pointer"
              >
                <option value="">All Statuses</option>
                <option value="UPCOMING">Upcoming</option>
                <option value="PENDING">Pending</option>
                <option value="ON_TIME">Paid</option>
                <option value="LATE">Late</option>
                <option value="OVERDUE">Overdue</option>
                <option value="WAIVED">Waived</option>
              </select>
            </div>
          </div>

          {/* Date Range */}
          <div className="flex gap-2">
            <input
              type="date"
              value={dateRange.start}
              onChange={(e) => setDateRange((prev) => ({ ...prev, start: e.target.value }))}
              className="input w-36"
              placeholder="Start date"
            />
            <input
              type="date"
              value={dateRange.end}
              onChange={(e) => setDateRange((prev) => ({ ...prev, end: e.target.value }))}
              className="input w-36"
              placeholder="End date"
            />
          </div>

          {/* Clear Filters */}
          {(filterProperty || filterStatus || dateRange.start || dateRange.end) && (
            <button
              onClick={() => {
                setFilterProperty("");
                setFilterStatus("");
                setDateRange({ start: "", end: "" });
              }}
              className="btn btn-ghost text-sm"
            >
              <X className="w-4 h-4" />
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Payments Table */}
      {filteredPayments.length === 0 ? (
        <div className="card empty-state animate-slide-up stagger-3">
          <div className="empty-state-icon">
            <CreditCard className="w-full h-full" />
          </div>
          <p className="empty-state-title">
            {searchQuery || filterProperty || filterStatus ? "No payments found" : "No payments yet"}
          </p>
          <p className="empty-state-description">
            {searchQuery || filterProperty || filterStatus
              ? "Try adjusting your filters."
              : "Payments will appear here once tenants are added with payment schedules."}
          </p>
        </div>
      ) : (
        <div className="card overflow-hidden animate-slide-up stagger-3">
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>Tenant</th>
                  <th>Property / Room</th>
                  <th>Period</th>
                  <th>Amount</th>
                  <th>Due Date</th>
                  <th>Status</th>
                  <th className="text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredPayments.map((payment, i) => {
                  const status = statusConfig[payment.status];
                  const isPending = ["UPCOMING", "PENDING", "OVERDUE"].includes(payment.status);

                  return (
                    <tr
                      key={payment.id}
                      className="animate-fade-in"
                      style={{ animationDelay: `${i * 0.03}s` }}
                    >
                      <td>
                        <div className="flex items-center gap-3">
                          <div className="avatar avatar-sm avatar-primary">
                            {payment.tenant?.name?.charAt(0).toUpperCase() || "?"}
                          </div>
                          <span className="font-medium">{payment.tenant?.name || "Unknown"}</span>
                        </div>
                      </td>
                      <td>
                        <div className="text-sm">
                          <p className="font-medium">{payment.property?.name}</p>
                          <p className="text-[var(--text-muted)]">{payment.room?.name}</p>
                        </div>
                      </td>
                      <td>
                        <div className="text-sm">
                          <p>{formatDate(payment.period_start)}</p>
                          <p className="text-[var(--text-muted)]">
                            to {formatDate(payment.period_end)}
                          </p>
                        </div>
                      </td>
                      <td>
                        <span className="font-semibold">
                          {formatCurrency(payment.amount_due)}
                        </span>
                      </td>
                      <td>
                        <div className="text-sm">
                          <p>{formatDate(payment.due_date)}</p>
                          {payment.window_end_date !== payment.due_date && (
                            <p className="text-[var(--text-muted)]">
                              Grace: {formatDate(payment.window_end_date)}
                            </p>
                          )}
                        </div>
                      </td>
                      <td>
                        <span className={`badge ${status.class}`}>
                          {status.label}
                        </span>
                        {payment.paid_date && (
                          <p className="text-xs text-[var(--text-muted)] mt-1">
                            Paid: {formatDate(payment.paid_date)}
                          </p>
                        )}
                      </td>
                      <td>
                        <div className="flex items-center justify-end gap-1">
                          {isPending && (
                            <>
                              <button
                                onClick={() => setMarkPaidPayment(payment)}
                                className="btn btn-sm btn-ghost text-[var(--success)]"
                                title="Mark as Paid"
                              >
                                <CheckCircle className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => setWaivePayment(payment)}
                                className="btn btn-sm btn-ghost text-[var(--text-muted)]"
                                title="Waive Payment"
                              >
                                <Ban className="w-4 h-4" />
                              </button>
                              {payment.status === "OVERDUE" && (
                                <button
                                  onClick={() => setSendReminderPayment(payment)}
                                  className="btn btn-sm btn-ghost text-[var(--warning)]"
                                  title="Send Reminder"
                                >
                                  <Send className="w-4 h-4" />
                                </button>
                              )}
                            </>
                          )}
                          {payment.payment_reference && (
                            <span
                              className="text-xs text-[var(--text-muted)] ml-2"
                              title={`Ref: ${payment.payment_reference}`}
                            >
                              <Receipt className="w-4 h-4" />
                            </span>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Mark Paid Modal */}
      {markPaidPayment && (
        <MarkPaidModal
          payment={markPaidPayment}
          onClose={() => setMarkPaidPayment(null)}
          onSave={loadData}
        />
      )}

      {/* Waive Payment Modal */}
      {waivePayment && (
        <WaiveModal
          payment={waivePayment}
          onClose={() => setWaivePayment(null)}
          onSave={loadData}
        />
      )}

      {/* Send Reminder Modal */}
      {sendReminderPayment && (
        <SendReminderModal
          payment={sendReminderPayment}
          onClose={() => setSendReminderPayment(null)}
        />
      )}
    </div>
  );
}

function MarkPaidModal({
  payment,
  onClose,
  onSave,
}: {
  payment: PaymentWithTenant;
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
      onClose();
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

            {/* Payment Summary */}
            <div className="p-4 bg-[var(--surface-inset)] rounded-xl mb-6">
              <div className="flex items-center gap-3 mb-3">
                <div className="avatar avatar-md avatar-primary">
                  {payment.tenant?.name?.charAt(0).toUpperCase() || "?"}
                </div>
                <div>
                  <p className="font-semibold">{payment.tenant?.name}</p>
                  <p className="text-sm text-[var(--text-muted)]">
                    {payment.property?.name} — {payment.room?.name}
                  </p>
                </div>
              </div>
              <div className="flex items-center justify-between pt-3 border-t border-[var(--border)]">
                <span className="text-[var(--text-secondary)]">Amount Due</span>
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
                  placeholder="e.g., Bank transfer #12345, Check #789"
                  required
                />
                <p className="text-xs text-[var(--text-muted)] mt-1">
                  Enter the bank transfer reference or receipt number
                </p>
              </div>

              <div>
                <label className="label">
                  Notes <span className="text-[var(--text-muted)]">(optional)</span>
                </label>
                <textarea
                  value={formData.notes}
                  onChange={(e) => setFormData((prev) => ({ ...prev, notes: e.target.value }))}
                  className="input min-h-[80px]"
                  placeholder="Any additional notes..."
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

function WaiveModal({
  payment,
  onClose,
  onSave,
}: {
  payment: PaymentWithTenant;
  onClose: () => void;
  onSave: () => void;
}) {
  const [reason, setReason] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason.trim()) {
      setError("Please provide a reason for waiving this payment");
      return;
    }

    setError("");
    setIsLoading(true);

    try {
      await api.waivePayment(payment.id, reason);
      onSave();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to waive payment");
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
            Waive Payment
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
                  <p className="font-medium text-[var(--warning)]">This action cannot be undone</p>
                  <p className="text-sm text-[var(--text-secondary)] mt-1">
                    Waiving this payment will mark it as not required. The{" "}
                    <strong>{formatCurrency(payment.amount_due)}</strong> will not be collected.
                  </p>
                </div>
              </div>
            </div>

            <div>
              <label className="label">
                Reason for Waiving <span className="text-[var(--error)]">*</span>
              </label>
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                className="input min-h-[100px]"
                placeholder="e.g., First month free promotion, maintenance compensation..."
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
                  Waiving...
                </>
              ) : (
                <>
                  <Ban className="w-4 h-4" />
                  Waive Payment
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function SendReminderModal({
  payment,
  onClose,
}: {
  payment: PaymentWithTenant;
  onClose: () => void;
}) {
  const [method, setMethod] = useState<"email" | "sms" | "both">("email");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<{ success: boolean; message: string } | null>(null);

  const handleSend = async () => {
    setIsLoading(true);
    setResult(null);

    try {
      const res = await api.sendPaymentReminder(payment.id, method);
      setResult({ success: true, message: res.message });
    } catch (err) {
      setResult({
        success: false,
        message: err instanceof Error ? err.message : "Failed to send reminder",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const hasEmail = !!payment.tenant?.email;
  const hasPhone = !!payment.tenant?.phone;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header flex items-center justify-between">
          <h2 className="text-xl font-semibold" style={{ fontFamily: "var(--font-outfit)" }}>
            Send Payment Reminder
          </h2>
          <button onClick={onClose} className="btn btn-ghost p-2">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="modal-body">
          {result ? (
            <div
              className={`p-4 rounded-xl ${
                result.success ? "bg-[var(--success-light)]" : "bg-[var(--error-light)]"
              }`}
            >
              <p
                className={`font-medium ${
                  result.success ? "text-[var(--success)]" : "text-[var(--error)]"
                }`}
              >
                {result.message}
              </p>
            </div>
          ) : (
            <>
              <p className="text-[var(--text-secondary)] mb-6">
                Send a payment reminder to <strong>{payment.tenant?.name}</strong> for the overdue
                payment.
              </p>

              <div className="space-y-3">
                <label className="label">Notification Method</label>

                <label
                  className={`flex items-center gap-3 p-4 rounded-xl border cursor-pointer transition-all ${
                    method === "email"
                      ? "border-[var(--primary-500)] bg-[var(--primary-50)]"
                      : "border-[var(--border)] hover:border-[var(--border-strong)]"
                  } ${!hasEmail ? "opacity-50 cursor-not-allowed" : ""}`}
                >
                  <input
                    type="radio"
                    name="method"
                    value="email"
                    checked={method === "email"}
                    onChange={() => setMethod("email")}
                    disabled={!hasEmail}
                    className="sr-only"
                  />
                  <div
                    className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                      method === "email"
                        ? "border-[var(--primary-500)]"
                        : "border-[var(--border-strong)]"
                    }`}
                  >
                    {method === "email" && (
                      <div className="w-2.5 h-2.5 rounded-full bg-[var(--primary-500)]" />
                    )}
                  </div>
                  <div className="flex-1">
                    <p className="font-medium">Email</p>
                    <p className="text-sm text-[var(--text-muted)]">
                      {hasEmail ? payment.tenant?.email : "No email on file"}
                    </p>
                  </div>
                </label>

                <label
                  className={`flex items-center gap-3 p-4 rounded-xl border cursor-pointer transition-all ${
                    method === "sms"
                      ? "border-[var(--primary-500)] bg-[var(--primary-50)]"
                      : "border-[var(--border)] hover:border-[var(--border-strong)]"
                  } ${!hasPhone ? "opacity-50 cursor-not-allowed" : ""}`}
                >
                  <input
                    type="radio"
                    name="method"
                    value="sms"
                    checked={method === "sms"}
                    onChange={() => setMethod("sms")}
                    disabled={!hasPhone}
                    className="sr-only"
                  />
                  <div
                    className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                      method === "sms"
                        ? "border-[var(--primary-500)]"
                        : "border-[var(--border-strong)]"
                    }`}
                  >
                    {method === "sms" && (
                      <div className="w-2.5 h-2.5 rounded-full bg-[var(--primary-500)]" />
                    )}
                  </div>
                  <div className="flex-1">
                    <p className="font-medium">SMS</p>
                    <p className="text-sm text-[var(--text-muted)]">
                      {hasPhone ? payment.tenant?.phone : "No phone on file"}
                    </p>
                  </div>
                </label>

                <label
                  className={`flex items-center gap-3 p-4 rounded-xl border cursor-pointer transition-all ${
                    method === "both"
                      ? "border-[var(--primary-500)] bg-[var(--primary-50)]"
                      : "border-[var(--border)] hover:border-[var(--border-strong)]"
                  } ${!hasEmail || !hasPhone ? "opacity-50 cursor-not-allowed" : ""}`}
                >
                  <input
                    type="radio"
                    name="method"
                    value="both"
                    checked={method === "both"}
                    onChange={() => setMethod("both")}
                    disabled={!hasEmail || !hasPhone}
                    className="sr-only"
                  />
                  <div
                    className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                      method === "both"
                        ? "border-[var(--primary-500)]"
                        : "border-[var(--border-strong)]"
                    }`}
                  >
                    {method === "both" && (
                      <div className="w-2.5 h-2.5 rounded-full bg-[var(--primary-500)]" />
                    )}
                  </div>
                  <div className="flex-1">
                    <p className="font-medium">Both Email & SMS</p>
                    <p className="text-sm text-[var(--text-muted)]">Send via all channels</p>
                  </div>
                </label>
              </div>
            </>
          )}
        </div>

        <div className="modal-footer">
          <button onClick={onClose} className="btn btn-secondary">
            {result ? "Close" : "Cancel"}
          </button>
          {!result && (
            <button onClick={handleSend} disabled={isLoading} className="btn btn-primary">
              {isLoading ? (
                <>
                  <div className="spinner" />
                  Sending...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  Send Reminder
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
