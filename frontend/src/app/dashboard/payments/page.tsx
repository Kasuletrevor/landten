"use client";

import { useCallback, useEffect, useState } from "react";
import api, {
  PaymentWithTenant,
  PaymentSummary,
  PropertyWithStats,
  PaymentStatus,
  PaymentDispute,
} from "@/lib/api";
import {
  CreditCard,
  DollarSign,
  Clock,
  AlertTriangle,
  CheckCircle,
  Search,
  X,
  Send,
  FileSearch,
  Ban,
  Receipt,
  MessageSquare,
  Paperclip,
  Upload,
  Download,
} from "lucide-react";
import ExportModal from "./ExportModal";

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
  const [rejectPayment, setRejectPayment] = useState<PaymentWithTenant | null>(null);
  const [disputePayment, setDisputePayment] = useState<PaymentWithTenant | null>(null);
  const [exportModalOpen, setExportModalOpen] = useState(false);

  const loadData = useCallback(async () => {
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
  }, [dateRange, filterProperty, filterStatus]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const filteredPayments = payments.filter((payment) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      payment.tenant_name?.toLowerCase().includes(q) ||
      payment.property_name?.toLowerCase().includes(q) ||
      payment.room_name?.toLowerCase().includes(q)
    );
  });

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
    upcoming: { class: "badge-info", label: "Upcoming", icon: Clock },
    pending: { class: "badge-warning", label: "Pending", icon: Clock },
    on_time: { class: "badge-success", label: "Paid", icon: CheckCircle },
    late: { class: "badge-warning", label: "Late", icon: AlertTriangle },
    overdue: { class: "badge-error", label: "Overdue", icon: AlertTriangle },
    waived: { class: "badge-neutral", label: "Waived", icon: Ban },
    verifying: { class: "badge-info", label: "Verifying", icon: FileSearch },
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
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
        {[
          { label: "Upcoming", count: summary?.upcoming_count || 0, status: "upcoming" },
          { label: "Pending", count: summary?.pending_count || 0, status: "pending" },
          { label: "Overdue", count: summary?.overdue_count || 0, status: "overdue" },
          { label: "Paid", count: summary?.paid_count || 0, status: "on_time" },
        ].map((item) => (
          <button
            key={item.label}
            onClick={() => setFilterStatus(filterStatus === item.status ? "" : item.status)}
            className={`card p-4 min-h-11 text-center transition-all ${
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
                <option value="upcoming">Upcoming</option>
                <option value="pending">Pending</option>
                <option value="on_time">Paid</option>
                <option value="late">Late</option>
                <option value="overdue">Overdue</option>
                <option value="waived">Waived</option>
                <option value="verifying">Verifying</option>
              </select>
            </div>
          </div>

          {/* Date Range */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full lg:w-auto lg:min-w-[18rem]">
            <input
              type="date"
              value={dateRange.start}
              onChange={(e) => setDateRange((prev) => ({ ...prev, start: e.target.value }))}
              className="input w-full"
              placeholder="Start date"
            />
            <input
              type="date"
              value={dateRange.end}
              onChange={(e) => setDateRange((prev) => ({ ...prev, end: e.target.value }))}
              className="input w-full"
              placeholder="End date"
            />
          </div>

          {/* Export Button */}
          <button
            onClick={() => setExportModalOpen(true)}
            className="btn btn-secondary w-full sm:w-auto min-h-11"
          >
            <Download className="w-4 h-4" />
            Export
          </button>

          {/* Clear Filters */}
          {(filterProperty || filterStatus || dateRange.start || dateRange.end) && (
            <button
              onClick={() => {
                setFilterProperty("");
                setFilterStatus("");
                setDateRange({ start: "", end: "" });
              }}
              className="btn btn-ghost text-sm w-full sm:w-auto min-h-11"
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
          <div className="md:hidden divide-y divide-[var(--border)]">
            {filteredPayments.map((payment, i) => {
              const status = statusConfig[payment.status] || statusConfig.pending;
              const isPending = ["upcoming", "pending", "overdue"].includes(payment.status);

              return (
                <div
                  key={payment.id}
                  className="p-4 space-y-3 animate-fade-in"
                  style={{ animationDelay: `${i * 0.03}s` }}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="font-semibold truncate">{payment.tenant_name || "Unknown"}</p>
                      <p className="text-xs text-[var(--text-muted)] truncate">
                        {payment.property_name} • {payment.room_name}
                      </p>
                    </div>
                    <span className={`badge ${status.class} flex-shrink-0`}>{status.label}</span>
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <p className="text-[var(--text-muted)] text-xs">Amount</p>
                      <p className="font-semibold">{formatCurrency(payment.amount_due)}</p>
                    </div>
                    <div>
                      <p className="text-[var(--text-muted)] text-xs">Due Date</p>
                      <p className="font-medium">{formatDate(payment.due_date)}</p>
                    </div>
                    <div>
                      <p className="text-[var(--text-muted)] text-xs">Period</p>
                      <p className="text-xs">
                        {formatDate(payment.period_start)} - {formatDate(payment.period_end)}
                      </p>
                    </div>
                    <div>
                      <p className="text-[var(--text-muted)] text-xs">Grace Ends</p>
                      <p className="text-xs">{formatDate(payment.window_end_date)}</p>
                    </div>
                  </div>

                  {(payment.paid_date || payment.rejection_reason) && (
                    <div className="text-xs space-y-1">
                      {payment.paid_date && (
                        <p className="text-[var(--success)]">Paid: {formatDate(payment.paid_date)}</p>
                      )}
                      {payment.rejection_reason && (
                        <p className="text-[var(--error)]">
                          Rejected: {payment.rejection_reason}
                        </p>
                      )}
                    </div>
                  )}

                  <div className="grid grid-cols-2 gap-2 pt-1">
                    {isPending && (
                      <>
                        <button
                          onClick={() => setMarkPaidPayment(payment)}
                          className="btn btn-secondary min-h-11"
                          title="Mark as Paid"
                        >
                          <CheckCircle className="w-4 h-4" />
                          Mark Paid
                        </button>
                        <button
                          onClick={() => setWaivePayment(payment)}
                          className="btn btn-ghost min-h-11"
                          title="Waive Payment"
                        >
                          <Ban className="w-4 h-4" />
                          Waive
                        </button>
                        {payment.status === "overdue" && (
                          <button
                            onClick={() => setSendReminderPayment(payment)}
                            className="btn btn-ghost min-h-11 col-span-2"
                            title="Send Reminder"
                          >
                            <Send className="w-4 h-4" />
                            Send Reminder
                          </button>
                        )}
                      </>
                    )}
                    {payment.status === "verifying" && (
                      <>
                        <button
                          onClick={() => setMarkPaidPayment(payment)}
                          className="btn btn-secondary min-h-11"
                          title="Approve Receipt"
                        >
                          <CheckCircle className="w-4 h-4" />
                          Approve
                        </button>
                        <button
                          onClick={() => setRejectPayment(payment)}
                          className="btn btn-danger min-h-11"
                          title="Reject Receipt"
                        >
                          <X className="w-4 h-4" />
                          Reject
                        </button>
                      </>
                    )}
                    <button
                      onClick={() => setDisputePayment(payment)}
                      className="btn btn-primary min-h-11 col-span-2 relative justify-center"
                      title="Open payment discussion"
                    >
                      <MessageSquare className="w-4 h-4" />
                      Discuss Payment
                      {(payment.dispute_unread_count || 0) > 0 && (
                        <span className="absolute -top-1 -right-1 min-w-4 h-4 px-1 rounded-full bg-[var(--error)] text-white text-[10px] leading-4">
                          {payment.dispute_unread_count}
                        </span>
                      )}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="hidden md:block overflow-x-auto">
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
                            {payment.tenant_name?.charAt(0).toUpperCase() || "?"}
                          </div>
                          <span className="font-medium">{payment.tenant_name || "Unknown"}</span>
                        </div>
                      </td>
                      <td>
                        <div className="text-sm">
                          <p className="font-medium">{payment.property_name}</p>
                          <p className="text-[var(--text-muted)]">{payment.room_name}</p>
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
                                className="btn btn-sm btn-ghost text-[var(--success)] min-h-11 min-w-11"
                                title="Mark as Paid"
                              >
                                <CheckCircle className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => setWaivePayment(payment)}
                                className="btn btn-sm btn-ghost text-[var(--text-muted)] min-h-11 min-w-11"
                                title="Waive Payment"
                              >
                                <Ban className="w-4 h-4" />
                              </button>
                              {payment.status === "overdue" && (
                                <button
                                  onClick={() => setSendReminderPayment(payment)}
                                  className="btn btn-sm btn-ghost text-[var(--warning)] min-h-11 min-w-11"
                                  title="Send Reminder"
                                >
                                  <Send className="w-4 h-4" />
                                </button>
                              )}
                            </>
                          )}
                          {payment.status === "verifying" && (
                            <>
                              <button
                                onClick={() => setMarkPaidPayment(payment)}
                                className="btn btn-sm btn-ghost text-[var(--success)] min-h-11 min-w-11"
                                title="Approve Receipt"
                              >
                                <CheckCircle className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => setRejectPayment(payment)}
                                className="btn btn-sm btn-ghost text-[var(--error)] min-h-11 min-w-11"
                                title="Reject Receipt"
                              >
                                <X className="w-4 h-4" />
                              </button>
                            </>
                          )}
                          {payment.rejection_reason && (
                            <span
                              className="text-xs text-[var(--error)] ml-2 cursor-help"
                              title={`Rejected: ${payment.rejection_reason}`}
                            >
                              <AlertTriangle className="w-4 h-4" />
                            </span>
                          )}
                          {payment.payment_reference && (
                            <span
                              className="text-xs text-[var(--text-muted)] ml-2"
                              title={`Ref: ${payment.payment_reference}`}
                            >
                              <Receipt className="w-4 h-4" />
                            </span>
                          )}
                          <button
                            onClick={() => setDisputePayment(payment)}
                            className="btn btn-sm btn-ghost text-[var(--primary-700)] relative min-h-11 min-w-11"
                            title="Open payment discussion"
                          >
                            <MessageSquare className="w-4 h-4" />
                            {(payment.dispute_unread_count || 0) > 0 && (
                              <span className="absolute -top-1 -right-1 min-w-4 h-4 px-1 rounded-full bg-[var(--error)] text-white text-[10px] leading-4">
                                {payment.dispute_unread_count}
                              </span>
                            )}
                          </button>
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

      {/* Reject Receipt Modal */}
      {rejectPayment && (
        <RejectReceiptModal
          payment={rejectPayment}
          onClose={() => setRejectPayment(null)}
          onSave={loadData}
        />
      )}

      {disputePayment && (
        <LandlordDisputeModal
          payment={disputePayment}
          onClose={() => setDisputePayment(null)}
          onSave={loadData}
        />
      )}

      {/* Export Modal */}
      <ExportModal
        isOpen={exportModalOpen}
        onClose={() => setExportModalOpen(false)}
        properties={properties}
        tenants={Array.from(
          new Map(
            payments
              .filter((p): p is typeof p & { tenant_name: string } => !!p.tenant_name)
              .map((p) => [
                p.tenant_name,
                {
                  id: p.tenant_name,
                  name: p.tenant_name,
                  email: p.tenant_email || "",
                  phone: p.tenant_phone || "",
                  property: { id: p.property_id || "", name: p.property_name || "Unknown" },
                  room: { id: "", name: p.room_name || "Unknown" },
                  is_active: true,
                  move_in_date: "",
                  total_payments: 0,
                  total_paid: 0,
                  total_outstanding: 0,
                },
              ])
          ).values()
        )}
      />
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
                  {payment.tenant_name?.charAt(0).toUpperCase() || "?"}
                </div>
                <div>
                  <p className="font-semibold">{payment.tenant_name}</p>
                  <p className="text-sm text-[var(--text-muted)]">
                    {payment.property_name} — {payment.room_name}
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
  const method = "email" as const;
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

  const hasEmail = !!payment.tenant_email;

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
                Send a payment reminder to <strong>{payment.tenant_name}</strong> for the overdue
                payment.
              </p>

              <div className="space-y-3">
                <label className="label">Reminder Channel</label>

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
                      {hasEmail ? payment.tenant_email : "No email on file"}
                    </p>
                  </div>
                </label>

                <div className="rounded-xl border border-[var(--warning)]/20 bg-[var(--warning-light)] p-4">
                  <p className="font-medium text-[var(--warning)]">SMS is disabled</p>
                  <p className="mt-1 text-sm text-[var(--text-secondary)]">
                    Payment reminders currently send by email only until a real SMS provider is integrated.
                  </p>
                </div>
              </div>
            </>
          )}
        </div>

        <div className="modal-footer">
          <button onClick={onClose} className="btn btn-secondary">
            {result ? "Close" : "Cancel"}
          </button>
          {!result && (
            <button onClick={handleSend} disabled={isLoading || !hasEmail} className="btn btn-primary">
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

function RejectReceiptModal({
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
      setError("Please provide a reason for rejecting this receipt");
      return;
    }

    setError("");
    setIsLoading(true);

    try {
      await api.rejectReceipt(payment.id, reason);
      onSave();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reject receipt");
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
            Reject Receipt
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

            <div className="p-4 bg-[var(--error-light)] rounded-xl mb-6">
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-[var(--error)] flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-[var(--error)]">Reject uploaded receipt</p>
                  <p className="text-sm text-[var(--text-secondary)] mt-1">
                    The tenant will be notified that their receipt for{" "}
                    <strong>{formatCurrency(payment.amount_due)}</strong> was rejected and will need
                    to upload a new one.
                  </p>
                </div>
              </div>
            </div>

            <div>
              <label className="label">
                Reason for Rejection <span className="text-[var(--error)]">*</span>
              </label>
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                className="input min-h-[100px]"
                placeholder="e.g., Receipt amount doesn't match, blurry image, wrong date..."
                required
              />
              <p className="text-xs text-[var(--text-muted)] mt-1">
                This will be shown to the tenant so they know what to fix.
              </p>
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
                  Rejecting...
                </>
              ) : (
                <>
                  <X className="w-4 h-4" />
                  Reject Receipt
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function LandlordDisputeModal({
  payment,
  onClose,
  onSave,
}: {
  payment: PaymentWithTenant;
  onClose: () => void;
  onSave: () => void;
}) {
  const [thread, setThread] = useState<PaymentDispute | null>(null);
  const [message, setMessage] = useState("");
  const [attachmentNote, setAttachmentNote] = useState("");
  const [attachmentFile, setAttachmentFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [isUploadingAttachment, setIsUploadingAttachment] = useState(false);
  const [isResolving, setIsResolving] = useState(false);
  const [isReopening, setIsReopening] = useState(false);
  const [error, setError] = useState("");

  const loadThread = async () => {
    setIsLoading(true);
    setError("");
    try {
      const data = await api.getPaymentDispute(payment.id);
      setThread(data);
      onSave();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to load dispute thread";
      if (msg.toLowerCase().includes("dispute not found")) {
        setThread(null);
      } else {
        setError(msg);
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadThread();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [payment.id]);

  const isResolved = (thread?.status || "").toString().toLowerCase() === "resolved";

  const handleSend = async () => {
    const body = message.trim();
    if (!body) return;
    setIsSending(true);
    setError("");
    try {
      const updated = await api.postPaymentDisputeMessage(payment.id, body);
      setThread(updated);
      setMessage("");
      onSave();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send message");
    } finally {
      setIsSending(false);
    }
  };

  const handleAttachmentUpload = async () => {
    if (!attachmentFile) return;
    setIsUploadingAttachment(true);
    setError("");
    try {
      const updated = await api.postPaymentDisputeAttachment(
        payment.id,
        attachmentFile,
        attachmentNote || undefined
      );
      setThread(updated);
      setAttachmentFile(null);
      setAttachmentNote("");
      onSave();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to upload attachment");
    } finally {
      setIsUploadingAttachment(false);
    }
  };

  const handleResolve = async () => {
    setIsResolving(true);
    setError("");
    try {
      const updated = await api.resolvePaymentDispute(payment.id);
      setThread(updated);
      onSave();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to resolve dispute");
    } finally {
      setIsResolving(false);
    }
  };

  const handleReopen = async () => {
    setIsReopening(true);
    setError("");
    try {
      const updated = await api.reopenPaymentDispute(payment.id);
      setThread(updated);
      onSave();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reopen dispute");
    } finally {
      setIsReopening(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal max-w-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header flex items-center justify-between">
          <h2 className="text-xl font-semibold" style={{ fontFamily: "var(--font-outfit)" }}>
            Payment Discussion
          </h2>
          <button onClick={onClose} className="btn btn-ghost p-2">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="modal-body space-y-4">
          {error && (
            <div className="p-3 bg-[var(--error-light)] text-[var(--error)] rounded-lg text-sm">
              {error}
            </div>
          )}

          <div className="flex items-center justify-between gap-4">
            <p className="text-sm text-[var(--text-secondary)]">
              Status:{" "}
              <span
                className={`font-medium ${
                  isResolved ? "text-[var(--success)]" : "text-[var(--warning)]"
                }`}
              >
                {isResolved ? "Resolved" : "Open"}
              </span>
            </p>
            {thread && (
              <div className="flex items-center gap-2">
                {isResolved ? (
                  <button
                    type="button"
                    className="btn btn-sm btn-secondary"
                    onClick={handleReopen}
                    disabled={isReopening}
                  >
                    {isReopening ? "Reopening..." : "Reopen"}
                  </button>
                ) : (
                  <button
                    type="button"
                    className="btn btn-sm btn-primary"
                    onClick={handleResolve}
                    disabled={isResolving}
                  >
                    {isResolving ? "Resolving..." : "Resolve"}
                  </button>
                )}
              </div>
            )}
          </div>

          <div className="border border-[var(--border)] rounded-xl p-4 max-h-72 overflow-y-auto space-y-3 bg-[var(--surface-inset)]">
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <div className="spinner" />
              </div>
            ) : !thread || thread.messages.length === 0 ? (
              <p className="text-sm text-[var(--text-muted)]">
                No discussion yet. Add a message to start clarification with the tenant.
              </p>
            ) : (
              thread.messages.map((entry) => (
                <div key={entry.id} className="p-3 rounded-lg bg-[var(--surface)] border border-[var(--border)]">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-medium">
                      {entry.author_type === "landlord" ? "You" : payment.tenant_name || "Tenant"}
                    </p>
                    <p className="text-xs text-[var(--text-muted)]">
                      {new Date(entry.created_at).toLocaleString()}
                    </p>
                  </div>
                  <p className="text-sm text-[var(--text-secondary)] mt-1 whitespace-pre-wrap">
                    {entry.body}
                  </p>
                  {entry.attachment_url && (
                    <div className="mt-2">
                      <a
                        href={api.getPaymentDisputeAttachmentUrl(payment.id, entry.id)}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-2 text-xs text-[var(--primary-700)] hover:underline"
                      >
                        <Paperclip className="w-3.5 h-3.5" />
                        {entry.attachment_name || "View attachment"}
                      </a>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>

          <div>
            <label className="label">Message</label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              className="input min-h-[110px]"
              placeholder={
                isResolved
                  ? "This thread is resolved. Reopen it to send another message."
                  : "Explain discrepancies, references, or next action..."
              }
              disabled={isResolved || isSending}
            />
          </div>

          <div className="border border-[var(--border)] rounded-xl p-3 bg-[var(--surface)]">
            <label className="label mb-2">Attachment (optional)</label>
            <input
              type="file"
              accept=".png,.jpg,.jpeg,.pdf"
              className="input"
              onChange={(e) => setAttachmentFile(e.target.files?.[0] || null)}
              disabled={isResolved || isUploadingAttachment}
            />
            <textarea
              value={attachmentNote}
              onChange={(e) => setAttachmentNote(e.target.value)}
              className="input min-h-[72px] mt-2"
              placeholder="Optional note for this attachment..."
              disabled={isResolved || isUploadingAttachment}
            />
            <div className="mt-2 flex justify-end">
              <button
                type="button"
                onClick={handleAttachmentUpload}
                disabled={isLoading || isResolved || isUploadingAttachment || !attachmentFile}
                className="btn btn-secondary btn-sm"
              >
                {isUploadingAttachment ? (
                  <>
                    <div className="spinner" />
                    Uploading...
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4" />
                    Send Attachment
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <button type="button" onClick={onClose} className="btn btn-secondary">
            Close
          </button>
          <button
            type="button"
            onClick={handleSend}
            disabled={isLoading || isResolved || isSending || !message.trim()}
            className="btn btn-primary"
          >
            {isSending ? (
              <>
                <div className="spinner" />
                Sending...
              </>
            ) : (
              <>
                <MessageSquare className="w-4 h-4" />
                Send Message
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
