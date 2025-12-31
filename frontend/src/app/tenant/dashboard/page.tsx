"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import api, { Payment, TenantPortalResponse, PaymentStatus } from "@/lib/api";
import ReceiptUploadModal from "./ReceiptUploadModal";
import {
  Building2,
  LogOut,
  Home,
  Clock,
  CheckCircle,
  AlertTriangle,
  CreditCard,
  Ban,
  Calendar,
  User,
  DollarSign
} from "lucide-react";

export default function TenantDashboardPage() {
  const router = useRouter();
  const [tenant, setTenant] = useState<TenantPortalResponse | null>(null);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [summary, setSummary] = useState({
    total_payments: 0,
    pending: 0,
    overdue: 0,
    paid_on_time: 0,
    paid_late: 0
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [uploadPayment, setUploadPayment] = useState<Payment | null>(null);

  useEffect(() => {
    const token = api.getToken();
    if (!token) {
      router.push("/tenant/login");
      return;
    }
    loadData();
  }, [router]);

  const loadData = async () => {
    try {
      const [profile, paymentsData] = await Promise.all([
        api.getTenantMe(),
        api.getTenantPaymentsMe()
      ]);
      setTenant(profile);
      setPayments(paymentsData.payments);
      setSummary(paymentsData.summary);
    } catch (err) {
      console.error(err);
      setError("Failed to load dashboard data. Please try logging in again.");
      // Optionally redirect to login on 401
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = () => {
    api.setToken(null);
    router.push("/tenant/login");
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
    VERIFYING: { class: "badge-info", label: "Verifying", icon: Clock },
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--background)]">
        <div className="spinner" />
      </div>
    );
  }

  if (error || !tenant) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-[var(--background)] p-4 text-center">
        <AlertTriangle className="w-12 h-12 text-[var(--error)] mb-4" />
        <h2 className="text-xl font-semibold mb-2">Error Loading Dashboard</h2>
        <p className="text-[var(--text-secondary)] mb-6">{error}</p>
        <Link href="/tenant/login" className="btn btn-secondary">
          Back to Login
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--background)]">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 h-16 bg-[var(--surface)] border-b border-[var(--border)] z-40 px-4 lg:px-8 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[var(--primary-500)] to-[var(--primary-700)] flex items-center justify-center">
            <Building2 className="w-4 h-4 text-white" />
          </div>
          <span
            className="font-semibold text-lg hidden sm:block"
            style={{ fontFamily: "var(--font-outfit)" }}
          >
            Tenant Portal
          </span>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3">
             <div className="text-right hidden sm:block">
                <p className="text-sm font-medium">{tenant.name}</p>
                <p className="text-xs text-[var(--text-muted)]">{tenant.property_name}</p>
             </div>
             <div className="w-9 h-9 rounded-full bg-[var(--primary-100)] text-[var(--primary-700)] flex items-center justify-center font-medium">
                {tenant.name.charAt(0).toUpperCase()}
             </div>
          </div>
          <button
            onClick={handleLogout}
            className="btn btn-ghost p-2 text-[var(--text-muted)] hover:text-[var(--error)]"
            title="Sign Out"
          >
            <LogOut className="w-5 h-5" />
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="pt-24 pb-12 px-4 lg:px-8 max-w-6xl mx-auto space-y-8 animate-fade-in">
        
        {/* Welcome Section */}
        <section>
          <h1 className="text-2xl font-bold mb-1" style={{ fontFamily: "var(--font-outfit)" }}>
            Welcome back, {tenant.name.split(' ')[0]}
          </h1>
          <p className="text-[var(--text-secondary)]">
            Here is an overview of your tenancy at {tenant.property_name}, {tenant.room_name}
          </p>
        </section>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
           {/* Pending/Due */}
           <div className="card p-5 flex items-center gap-4 animate-slide-up">
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${summary.pending > 0 ? "bg-[var(--warning-light)]" : "bg-[var(--surface-inset)]"}`}>
                 <Clock className={`w-6 h-6 ${summary.pending > 0 ? "text-[var(--warning)]" : "text-[var(--text-muted)]"}`} />
              </div>
              <div>
                 <p className="text-sm text-[var(--text-muted)]">Pending</p>
                 <p className="text-2xl font-bold">{summary.pending}</p>
              </div>
           </div>

           {/* Overdue */}
           <div className="card p-5 flex items-center gap-4 animate-slide-up" style={{ animationDelay: "0.05s" }}>
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${summary.overdue > 0 ? "bg-[var(--error-light)]" : "bg-[var(--surface-inset)]"}`}>
                 <AlertTriangle className={`w-6 h-6 ${summary.overdue > 0 ? "text-[var(--error)]" : "text-[var(--text-muted)]"}`} />
              </div>
              <div>
                 <p className="text-sm text-[var(--text-muted)]">Overdue</p>
                 <p className="text-2xl font-bold">{summary.overdue}</p>
              </div>
           </div>

           {/* Paid On Time */}
           <div className="card p-5 flex items-center gap-4 animate-slide-up" style={{ animationDelay: "0.1s" }}>
              <div className="w-12 h-12 rounded-xl bg-[var(--success-light)] flex items-center justify-center">
                 <CheckCircle className="w-6 h-6 text-[var(--success)]" />
              </div>
              <div>
                 <p className="text-sm text-[var(--text-muted)]">Paid</p>
                 <p className="text-2xl font-bold">{summary.paid_on_time + summary.paid_late}</p>
              </div>
           </div>

           {/* Property Info */}
           <div className="card p-5 flex items-center gap-4 animate-slide-up" style={{ animationDelay: "0.15s" }}>
              <div className="w-12 h-12 rounded-xl bg-[var(--primary-100)] flex items-center justify-center">
                 <Home className="w-6 h-6 text-[var(--primary-700)]" />
              </div>
              <div className="min-w-0">
                 <p className="text-sm text-[var(--text-muted)]">Room</p>
                 <p className="text-lg font-bold truncate">{tenant.room_name}</p>
              </div>
           </div>
        </div>

        {/* Payment History */}
        <section className="space-y-4 animate-slide-up stagger-2">
           <h2 className="text-xl font-semibold flex items-center gap-2" style={{ fontFamily: "var(--font-outfit)" }}>
              <CreditCard className="w-5 h-5 text-[var(--text-muted)]" />
              Payment History
           </h2>

           <div className="card overflow-hidden">
             {payments.length === 0 ? (
                <div className="p-12 text-center">
                   <div className="w-16 h-16 bg-[var(--surface-inset)] rounded-full flex items-center justify-center mx-auto mb-4">
                      <CreditCard className="w-8 h-8 text-[var(--text-muted)] opacity-50" />
                   </div>
                   <h3 className="text-lg font-medium mb-1">No Payments Yet</h3>
                   <p className="text-[var(--text-secondary)]">Your payment history will appear here once recorded.</p>
                </div>
             ) : (
                <div className="divide-y divide-[var(--border)]">
                   {payments.map((payment) => {
                      const status = statusConfig[payment.status];
                      return (
                         <div key={payment.id} className="p-4 sm:p-6 hover:bg-[var(--surface-inset)] transition-colors">
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                               <div className="flex items-start gap-4">
                                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${
                                     payment.status === "ON_TIME" || payment.status === "LATE"
                                       ? "bg-[var(--success-light)]"
                                       : payment.status === "OVERDUE"
                                       ? "bg-[var(--error-light)]"
                                       : "bg-[var(--warning-light)]"
                                  }`}>
                                     <status.icon className={`w-5 h-5 ${
                                        payment.status === "ON_TIME" || payment.status === "LATE"
                                          ? "text-[var(--success)]"
                                          : payment.status === "OVERDUE"
                                          ? "text-[var(--error)]"
                                          : "text-[var(--warning)]"
                                     }`} />
                                  </div>
                                  <div>
                                     <div className="flex items-center gap-2 flex-wrap">
                                        <span className="font-semibold">{formatCurrency(payment.amount_due)}</span>
                                        <span className={`badge ${status.class} text-xs`}>{status.label}</span>
                                     </div>
                                     <p className="text-sm text-[var(--text-secondary)] mt-1">
                                        For period: {formatDate(payment.period_start)} - {formatDate(payment.period_end)}
                                     </p>
                                     <div className="flex items-center gap-3 mt-1 text-xs text-[var(--text-muted)]">
                                        <span className="flex items-center gap-1">
                                           <Calendar className="w-3 h-3" />
                                           Due {formatDate(payment.due_date)}
                                        </span>
                                        {payment.paid_date && (
                                           <span className="flex items-center gap-1 text-[var(--success)]">
                                              <CheckCircle className="w-3 h-3" />
                                              Paid {formatDate(payment.paid_date)}
                                           </span>
                                        )}
                                     </div>
                                  </div>
                               </div>
                               
                               {/* Upload Receipt Action */}
                               {(payment.status === "PENDING" || payment.status === "OVERDUE" || payment.status === "UPCOMING" || payment.status === "VERIFYING") && (
                                 <button
                                   onClick={() => setUploadPayment(payment)}
                                   className={`btn btn-sm ${payment.status === "VERIFYING" ? "btn-secondary" : "btn-primary"}`}
                                 >
                                    {payment.status === "VERIFYING" ? "Update Receipt" : "Upload Receipt"}
                                 </button>
                               )}
                            </div>
                            {(payment.payment_reference || payment.notes) && (
                               <div className="mt-3 ml-14 p-3 bg-[var(--background)] rounded-lg text-sm border border-[var(--border)]">
                                  {payment.payment_reference && (
                                     <p className="text-[var(--text-secondary)]">
                                        <span className="font-medium text-[var(--text-primary)]">Ref:</span> {payment.payment_reference}
                                     </p>
                                  )}
                                  {payment.notes && (
                                     <p className="text-[var(--text-muted)] mt-1">
                                        {payment.notes}
                                     </p>
                                  )}
                               </div>
                            )}
                         </div>
                      );
                   })}
                </div>
             )}
           </div>
        </section>
      </main>

      {/* Upload Modal */}
      {uploadPayment && (
        <ReceiptUploadModal
          payment={uploadPayment}
          onClose={() => setUploadPayment(null)}
          onSuccess={(updatedPayment) => {
            setPayments(payments.map(p => p.id === updatedPayment.id ? updatedPayment : p));
            setUploadPayment(null);
            // Ideally also refresh summary
            loadData();
          }}
        />
      )}
    </div>
  );
}
