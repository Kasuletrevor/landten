"use client";

import { useEffect, useState } from "react";
import api, {
  MaintenanceCategory,
  MaintenanceRequest,
  MaintenanceStatusValue,
  MaintenanceUrgency,
} from "@/lib/api";
import {
  AlertTriangle,
  Calendar,
  CheckCircle,
  Clock,
  MessageSquare,
  Paperclip,
  Plus,
  Star,
  Wrench,
  X,
} from "lucide-react";

const categoryOptions: Array<{ value: MaintenanceCategory; label: string }> = [
  { value: "plumbing", label: "Plumbing" },
  { value: "electrical", label: "Electrical" },
  { value: "appliance", label: "Appliance" },
  { value: "structural", label: "Structural" },
  { value: "other", label: "Other" },
];

const urgencyOptions: Array<{ value: MaintenanceUrgency; label: string }> = [
  { value: "emergency", label: "Emergency" },
  { value: "high", label: "High" },
  { value: "medium", label: "Medium" },
  { value: "low", label: "Low" },
];

const statusLabel: Record<MaintenanceStatusValue, string> = {
  submitted: "Submitted",
  acknowledged: "Acknowledged",
  in_progress: "In Progress",
  completed: "Completed",
  cancelled: "Cancelled",
};

function getStatusBadgeClass(status: MaintenanceStatusValue) {
  if (status === "completed") return "badge-success";
  if (status === "cancelled") return "badge-neutral";
  if (status === "in_progress") return "badge-info";
  if (status === "acknowledged") return "badge-warning";
  return "badge-warning";
}

function getUrgencyBadgeClass(urgency: MaintenanceUrgency) {
  if (urgency === "emergency") return "badge-error";
  if (urgency === "high") return "badge-warning";
  if (urgency === "medium") return "badge-info";
  return "badge-neutral";
}

export default function TenantMaintenanceSection() {
  const [requests, setRequests] = useState<MaintenanceRequest[]>([]);
  const [selectedRequest, setSelectedRequest] = useState<MaintenanceRequest | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");

  const [commentBody, setCommentBody] = useState("");
  const [commentAttachment, setCommentAttachment] = useState<File | null>(null);

  const [resolveOpen, setResolveOpen] = useState(false);
  const [resolveRating, setResolveRating] = useState("");
  const [resolveFeedback, setResolveFeedback] = useState("");

  const [form, setForm] = useState({
    category: "other" as MaintenanceCategory,
    urgency: "medium" as MaintenanceUrgency,
    title: "",
    description: "",
    preferred_entry_time: "",
    attachment: null as File | null,
  });

  const loadRequests = async () => {
    try {
      setError("");
      const data = await api.getTenantMaintenanceRequests();
      setRequests(data.requests);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load maintenance requests");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadRequests();
  }, []);

  const openRequest = async (requestId: string) => {
    setError("");
    setIsDetailLoading(true);
    try {
      const detail = await api.getTenantMaintenanceRequest(requestId);
      setSelectedRequest(detail);
      setResolveOpen(false);
      setResolveRating(detail.tenant_rating ? String(detail.tenant_rating) : "");
      setResolveFeedback(detail.tenant_feedback || "");
      setCommentBody("");
      setCommentAttachment(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load request details");
    } finally {
      setIsDetailLoading(false);
    }
  };

  const closeCreateModal = () => {
    setIsCreateModalOpen(false);
    setForm({
      category: "other",
      urgency: "medium",
      title: "",
      description: "",
      preferred_entry_time: "",
      attachment: null,
    });
  };

  const handleCreate = async () => {
    const title = form.title.trim();
    const description = form.description.trim();
    if (!title || !description) return;

    setIsSaving(true);
    setError("");
    try {
      let created = await api.createTenantMaintenanceRequest({
        category: form.category,
        urgency: form.urgency,
        title,
        description,
        preferred_entry_time: form.preferred_entry_time.trim() || undefined,
      });
      if (form.attachment) {
        created = await api.addTenantMaintenanceAttachment(
          created.id,
          form.attachment,
          "Initial photo attachment"
        );
      }
      await loadRequests();
      closeCreateModal();
      setSelectedRequest(created);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit request");
    } finally {
      setIsSaving(false);
    }
  };

  const refreshSelectedRequest = async (requestId: string) => {
    const refreshed = await api.getTenantMaintenanceRequest(requestId);
    setSelectedRequest(refreshed);
    await loadRequests();
  };

  const handleComment = async () => {
    if (!selectedRequest) return;
    const body = commentBody.trim();
    if (!body && !commentAttachment) return;

    setIsSaving(true);
    setError("");
    try {
      const updated = commentAttachment
        ? await api.addTenantMaintenanceAttachment(
            selectedRequest.id,
            commentAttachment,
            body || undefined
          )
        : await api.addTenantMaintenanceComment(selectedRequest.id, body);
      setSelectedRequest(updated);
      setCommentBody("");
      setCommentAttachment(null);
      await loadRequests();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to post update");
    } finally {
      setIsSaving(false);
    }
  };

  const handleResolve = async () => {
    if (!selectedRequest) return;

    setIsSaving(true);
    setError("");
    try {
      const parsedRating = resolveRating ? Number(resolveRating) : undefined;
      await api.resolveTenantMaintenanceRequest(selectedRequest.id, {
        tenant_rating:
          parsedRating && parsedRating >= 1 && parsedRating <= 5 ? parsedRating : undefined,
        tenant_feedback: resolveFeedback.trim() || undefined,
      });
      await refreshSelectedRequest(selectedRequest.id);
      setResolveOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to mark request as completed");
    } finally {
      setIsSaving(false);
    }
  };

  const handleReopen = async () => {
    if (!selectedRequest) return;

    setIsSaving(true);
    setError("");
    try {
      await api.reopenTenantMaintenanceRequest(selectedRequest.id);
      await refreshSelectedRequest(selectedRequest.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reopen request");
    } finally {
      setIsSaving(false);
    }
  };

  const openCount = requests.filter(
    (request) => request.status !== "completed" && request.status !== "cancelled"
  ).length;
  const completedCount = requests.filter((request) => request.status === "completed").length;

  return (
    <section className="space-y-4 animate-slide-up stagger-3">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold flex items-center gap-2" style={{ fontFamily: "var(--font-outfit)" }}>
            <Wrench className="w-5 h-5 text-[var(--text-muted)]" />
            Maintenance Requests
          </h2>
          <p className="text-sm text-[var(--text-secondary)]">
            Report issues, follow repair progress, and confirm fixes.
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => setIsCreateModalOpen(true)}>
          <Plus className="w-4 h-4" />
          New Request
        </button>
      </div>

      {error && (
        <div className="p-3 bg-[var(--error-light)] text-[var(--error)] rounded-lg text-sm">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="card p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[var(--warning-light)] flex items-center justify-center">
            <Clock className="w-5 h-5 text-[var(--warning)]" />
          </div>
          <div>
            <p className="text-sm text-[var(--text-muted)]">Open Requests</p>
            <p className="text-xl font-semibold">{openCount}</p>
          </div>
        </div>
        <div className="card p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[var(--success-light)] flex items-center justify-center">
            <CheckCircle className="w-5 h-5 text-[var(--success)]" />
          </div>
          <div>
            <p className="text-sm text-[var(--text-muted)]">Completed</p>
            <p className="text-xl font-semibold">{completedCount}</p>
          </div>
        </div>
      </div>

      <div className="card overflow-hidden">
        {isLoading ? (
          <div className="p-10 flex items-center justify-center">
            <div className="spinner" />
          </div>
        ) : requests.length === 0 ? (
          <div className="p-10 text-center">
            <div className="w-14 h-14 rounded-full bg-[var(--surface-inset)] mx-auto mb-3 flex items-center justify-center">
              <Wrench className="w-7 h-7 text-[var(--text-muted)] opacity-60" />
            </div>
            <p className="font-medium">No maintenance requests yet.</p>
            <p className="text-sm text-[var(--text-secondary)] mt-1">
              Use New Request when anything needs repair.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-[var(--border)]">
            {requests.map((request) => (
              <div key={request.id} className="p-4 sm:p-5 flex flex-col gap-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold">{request.title}</p>
                    <p className="text-xs text-[var(--text-muted)] mt-1">
                      {request.property_name} / {request.room_name}
                    </p>
                  </div>
                  <div className="flex gap-2 flex-wrap justify-end">
                    <span className={`badge ${getStatusBadgeClass(request.status)}`}>
                      {statusLabel[request.status]}
                    </span>
                    <span className={`badge ${getUrgencyBadgeClass(request.urgency)}`}>
                      {request.urgency}
                    </span>
                  </div>
                </div>
                <p className="text-sm text-[var(--text-secondary)] line-clamp-2">
                  {request.description}
                </p>
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                  <p className="text-xs text-[var(--text-muted)] flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5" />
                    Updated {new Date(request.updated_at).toLocaleString()}
                  </p>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => void openRequest(request.id)}
                  >
                    <MessageSquare className="w-4 h-4" />
                    Open Thread
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {isCreateModalOpen && (
        <div className="modal-overlay" onClick={closeCreateModal}>
          <div className="modal max-w-2xl" onClick={(event) => event.stopPropagation()}>
            <div className="modal-header flex items-center justify-between">
              <h3 className="text-lg font-semibold">New Maintenance Request</h3>
              <button type="button" onClick={closeCreateModal} className="btn btn-ghost p-2">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="modal-body space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="label">Category</label>
                  <select
                    value={form.category}
                    onChange={(event) =>
                      setForm((prev) => ({
                        ...prev,
                        category: event.target.value as MaintenanceCategory,
                      }))
                    }
                    className="input"
                  >
                    {categoryOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="label">Urgency</label>
                  <select
                    value={form.urgency}
                    onChange={(event) =>
                      setForm((prev) => ({
                        ...prev,
                        urgency: event.target.value as MaintenanceUrgency,
                      }))
                    }
                    className="input"
                  >
                    {urgencyOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="label">Title</label>
                <input
                  value={form.title}
                  onChange={(event) =>
                    setForm((prev) => ({ ...prev, title: event.target.value }))
                  }
                  className="input"
                  placeholder="Example: Kitchen sink leak"
                  maxLength={140}
                />
              </div>

              <div>
                <label className="label">Description</label>
                <textarea
                  value={form.description}
                  onChange={(event) =>
                    setForm((prev) => ({ ...prev, description: event.target.value }))
                  }
                  className="input min-h-[120px]"
                  placeholder="Describe what is happening and where it happens."
                  maxLength={5000}
                />
              </div>

              <div>
                <label className="label">Preferred Entry Time (optional)</label>
                <input
                  value={form.preferred_entry_time}
                  onChange={(event) =>
                    setForm((prev) => ({
                      ...prev,
                      preferred_entry_time: event.target.value,
                    }))
                  }
                  className="input"
                  placeholder="Weekdays after 6pm"
                  maxLength={280}
                />
              </div>

              <div>
                <label className="label">Photo or PDF (optional)</label>
                <input
                  type="file"
                  accept="image/png,image/jpeg,application/pdf"
                  className="input"
                  onChange={(event) =>
                    setForm((prev) => ({ ...prev, attachment: event.target.files?.[0] || null }))
                  }
                />
              </div>
            </div>

            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={closeCreateModal}
                disabled={isSaving}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => void handleCreate()}
                disabled={isSaving || !form.title.trim() || !form.description.trim()}
              >
                {isSaving ? (
                  <>
                    <div className="spinner" />
                    Submitting...
                  </>
                ) : (
                  <>
                    <Wrench className="w-4 h-4" />
                    Submit Request
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {(selectedRequest || isDetailLoading) && (
        <div className="modal-overlay" onClick={() => setSelectedRequest(null)}>
          <div className="modal max-w-3xl" onClick={(event) => event.stopPropagation()}>
            <div className="modal-header flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold">
                  {selectedRequest?.title || "Maintenance Request"}
                </h3>
                {selectedRequest && (
                  <p className="text-xs text-[var(--text-muted)] mt-1">
                    {selectedRequest.property_name} / {selectedRequest.room_name}
                  </p>
                )}
              </div>
              <button
                type="button"
                className="btn btn-ghost p-2"
                onClick={() => setSelectedRequest(null)}
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="modal-body space-y-4">
              {isDetailLoading || !selectedRequest ? (
                <div className="h-36 flex items-center justify-center">
                  <div className="spinner" />
                </div>
              ) : (
                <>
                  <div className="flex flex-wrap gap-2">
                    <span className={`badge ${getStatusBadgeClass(selectedRequest.status)}`}>
                      {statusLabel[selectedRequest.status]}
                    </span>
                    <span className={`badge ${getUrgencyBadgeClass(selectedRequest.urgency)}`}>
                      {selectedRequest.urgency}
                    </span>
                    {selectedRequest.assigned_to && (
                      <span className="badge badge-info">Assigned: {selectedRequest.assigned_to}</span>
                    )}
                  </div>

                  <p className="text-sm text-[var(--text-secondary)]">
                    {selectedRequest.description}
                  </p>

                  {selectedRequest.preferred_entry_time && (
                    <div className="text-sm text-[var(--text-secondary)]">
                      <span className="font-medium text-[var(--text-primary)]">Preferred entry:</span>{" "}
                      {selectedRequest.preferred_entry_time}
                    </div>
                  )}

                  {selectedRequest.scheduled_visit_at && (
                    <div className="text-sm text-[var(--text-secondary)]">
                      <span className="font-medium text-[var(--text-primary)]">Scheduled visit:</span>{" "}
                      {new Date(selectedRequest.scheduled_visit_at).toLocaleString()}
                    </div>
                  )}

                  {(selectedRequest.estimated_cost || selectedRequest.actual_cost) && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm">
                      {selectedRequest.estimated_cost !== null &&
                        selectedRequest.estimated_cost !== undefined && (
                          <div>
                            <span className="font-medium">Estimated cost:</span>{" "}
                            {selectedRequest.estimated_cost.toLocaleString()}
                          </div>
                        )}
                      {selectedRequest.actual_cost !== null &&
                        selectedRequest.actual_cost !== undefined && (
                          <div>
                            <span className="font-medium">Actual cost:</span>{" "}
                            {selectedRequest.actual_cost.toLocaleString()}
                          </div>
                        )}
                    </div>
                  )}

                  {(selectedRequest.status === "acknowledged" ||
                    selectedRequest.status === "in_progress") && (
                    <div className="card p-3 bg-[var(--surface-inset)] border border-[var(--border)]">
                      {!resolveOpen ? (
                        <button
                          type="button"
                          className="btn btn-primary btn-sm"
                          onClick={() => setResolveOpen(true)}
                          disabled={isSaving}
                        >
                          <CheckCircle className="w-4 h-4" />
                          Mark as Fixed
                        </button>
                      ) : (
                        <div className="space-y-3">
                          <div>
                            <label className="label">Rating (optional)</label>
                            <select
                              className="input"
                              value={resolveRating}
                              onChange={(event) => setResolveRating(event.target.value)}
                            >
                              <option value="">No rating</option>
                              <option value="5">5 - Excellent</option>
                              <option value="4">4 - Good</option>
                              <option value="3">3 - Fair</option>
                              <option value="2">2 - Poor</option>
                              <option value="1">1 - Very Poor</option>
                            </select>
                          </div>
                          <div>
                            <label className="label">Feedback (optional)</label>
                            <textarea
                              value={resolveFeedback}
                              onChange={(event) => setResolveFeedback(event.target.value)}
                              className="input min-h-[90px]"
                              placeholder="How was the repair?"
                              maxLength={2000}
                            />
                          </div>
                          <div className="flex gap-2">
                            <button
                              type="button"
                              className="btn btn-secondary btn-sm"
                              onClick={() => setResolveOpen(false)}
                              disabled={isSaving}
                            >
                              Cancel
                            </button>
                            <button
                              type="button"
                              className="btn btn-primary btn-sm"
                              onClick={() => void handleResolve()}
                              disabled={isSaving}
                            >
                              <CheckCircle className="w-4 h-4" />
                              Confirm Resolution
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {(selectedRequest.status === "completed" ||
                    selectedRequest.status === "cancelled") && (
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => void handleReopen()}
                      disabled={isSaving}
                    >
                      <AlertTriangle className="w-4 h-4" />
                      Reopen Request
                    </button>
                  )}

                  <div className="divider" />

                  <div className="space-y-3">
                    <h4 className="font-medium">Discussion</h4>
                    <div className="max-h-72 overflow-y-auto space-y-2 rounded-xl border border-[var(--border)] p-3 bg-[var(--surface-inset)]">
                      {selectedRequest.comments.length === 0 ? (
                        <p className="text-sm text-[var(--text-muted)]">
                          No updates yet.
                        </p>
                      ) : (
                        selectedRequest.comments.map((comment) => (
                          <div key={comment.id} className="p-3 rounded-lg bg-[var(--surface)] border border-[var(--border)]">
                            <div className="flex items-center justify-between gap-3">
                              <p className="text-sm font-medium">
                                {comment.author_type === "tenant" ? "You" : "Landlord"}
                              </p>
                              <p className="text-xs text-[var(--text-muted)]">
                                {new Date(comment.created_at).toLocaleString()}
                              </p>
                            </div>
                            <p className="text-sm text-[var(--text-secondary)] mt-1 whitespace-pre-wrap">
                              {comment.body}
                            </p>
                            {comment.attachment_url && (
                              <a
                                href={api.getPublicAssetUrl(comment.attachment_url)}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-1.5 text-xs mt-2 text-[var(--primary-700)] hover:underline"
                              >
                                <Paperclip className="w-3.5 h-3.5" />
                                {comment.attachment_name || "View attachment"}
                              </a>
                            )}
                          </div>
                        ))
                      )}
                    </div>

                    <div>
                      <label className="label">Add Update</label>
                      <textarea
                        className="input min-h-[96px]"
                        value={commentBody}
                        onChange={(event) => setCommentBody(event.target.value)}
                        placeholder="Share progress details or ask a question..."
                        disabled={isSaving}
                      />
                    </div>

                    <div className="flex flex-col sm:flex-row gap-2 sm:items-center sm:justify-between">
                      <label className="btn btn-secondary btn-sm">
                        <Paperclip className="w-4 h-4" />
                        {commentAttachment ? commentAttachment.name : "Attach File"}
                        <input
                          type="file"
                          className="hidden"
                          accept="image/png,image/jpeg,application/pdf"
                          onChange={(event) =>
                            setCommentAttachment(event.target.files?.[0] || null)
                          }
                          disabled={isSaving}
                        />
                      </label>
                      <button
                        type="button"
                        className="btn btn-primary btn-sm"
                        onClick={() => void handleComment()}
                        disabled={isSaving || (!commentBody.trim() && !commentAttachment)}
                      >
                        <MessageSquare className="w-4 h-4" />
                        Send Update
                      </button>
                    </div>

                    {selectedRequest.tenant_rating && (
                      <div className="text-sm text-[var(--text-secondary)] flex items-center gap-2">
                        <Star className="w-4 h-4 text-[var(--warning)]" />
                        Rating submitted: {selectedRequest.tenant_rating}/5
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
