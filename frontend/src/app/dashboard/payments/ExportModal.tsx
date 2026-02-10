"use client";

import { useState } from "react";
import api, { PropertyWithStats, TenantWithDetails } from "@/lib/api";
import {
  Download,
  FileSpreadsheet,
  FileText,
  Calendar,
  Filter,
  X,
  Building2,
  User,
  CheckCircle,
  AlertCircle,
} from "lucide-react";

interface ExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  properties: PropertyWithStats[];
  tenants: TenantWithDetails[];
}

export default function ExportModal({
  isOpen,
  onClose,
  properties,
  tenants,
}: ExportModalProps) {
  const [format, setFormat] = useState<"excel" | "pdf">("excel");
  const [startDate, setStartDate] = useState<string>(() => {
    const now = new Date();
    return `${now.getFullYear()}-01-01`;
  });
  const [endDate, setEndDate] = useState<string>(() => {
    const now = new Date();
    return `${now.getFullYear()}-12-31`;
  });
  const [propertyId, setPropertyId] = useState<string>("");
  const [tenantId, setTenantId] = useState<string>("");
  const [selectedStatuses, setSelectedStatuses] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const statuses = [
    { value: "ON_TIME", label: "Paid On Time", color: "success" },
    { value: "LATE", label: "Paid Late", color: "warning" },
    { value: "PENDING", label: "Pending", color: "warning" },
    { value: "OVERDUE", label: "Overdue", color: "error" },
    { value: "WAIVED", label: "Waived", color: "neutral" },
  ];

  const handleQuickSelect = (type: string) => {
    const now = new Date();
    switch (type) {
      case "this_year":
        setStartDate(`${now.getFullYear()}-01-01`);
        setEndDate(`${now.getFullYear()}-12-31`);
        break;
      case "last_year":
        setStartDate(`${now.getFullYear() - 1}-01-01`);
        setEndDate(`${now.getFullYear() - 1}-12-31`);
        break;
      case "last_12_months":
        const lastYear = new Date(now);
        lastYear.setFullYear(lastYear.getFullYear() - 1);
        setStartDate(lastYear.toISOString().split("T")[0]);
        setEndDate(now.toISOString().split("T")[0]);
        break;
    }
  };

  const toggleStatus = (status: string) => {
    setSelectedStatuses((prev) =>
      prev.includes(status)
        ? prev.filter((s) => s !== status)
        : [...prev, status]
    );
  };

  const handleExport = async () => {
    setError("");

    // Validate date range (max 2 years)
    const start = new Date(startDate);
    const end = new Date(endDate);
    const diffTime = Math.abs(end.getTime() - start.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays > 730) {
      setError("Date range cannot exceed 2 years");
      return;
    }

    if (start > end) {
      setError("Start date must be before end date");
      return;
    }

    setIsLoading(true);

    try {
      const blob = await api.exportPayments({
        format,
        start_date: startDate,
        end_date: endDate,
        property_id: propertyId || undefined,
        tenant_id: tenantId || undefined,
        status: selectedStatuses.join(",") || undefined,
      });

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `payments_export_${startDate}_${endDate}.${format === "excel" ? "xlsx" : "pdf"}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="card max-w-2xl w-full max-h-[90vh] overflow-y-auto animate-slide-up">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-[var(--border)]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[var(--primary-100)] flex items-center justify-center">
              <Download className="w-5 h-5 text-[var(--primary-600)]" />
            </div>
            <div>
              <h2 className="text-xl font-semibold" style={{ fontFamily: "var(--font-outfit)" }}>
                Export Payments
              </h2>
              <p className="text-sm text-[var(--text-muted)]">
                Download payment history for tax/accounting
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="btn btn-ghost p-2"
            disabled={isLoading}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {error && (
            <div className="p-3 bg-[var(--error-light)] text-[var(--error)] rounded-lg text-sm flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              {error}
            </div>
          )}

          {/* Format Selection */}
          <div>
            <label className="label mb-2">Export Format</label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setFormat("excel")}
                className={`p-4 rounded-xl border-2 flex items-center gap-3 transition-all ${
                  format === "excel"
                    ? "border-[var(--primary-500)] bg-[var(--primary-50)]"
                    : "border-[var(--border)] hover:border-[var(--primary-300)]"
                }`}
              >
                <FileSpreadsheet
                  className={`w-6 h-6 ${
                    format === "excel" ? "text-[var(--primary-600)]" : "text-[var(--text-muted)]"
                  }`}
                />
                <div className="text-left">
                  <p className="font-medium">Excel</p>
                  <p className="text-xs text-[var(--text-muted)]">.xlsx format</p>
                </div>
              </button>

              <button
                type="button"
                onClick={() => setFormat("pdf")}
                className={`p-4 rounded-xl border-2 flex items-center gap-3 transition-all ${
                  format === "pdf"
                    ? "border-[var(--primary-500)] bg-[var(--primary-50)]"
                    : "border-[var(--border)] hover:border-[var(--primary-300)]"
                }`}
              >
                <FileText
                  className={`w-6 h-6 ${
                    format === "pdf" ? "text-[var(--primary-600)]" : "text-[var(--text-muted)]"
                  }`}
                />
                <div className="text-left">
                  <p className="font-medium">PDF</p>
                  <p className="text-xs text-[var(--text-muted)]">.pdf format</p>
                </div>
              </button>
            </div>
          </div>

          {/* Date Range */}
          <div>
            <label className="label mb-2">Date Range</label>
            <div className="flex flex-wrap gap-2 mb-3">
              <button
                type="button"
                onClick={() => handleQuickSelect("this_year")}
                className="btn btn-sm btn-secondary"
              >
                This Year
              </button>
              <button
                type="button"
                onClick={() => handleQuickSelect("last_year")}
                className="btn btn-sm btn-secondary"
              >
                Last Year
              </button>
              <button
                type="button"
                onClick={() => handleQuickSelect("last_12_months")}
                className="btn btn-sm btn-secondary"
              >
                Last 12 Months
              </button>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-[var(--text-muted)] mb-1 block">Start Date</label>
                <div className="relative">
                  <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
                  <input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="input pl-10"
                  />
                </div>
              </div>
              <div>
                <label className="text-xs text-[var(--text-muted)] mb-1 block">End Date</label>
                <div className="relative">
                  <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
                  <input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="input pl-10"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Filters */}
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-[var(--text-muted)]" />
              <span className="font-medium">Filters</span>
            </div>

            {/* Property Filter */}
            <div>
              <label className="text-sm text-[var(--text-muted)] mb-1 block">Property</label>
              <div className="relative">
                <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
                <select
                  value={propertyId}
                  onChange={(e) => setPropertyId(e.target.value)}
                  className="input pl-10 appearance-none cursor-pointer"
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

            {/* Tenant Filter */}
            <div>
              <label className="text-sm text-[var(--text-muted)] mb-1 block">Tenant</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
                <select
                  value={tenantId}
                  onChange={(e) => setTenantId(e.target.value)}
                  className="input pl-10 appearance-none cursor-pointer"
                >
                  <option value="">All Tenants</option>
                  {tenants.map((tenant) => (
                    <option key={tenant.id} value={tenant.id}>
                      {tenant.name} - {tenant.property.name} ({tenant.room.name})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Status Filter */}
            <div>
              <label className="text-sm text-[var(--text-muted)] mb-2 block">
                Payment Status (select multiple)
              </label>
              <div className="flex flex-wrap gap-2">
                {statuses.map((status) => {
                  const isSelected = selectedStatuses.includes(status.value);
                  return (
                    <button
                      key={status.value}
                      type="button"
                      onClick={() => toggleStatus(status.value)}
                      className={`px-3 py-1.5 rounded-lg text-sm border transition-all flex items-center gap-1.5 ${
                        isSelected
                          ? `border-[var(--${status.color})] bg-[var(--${status.color}-light)] text-[var(--${status.color})]`
                          : "border-[var(--border)] hover:border-[var(--primary-300)]"
                      }`}
                    >
                      {isSelected && <CheckCircle className="w-3.5 h-3.5" />}
                      {status.label}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Info Box */}
          <div className="p-4 bg-[var(--surface-inset)] rounded-xl text-sm text-[var(--text-secondary)]">
            <p className="flex items-start gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>
                The export will include all payment details including tenant contact information,
                payment amounts, dates, and status. Maximum date range is 2 years.
              </span>
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 p-6 border-t border-[var(--border)]">
          <button
            type="button"
            onClick={onClose}
            disabled={isLoading}
            className="btn btn-secondary"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleExport}
            disabled={isLoading}
            className="btn btn-primary"
          >
            {isLoading ? (
              <>
                <div className="spinner" />
                Generating...
              </>
            ) : (
              <>
                <Download className="w-4 h-4" />
                Export {format === "excel" ? "Excel" : "PDF"}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
