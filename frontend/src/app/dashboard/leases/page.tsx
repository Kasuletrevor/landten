"use client";

import { useCallback, useEffect, useState } from "react";
import api, {
  LeaseAgreementWithTenant,
  LeaseStatusSummary,
  PropertyWithStats,
  TenantWithDetails,
} from "@/lib/api";
import {
  FileText,
  Upload,
  CheckCircle,
  Clock,
  AlertCircle,
  Search,
  X,
  Trash2,
} from "lucide-react";

export default function LeasesPage() {
  const [leases, setLeases] = useState<LeaseAgreementWithTenant[]>([]);
  const [summary, setSummary] = useState<LeaseStatusSummary | null>(null);
  const [properties, setProperties] = useState<PropertyWithStats[]>([]);
  const [tenants, setTenants] = useState<TenantWithDetails[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Filters
  const [filterProperty, setFilterProperty] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  // Modals
  const [uploadLease, setUploadLease] = useState<TenantWithDetails | null>(null);
  const [uploadSigned, setUploadSigned] = useState<LeaseAgreementWithTenant | null>(null);
  const [deleteLease, setDeleteLease] = useState<LeaseAgreementWithTenant | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [leasesRes, summaryRes, propertiesRes, tenantsRes] = await Promise.all([
        api.getLeases({
          property_id: filterProperty || undefined,
          status: filterStatus || undefined,
        }),
        api.getLeaseSummary(),
        api.getProperties(),
        api.getTenants({ active_only: true }),
      ]);
      setLeases(leasesRes.leases);
      setSummary(summaryRes);
      setProperties(propertiesRes.properties);
      setTenants(tenantsRes.tenants);
    } catch (error) {
      console.error("Failed to load leases:", error);
    } finally {
      setIsLoading(false);
    }
  }, [filterProperty, filterStatus]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const filteredLeases = leases.filter(
    (lease) =>
      lease.tenant_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      lease.property_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      lease.room_name?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const formatCurrency = (amount: number) => {
    if (!amount) return "-";
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
    }).format(amount);
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return "-";
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const openLeaseUrl = (url?: string) => {
    if (!url) return;
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
    window.open(`${apiBase}${url}`, "_blank");
  };

  const statusConfig = {
    UNSIGNED: { class: "badge-warning", label: "Awaiting Signature", icon: Clock },
    SIGNED: { class: "badge-success", label: "Signed", icon: CheckCircle },
  };

  const tenantsWithoutLease = tenants.filter(
    (tenant) => !leases.some((lease) => lease.tenant_id === tenant.id)
  );

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
            Lease Agreements
          </h1>
          <p className="page-subtitle">Manage tenant lease documents.</p>
        </div>
      </div>

      {/* Summary Stats */}
      {summary && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {[
            {
              label: "Total Leases",
              value: summary.total,
              icon: FileText,
              color: "primary",
            },
            {
              label: "Signed",
              value: summary.total_signed,
              icon: CheckCircle,
              color: "success",
            },
            {
              label: "Awaiting Signature",
              value: summary.total_unsigned,
              icon: Clock,
              color: "warning",
            },
            {
              label: "Without Lease",
              value: tenantsWithoutLease.length,
              icon: AlertCircle,
              color: "error",
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
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Quick Actions - Tenants Without Lease */}
      {tenantsWithoutLease.length > 0 && (
        <div className="card p-4 mb-6 animate-slide-up stagger-1 bg-[var(--warning-light)] border-[var(--warning)]">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
            <div className="flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-[var(--warning)]" />
              <span className="font-medium">
                {tenantsWithoutLease.length} tenant{tenantsWithoutLease.length !== 1 ? "s" : ""} without lease agreement
              </span>
            </div>
            <div className="flex flex-wrap gap-2 w-full lg:w-auto">
              {tenantsWithoutLease.slice(0, 3).map((tenant) => (
                <button
                  key={tenant.id}
                  onClick={() => setUploadLease(tenant)}
                  className="btn btn-sm btn-primary min-h-11 w-full sm:w-auto"
                >
                  <Upload className="w-4 h-4" />
                  Upload for {tenant.name}
                </button>
              ))}
              {tenantsWithoutLease.length > 3 && (
                <span className="text-sm text-[var(--text-muted)] self-center w-full lg:w-auto">
                  +{tenantsWithoutLease.length - 3} more
                </span>
              )}
            </div>
          </div>
        </div>
      )}

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
                <option value="UNSIGNED">Awaiting Signature</option>
                <option value="SIGNED">Signed</option>
              </select>
            </div>
          </div>

          {/* Clear Filters */}
          {(filterProperty || filterStatus || searchQuery) && (
            <button
              onClick={() => {
                setFilterProperty("");
                setFilterStatus("");
                setSearchQuery("");
              }}
              className="btn btn-ghost text-sm w-full sm:w-auto min-h-11"
            >
              <X className="w-4 h-4" />
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Leases Table */}
      {filteredLeases.length === 0 ? (
        <div className="card empty-state animate-slide-up stagger-3">
          <div className="empty-state-icon">
            <FileText className="w-full h-full" />
          </div>
          <p className="empty-state-title">
            {searchQuery || filterProperty || filterStatus
              ? "No leases found"
              : "No lease agreements yet"}
          </p>
          <p className="empty-state-description">
            {searchQuery || filterProperty || filterStatus
              ? "Try adjusting your filters."
              : "Upload lease agreements for your tenants to track them here."}
          </p>
        </div>
      ) : (
        <div className="card overflow-hidden animate-slide-up stagger-3">
          <div className="md:hidden divide-y divide-[var(--border)]">
            {filteredLeases.map((lease, i) => {
              const status = statusConfig[lease.status];
              return (
                <div
                  key={lease.id}
                  className="p-4 space-y-3 animate-fade-in"
                  style={{ animationDelay: `${i * 0.03}s` }}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="font-semibold truncate">{lease.tenant_name || "Unknown"}</p>
                      <p className="text-xs text-[var(--text-muted)] truncate">
                        {lease.property_name} • {lease.room_name}
                      </p>
                    </div>
                    <span className={`badge ${status.class} flex-shrink-0`}>
                      <status.icon className="w-3 h-3 inline mr-1" />
                      {status.label}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <p className="text-[var(--text-muted)] text-xs">Lease Start</p>
                      <p>{formatDate(lease.start_date)}</p>
                    </div>
                    <div>
                      <p className="text-[var(--text-muted)] text-xs">Lease End</p>
                      <p>{formatDate(lease.end_date)}</p>
                    </div>
                    <div>
                      <p className="text-[var(--text-muted)] text-xs">Rent</p>
                      <p className="font-semibold">
                        {lease.rent_amount != null ? formatCurrency(lease.rent_amount) : "-"}
                      </p>
                    </div>
                    <div>
                      <p className="text-[var(--text-muted)] text-xs">Uploaded By</p>
                      <p>{lease.uploaded_by_landlord ? "Landlord" : "Tenant"}</p>
                    </div>
                  </div>

                  {lease.signed_uploaded_by && (
                    <p className="text-xs text-[var(--text-muted)]">
                      Signed by: {lease.signed_uploaded_by}
                    </p>
                  )}

                  <div className="grid grid-cols-2 gap-2 pt-1">
                    <button
                      onClick={() => openLeaseUrl(lease.original_url)}
                      className="btn btn-secondary min-h-11"
                      title="View Original"
                    >
                      <FileText className="w-4 h-4" />
                      Original
                    </button>
                    {lease.status === "UNSIGNED" ? (
                      <button
                        onClick={() => setUploadSigned(lease)}
                        className="btn btn-primary min-h-11"
                        title="Upload Signed Copy"
                      >
                        <Upload className="w-4 h-4" />
                        Upload Signed
                      </button>
                    ) : (
                      <button
                        onClick={() => openLeaseUrl(lease.signed_url)}
                        className="btn btn-secondary min-h-11"
                        title="View Signed"
                        disabled={!lease.signed_url}
                      >
                        <CheckCircle className="w-4 h-4" />
                        Signed Copy
                      </button>
                    )}
                    <button
                      onClick={() => setDeleteLease(lease)}
                      className="btn btn-danger min-h-11 col-span-2"
                      title="Delete lease"
                    >
                      <Trash2 className="w-4 h-4" />
                      Delete Lease
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
                  <th>Lease Period</th>
                  <th>Rent Amount</th>
                  <th>Status</th>
                  <th>Uploaded By</th>
                  <th className="text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredLeases.map((lease, i) => {
                  const status = statusConfig[lease.status];

                  return (
                    <tr
                      key={lease.id}
                      className="animate-fade-in"
                      style={{ animationDelay: `${i * 0.03}s` }}
                    >
                      <td>
                        <div className="flex items-center gap-3">
                          <div className="avatar avatar-sm avatar-primary">
                            {lease.tenant_name?.charAt(0).toUpperCase() || "?"}
                          </div>
                          <div>
                            <span className="font-medium">{lease.tenant_name || "Unknown"}</span>
                            {lease.tenant_email && (
                              <p className="text-xs text-[var(--text-muted)]">{lease.tenant_email}</p>
                            )}
                          </div>
                        </div>
                      </td>
                      <td>
                        <div className="text-sm">
                          <p className="font-medium">{lease.property_name}</p>
                          <p className="text-[var(--text-muted)]">{lease.room_name}</p>
                        </div>
                      </td>
                      <td>
                        <div className="text-sm">
                          <p>{formatDate(lease.start_date)}</p>
                          {lease.end_date && (
                            <p className="text-[var(--text-muted)]">to {formatDate(lease.end_date)}</p>
                          )}
                        </div>
                      </td>
                      <td>
                        <span className="font-semibold">
                          {lease.rent_amount != null ? formatCurrency(lease.rent_amount) : "-"}
                        </span>
                      </td>
                      <td>
                        <span className={`badge ${status.class}`}>
                          <status.icon className="w-3 h-3 inline mr-1" />
                          {status.label}
                        </span>
                        {lease.signed_uploaded_by && (
                          <p className="text-xs text-[var(--text-muted)] mt-1">
                            Signed by: {lease.signed_uploaded_by}
                          </p>
                        )}
                      </td>
                      <td>
                        <span className="text-sm text-[var(--text-muted)]">
                          {lease.uploaded_by_landlord ? "Landlord" : "Tenant"}
                        </span>
                      </td>
                      <td>
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => openLeaseUrl(lease.original_url)}
                            className="btn btn-sm btn-ghost min-h-11 min-w-11"
                            title="View Original"
                          >
                            <FileText className="w-4 h-4" />
                          </button>
                          {lease.status === "UNSIGNED" && (
                              <button
                                onClick={() => setUploadSigned(lease)}
                                className="btn btn-sm btn-ghost text-[var(--success)] min-h-11 min-w-11"
                                title="Upload Signed Copy"
                              >
                                <Upload className="w-4 h-4" />
                            </button>
                          )}
                          {lease.signed_url && (
                              <button
                                onClick={() => openLeaseUrl(lease.signed_url)}
                                className="btn btn-sm btn-ghost text-[var(--success)] min-h-11 min-w-11"
                                title="View Signed"
                              >
                                <CheckCircle className="w-4 h-4" />
                            </button>
                          )}
                          <button
                            onClick={() => setDeleteLease(lease)}
                            className="btn btn-sm btn-ghost text-[var(--error)] min-h-11 min-w-11"
                            title="Delete"
                          >
                            <Trash2 className="w-4 h-4" />
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

      {/* Upload Original Modal */}
      {uploadLease && (
        <UploadLeaseModal
          tenant={uploadLease}
          onClose={() => setUploadLease(null)}
          onSuccess={loadData}
        />
      )}

      {/* Upload Signed Modal */}
      {uploadSigned && (
        <UploadSignedModal
          lease={uploadSigned}
          onClose={() => setUploadSigned(null)}
          onSuccess={loadData}
        />
      )}

      {/* Delete Confirmation Modal */}
      {deleteLease && (
        <DeleteLeaseModal
          lease={deleteLease}
          onClose={() => setDeleteLease(null)}
          onSuccess={loadData}
        />
      )}
    </div>
  );
}

function UploadLeaseModal({
  tenant,
  onClose,
  onSuccess,
}: {
  tenant: TenantWithDetails;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [formData, setFormData] = useState({
    start_date: "",
    end_date: "",
    rent_amount: "",
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("Please select a PDF file");
      return;
    }

    setError("");
    setIsLoading(true);

    try {
      await api.uploadLeaseDocument(tenant.id, file, {
        start_date: formData.start_date || undefined,
        end_date: formData.end_date || undefined,
        rent_amount: formData.rent_amount ? parseFloat(formData.rent_amount) : undefined,
      });
      onSuccess();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to upload lease");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header flex items-center justify-between">
          <h2 className="text-xl font-semibold" style={{ fontFamily: "var(--font-outfit)" }}>
            Upload Lease Agreement
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

            {/* Tenant Info */}
            <div className="p-4 bg-[var(--surface-inset)] rounded-xl mb-6">
              <div className="flex items-center gap-3">
                <div className="avatar avatar-md avatar-primary">
                  {tenant.name.charAt(0).toUpperCase()}
                </div>
                <div>
                  <p className="font-semibold">{tenant.name}</p>
                  <p className="text-sm text-[var(--text-muted)]">
                    {tenant.property.name} — {tenant.room.name}
                  </p>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              {/* File Upload */}
              <div>
                <label className="label">
                  Lease Document (PDF) <span className="text-[var(--error)]">*</span>
                </label>
                <input
                  type="file"
                  accept="application/pdf"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="input"
                  required
                />
                <p className="text-xs text-[var(--text-muted)] mt-1">
                  Upload the lease agreement PDF document
                </p>
              </div>

              {/* Start Date */}
              <div>
                <label className="label">Start Date</label>
                <input
                  type="date"
                  value={formData.start_date}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, start_date: e.target.value }))
                  }
                  className="input"
                />
              </div>

              {/* End Date */}
              <div>
                <label className="label">End Date</label>
                <input
                  type="date"
                  value={formData.end_date}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, end_date: e.target.value }))
                  }
                  className="input"
                />
              </div>

              {/* Rent Amount */}
              <div>
                <label className="label">Rent Amount</label>
                <input
                  type="number"
                  value={formData.rent_amount}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, rent_amount: e.target.value }))
                  }
                  className="input"
                  placeholder="e.g., 150000"
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
                  Uploading...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" />
                  Upload Lease
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function UploadSignedModal({
  lease,
  onClose,
  onSuccess,
}: {
  lease: LeaseAgreementWithTenant;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("Please select a PDF file");
      return;
    }

    setError("");
    setIsLoading(true);

    try {
      await api.uploadSignedLease(lease.id, file);
      onSuccess();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to upload signed lease");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header flex items-center justify-between">
          <h2 className="text-xl font-semibold" style={{ fontFamily: "var(--font-outfit)" }}>
            Upload Signed Lease
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

            {/* Tenant Info */}
            <div className="p-4 bg-[var(--surface-inset)] rounded-xl mb-6">
              <div className="flex items-center gap-3">
                <div className="avatar avatar-md avatar-primary">
                  {lease.tenant_name?.charAt(0).toUpperCase() || "?"}
                </div>
                <div>
                  <p className="font-semibold">{lease.tenant_name}</p>
                  <p className="text-sm text-[var(--text-muted)]">
                    {lease.property_name} — {lease.room_name}
                  </p>
                </div>
              </div>
            </div>

            <div>
              <label className="label">
                Signed Lease Document (PDF) <span className="text-[var(--error)]">*</span>
              </label>
              <input
                type="file"
                accept="application/pdf"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="input"
                required
              />
              <p className="text-xs text-[var(--text-muted)] mt-1">
                Upload the signed copy of the lease agreement
              </p>
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
                  Uploading...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" />
                  Upload Signed Copy
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function DeleteLeaseModal({
  lease,
  onClose,
  onSuccess,
}: {
  lease: LeaseAgreementWithTenant;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleDelete = async () => {
    setError("");
    setIsLoading(true);

    try {
      await api.deleteLease(lease.id);
      onSuccess();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete lease");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header flex items-center justify-between">
          <h2 className="text-xl font-semibold" style={{ fontFamily: "var(--font-outfit)" }}>
            Delete Lease Agreement
          </h2>
          <button onClick={onClose} className="btn btn-ghost p-2">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="modal-body">
          {error && (
            <div className="p-3 mb-4 bg-[var(--error-light)] text-[var(--error)] rounded-lg text-sm">
              {error}
            </div>
          )}

          <div className="p-4 bg-[var(--error-light)] rounded-xl mb-6">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-[var(--error)] flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-[var(--error)]">This action cannot be undone</p>
                <p className="text-sm text-[var(--text-secondary)] mt-1">
                  This will permanently delete the lease agreement for{" "}
                  <strong>{lease.tenant_name}</strong> and all associated files.
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <button onClick={onClose} className="btn btn-secondary">
            Cancel
          </button>
          <button onClick={handleDelete} disabled={isLoading} className="btn btn-danger">
            {isLoading ? (
              <>
                <div className="spinner" />
                Deleting...
              </>
            ) : (
              <>
                <Trash2 className="w-4 h-4" />
                Delete Lease
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
