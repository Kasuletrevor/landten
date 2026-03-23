"use client";

import { useEffect, useState } from "react";
import api, {
  MaintenanceRequest,
  MaintenanceStatusValue,
  MaintenanceUrgency,
} from "@/lib/api";
import {
  Wrench,
  Search,
  X,
  MessageSquare,
  Paperclip,
  Save,
  CheckCircle,
  AlertTriangle,
  Clock,
} from "lucide-react";

const statusOptions: Array<{ value: MaintenanceStatusValue; label: string }> = [
  { value: "submitted", label: "Submitted" },
  { value: "acknowledged", label: "Acknowledged" },
  { value: "in_progress", label: "In Progress" },
  { value: "completed", label: "Completed" },
  { value: "cancelled", label: "Cancelled" },
];

const urgencyOptions: Array<{ value: MaintenanceUrgency; label: string }> = [
  { value: "emergency", label: "Emergency" },
  { value: "high", label: "High" },
  { value: "medium", label: "Medium" },
  { value: "low", label: "Low" },
];

export default function MaintenancePage() {
  const [requests, setRequests] = useState<MaintenanceRequest[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<MaintenanceStatusValue | "">("");
  const [urgencyFilter, setUrgencyFilter] = useState<MaintenanceUrgency | "">("");
  const [search, setSearch] = useState("");
  const [detail, setDetail] = useState<MaintenanceRequest | null>(null);
  const [error, setError] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  const [updateForm, setUpdateForm] = useState({
    status: "submitted" as MaintenanceStatusValue,
    assigned_to: "",
    estimated_cost: "",
    actual_cost: "",
    landlord_notes: "",
  });
  const [commentBody, setCommentBody] = useState("");
  const [commentInternal, setCommentInternal] = useState(false);
  const [commentFile, setCommentFile] = useState<File | null>(null);

  const loadRequests = async () => {
    try {
      setError("");
      const res = await api.getMaintenanceRequests({
        status: statusFilter || undefined,
        urgency: urgencyFilter || undefined,
        search: search || undefined,
      });
      setRequests(res.requests);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load requests");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadRequests();
  }, [statusFilter, urgencyFilter]);

  const refreshDetail = async (requestId: string) => {
    const item = await api.getMaintenanceRequest(requestId);
    setDetail(item);
    setUpdateForm({
      status: item.status,
      assigned_to: item.assigned_to || "",
      estimated_cost: item.estimated_cost?.toString() || "",
      actual_cost: item.actual_cost?.toString() || "",
      landlord_notes: item.landlord_notes || "",
    });
  };

  const openDetail = async (requestId: string) => {
    setError("");
    try {
      await refreshDetail(requestId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load request");
    }
  };

  const handleQuickStatusUpdate = async (
    requestId: string,
    status: MaintenanceStatusValue
  ) => {
    try {
      await api.updateMaintenanceRequest(requestId, { status });
      await loadRequests();
      if (detail?.id === requestId) {
        await refreshDetail(requestId);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update request");
    }
  };

  const handleSaveDetail = async () => {
    if (!detail) return;
    setIsSaving(true);
    setError("");
    try {
      await api.updateMaintenanceRequest(detail.id, {
        status: updateForm.status,
        assigned_to: updateForm.assigned_to || undefined,
        estimated_cost: updateForm.estimated_cost
          ? parseFloat(updateForm.estimated_cost)
          : undefined,
        actual_cost: updateForm.actual_cost
          ? parseFloat(updateForm.actual_cost)
          : undefined,
        landlord_notes: updateForm.landlord_notes || undefined,
      });
      await refreshDetail(detail.id);
      await loadRequests();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save request");
    } finally {
      setIsSaving(false);
    }
  };

  const handleAddComment = async () => {
    if (!detail) return;
    const trimmed = commentBody.trim();
    if (!trimmed && !commentFile) return;

    setIsSaving(true);
    setError("");
    try {
      if (commentFile) {
        await api.addMaintenanceAttachment(detail.id, commentFile, {
          body: trimmed || undefined,
          is_internal: commentInternal,
        });
      } else {
        await api.addMaintenanceComment(detail.id, trimmed, commentInternal);
      }
      setCommentBody("");
      setCommentFile(null);
      setCommentInternal(false);
      await refreshDetail(detail.id);
      await loadRequests();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add comment");
    } finally {
      setIsSaving(false);
    }
  };

  const getStatusBadgeClass = (status: MaintenanceStatusValue) => {
    if (status === "completed") return "badge-success";
    if (status === "cancelled") return "badge-neutral";
    if (status === "in_progress") return "badge-info";
    if (status === "acknowledged") return "badge-warning";
    return "badge-warning";
  };

  const getUrgencyClass = (urgency: MaintenanceUrgency) => {
    if (urgency === "emergency") return "badge-error";
    if (urgency === "high") return "badge-warning";
    if (urgency === "medium") return "badge-info";
    return "badge-neutral";
  };

  const filteredRequests = requests.filter((item) => {
    if (!search.trim()) return true;
    const target = `${item.title} ${item.description} ${item.tenant_name || ""} ${
      item.property_name || ""
    } ${item.room_name || ""}`.toLowerCase();
    return target.includes(search.trim().toLowerCase());
  });

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title" style={{ fontFamily: "var(--font-outfit)" }}>
            Maintenance Requests
          </h1>
          <p className="page-subtitle">
            Track tenant issues, assignments, and repair progress.
          </p>
        </div>
      </div>

      {error && (
        <div className="p-3 mb-4 bg-[var(--error-light)] text-[var(--error)] rounded-lg text-sm">
          {error}
        </div>
      )}

      <div className="card p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <div className="md:col-span-2 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input pl-10"
              placeholder="Search requests..."
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) =>
              setStatusFilter((e.target.value as MaintenanceStatusValue) || "")
            }
            className="input"
          >
            <option value="">All Statuses</option>
            {statusOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <select
            value={urgencyFilter}
            onChange={(e) =>
              setUrgencyFilter((e.target.value as MaintenanceUrgency) || "")
            }
            className="input"
          >
            <option value="">All Urgency</option>
            {urgencyOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-40">
          <div className="spinner" />
        </div>
      ) : filteredRequests.length === 0 ? (
        <div className="card empty-state">
          <div className="empty-state-icon">
            <Wrench className="w-full h-full" />
          </div>
          <p className="empty-state-title">No maintenance requests</p>
          <p className="empty-state-description">
            New tenant issues will appear here once submitted.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          {filteredRequests.map((item) => (
            <div key={item.id} className="card p-4 space-y-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="text-lg font-semibold">{item.title}</h3>
                  <p className="text-sm text-[var(--text-muted)]">
                    {item.tenant_name} • {item.property_name} / {item.room_name}
                  </p>
                </div>
                <div className="flex gap-2 flex-wrap justify-end">
                  <span className={`badge ${getStatusBadgeClass(item.status)}`}>
                    {item.status.replace("_", " ")}
                  </span>
                  <span className={`badge ${getUrgencyClass(item.urgency)}`}>
                    {item.urgency}
                  </span>
                </div>
              </div>

              <p className="text-sm text-[var(--text-secondary)]">{item.description}</p>

              <div className="flex items-center justify-between text-xs text-[var(--text-muted)]">
                <span>
                  {new Date(item.created_at).toLocaleDateString()} • {item.comments_count} comments
                </span>
                {item.assigned_to && <span>Assigned: {item.assigned_to}</span>}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                <select
                  value={item.status}
                  onChange={(e) =>
                    void handleQuickStatusUpdate(
                      item.id,
                      e.target.value as MaintenanceStatusValue
                    )
                  }
                  className="input min-h-11"
                >
                  {statusOptions.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
                <button
                  onClick={() => void openDetail(item.id)}
                  className="btn btn-secondary min-h-11"
                >
                  <MessageSquare className="w-4 h-4" />
                  Open Thread
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {detail && (
        <div className="modal-overlay" onClick={() => setDetail(null)}>
          <div className="modal max-w-3xl" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold">{detail.title}</h2>
                <p className="text-sm text-[var(--text-muted)]">
                  {detail.tenant_name} • {detail.property_name} / {detail.room_name}
                </p>
              </div>
              <button onClick={() => setDetail(null)} className="btn btn-ghost p-2">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="modal-body space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="label">Status</label>
                  <select
                    value={updateForm.status}
                    onChange={(e) =>
                      setUpdateForm((prev) => ({
                        ...prev,
                        status: e.target.value as MaintenanceStatusValue,
                      }))
                    }
                    className="input"
                  >
                    {statusOptions.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="label">Assigned To</label>
                  <input
                    value={updateForm.assigned_to}
                    onChange={(e) =>
                      setUpdateForm((prev) => ({ ...prev, assigned_to: e.target.value }))
                    }
                    className="input"
                    placeholder="Technician or contractor"
                  />
                </div>
                <div>
                  <label className="label">Estimated Cost</label>
                  <input
                    type="number"
                    value={updateForm.estimated_cost}
                    onChange={(e) =>
                      setUpdateForm((prev) => ({
                        ...prev,
                        estimated_cost: e.target.value,
                      }))
                    }
                    className="input"
                    placeholder="0"
                  />
                </div>
                <div>
                  <label className="label">Actual Cost</label>
                  <input
                    type="number"
                    value={updateForm.actual_cost}
                    onChange={(e) =>
                      setUpdateForm((prev) => ({
                        ...prev,
                        actual_cost: e.target.value,
                      }))
                    }
                    className="input"
                    placeholder="0"
                  />
                </div>
              </div>

              <div>
                <label className="label">Landlord Notes</label>
                <textarea
                  value={updateForm.landlord_notes}
                  onChange={(e) =>
                    setUpdateForm((prev) => ({ ...prev, landlord_notes: e.target.value }))
                  }
                  className="input min-h-24"
                  placeholder="Internal planning notes..."
                />
              </div>

              <button
                onClick={() => void handleSaveDetail()}
                disabled={isSaving}
                className="btn btn-primary min-h-11"
              >
                <Save className="w-4 h-4" />
                Save Request Details
              </button>

              <div className="divider" />

              <div className="space-y-3">
                <h3 className="font-semibold">Discussion Thread</h3>
                {detail.comments.length === 0 ? (
                  <p className="text-sm text-[var(--text-muted)]">
                    No comments yet.
                  </p>
                ) : (
                  <div className="space-y-2">
                    {detail.comments.map((comment) => (
                      <div
                        key={comment.id}
                        className={`p-3 rounded-lg border ${
                          comment.is_internal
                            ? "bg-[var(--surface-inset)] border-[var(--warning)]"
                            : "bg-[var(--surface)] border-[var(--border)]"
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2 mb-1">
                          <div className="flex items-center gap-2 text-xs">
                            {comment.author_type === "landlord" ? (
                              <CheckCircle className="w-3.5 h-3.5 text-[var(--success)]" />
                            ) : (
                              <Clock className="w-3.5 h-3.5 text-[var(--primary-600)]" />
                            )}
                            <span className="font-medium">{comment.author_type}</span>
                            {comment.is_internal && (
                              <span className="badge badge-warning">Internal</span>
                            )}
                          </div>
                          <span className="text-xs text-[var(--text-muted)]">
                            {new Date(comment.created_at).toLocaleString()}
                          </span>
                        </div>
                        <p className="text-sm text-[var(--text-secondary)]">{comment.body}</p>
                        {comment.attachment_url && (
                          <a
                            href={api.getPublicAssetUrl(comment.attachment_url)}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1.5 text-xs mt-2"
                          >
                            <Paperclip className="w-3.5 h-3.5" />
                            {comment.attachment_name || "Attachment"}
                          </a>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="space-y-2">
                <label className="label">Add Comment</label>
                <textarea
                  value={commentBody}
                  onChange={(e) => setCommentBody(e.target.value)}
                  className="input min-h-24"
                  placeholder="Share update with tenant..."
                />
                <div className="flex flex-col sm:flex-row gap-2 sm:items-center">
                  <label className="btn btn-secondary min-h-11">
                    <Paperclip className="w-4 h-4" />
                    {commentFile ? commentFile.name : "Attach File"}
                    <input
                      type="file"
                      className="hidden"
                      accept="image/png,image/jpeg,application/pdf"
                      onChange={(e) => setCommentFile(e.target.files?.[0] || null)}
                    />
                  </label>
                  <label className="inline-flex items-center gap-2 text-sm text-[var(--text-muted)]">
                    <input
                      type="checkbox"
                      checked={commentInternal}
                      onChange={(e) => setCommentInternal(e.target.checked)}
                    />
                    Internal note (hidden from tenant)
                  </label>
                </div>
                {commentInternal && (
                  <p className="text-xs text-[var(--warning)] flex items-center gap-1">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    Internal comments are not visible to tenants.
                  </p>
                )}
                <button
                  onClick={() => void handleAddComment()}
                  disabled={isSaving || (!commentBody.trim() && !commentFile)}
                  className="btn btn-primary min-h-11"
                >
                  <MessageSquare className="w-4 h-4" />
                  Post Comment
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
