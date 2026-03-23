/**
 * API client for LandTen backend
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
const API_PUBLIC_BASE = API_BASE.replace(/\/api\/?$/, "");

interface ApiError {
  detail: string;
}

class ApiClient {
  setToken(_token: string | null) {
    // Cookie-based auth is the source of truth.
    // Keep this method for backward compatibility and to clear legacy storage.
    void _token;
    if (typeof window !== "undefined") {
      localStorage.removeItem("landten_token");
    }
  }

  getToken(): string | null {
    return null;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: HeadersInit = {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    };

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
      credentials: "include",
    });

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({
        detail: "An error occurred",
      }));
      throw new Error(error.detail);
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  }

  // Auth
  async register(data: {
    email: string;
    password: string;
    name: string;
    phone?: string;
  }) {
    return this.request<LoginResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async login(email: string, password: string) {
    return this.request<LoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  }

  async getMe() {
    return this.request<Landlord>("/auth/me");
  }

  async updateMe(data: { name?: string; phone?: string }) {
    return this.request<Landlord>("/auth/me", {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async logout() {
    return this.request<void>("/auth/logout", { method: "POST" });
  }

  // Properties
  async getProperties() {
    return this.request<PropertyListResponse>("/properties");
  }

  async getProperty(id: string) {
    return this.request<PropertyWithStats>(`/properties/${id}`);
  }

  async createProperty(data: { name: string; address: string; description?: string }) {
    return this.request<Property>("/properties", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async updateProperty(
    id: string,
    data: { name?: string; address?: string; description?: string; grace_period_days?: number }
  ) {
    return this.request<Property>(`/properties/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async deleteProperty(id: string) {
    return this.request<void>(`/properties/${id}`, { method: "DELETE" });
  }

  // Rooms
  async getRooms(propertyId: string) {
    return this.request<RoomListResponse>(`/properties/${propertyId}/rooms`);
  }

  async getRoom(propertyId: string, roomId: string) {
    return this.request<RoomWithTenant>(`/properties/${propertyId}/rooms/${roomId}`);
  }

  async createRoom(propertyId: string, data: { name: string; rent_amount: number; currency?: string }) {
    return this.request<Room>(`/properties/${propertyId}/rooms`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async updateRoom(
    propertyId: string,
    roomId: string,
    data: { name?: string; rent_amount?: number; currency?: string }
  ) {
    return this.request<Room>(`/properties/${propertyId}/rooms/${roomId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async deleteRoom(propertyId: string, roomId: string) {
    return this.request<void>(`/properties/${propertyId}/rooms/${roomId}`, {
      method: "DELETE",
    });
  }

  async createRoomsBulk(
    propertyId: string,
    data: {
      prefix: string;
      from_number: number;
      to_number: number;
      currency: string;
      price_ranges: { from_number: number; to_number: number; rent_amount: number }[];
      padding: number;
    }
  ) {
    return this.request<BulkRoomResponse>(`/properties/${propertyId}/rooms/bulk`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // Tenants
  async getTenants(filters?: { property_id?: string; room_id?: string; active_only?: boolean }) {
    const params = new URLSearchParams();
    if (filters?.property_id) params.set("property_id", filters.property_id);
    if (filters?.room_id) params.set("room_id", filters.room_id);
    if (filters?.active_only !== undefined)
      params.set("active_only", String(filters.active_only));
    const query = params.toString() ? `?${params.toString()}` : "";
    return this.request<TenantListResponse>(`/tenants${query}`);
  }

  async getTenant(id: string) {
    return this.request<TenantWithDetails>(`/tenants/${id}`);
  }

  async createTenant(data: {
    room_id: string;
    name: string;
    email?: string;
    phone?: string;
    move_in_date: string;
  }) {
    return this.request<Tenant>("/tenants", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async updateTenant(
    id: string,
    data: { name?: string; email?: string; phone?: string }
  ) {
    return this.request<Tenant>(`/tenants/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async moveOutTenant(id: string, moveOutDate: string) {
    return this.request<Tenant>(`/tenants/${id}/move-out`, {
      method: "POST",
      body: JSON.stringify({ move_out_date: moveOutDate }),
    });
  }

  // Tenant Portal (Landlord Side)
  async enableTenantPortal(tenantId: string) {
    return this.request<{ invite_url: string; invite_token: string }>(
      `/tenants/${tenantId}/enable-portal`,
      { method: "POST" }
    );
  }

  async disableTenantPortal(tenantId: string) {
    return this.request<void>(`/tenants/${tenantId}/disable-portal`, {
      method: "DELETE",
    });
  }

  // Tenant Portal (Tenant Side)
  async tenantLogin(email: string, password: string) {
    return this.request<TenantLoginResponse>("/tenant-auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  }

  async tenantSetupPassword(token: string, password: string) {
    // We explicitly set the Authorization header with the invite token
    // This overrides the default behavior if we were using a raw fetch,
    // but since our request method appends the stored token if it exists,
    // we need to be careful. However, for a setup flow, the user shouldn't be logged in.
    return this.request<TenantPortalResponse>("/tenant-auth/setup-password", {
      method: "POST",
      body: JSON.stringify({ password }),
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  }

  async getTenantMe() {
    return this.request<TenantPortalResponse>("/tenant-auth/me");
  }

  async tenantLogout() {
    return this.request<void>("/tenant-auth/logout", { method: "POST" });
  }

  async getTenantPaymentsMe() {
    return this.request<{
      payments: Payment[];
      summary: {
        total_payments: number;
        pending: number;
        overdue: number;
        paid_on_time: number;
        paid_late: number;
      };
    }>("/tenant-auth/payments");
  }

  async getTenantPaymentDispute(paymentId: string) {
    return this.request<PaymentDispute>(`/tenant-auth/payments/${paymentId}/dispute`);
  }

  async postTenantPaymentDisputeMessage(paymentId: string, body: string) {
    return this.request<PaymentDispute>(`/tenant-auth/payments/${paymentId}/dispute/messages`, {
      method: "POST",
      body: JSON.stringify({ body }),
    });
  }

  async postTenantPaymentDisputeAttachment(paymentId: string, file: File, body?: string) {
    const formData = new FormData();
    formData.append("file", file);
    if (body) {
      formData.append("body", body);
    }

    const token = this.getToken();
    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(
      `${API_BASE}/tenant-auth/payments/${paymentId}/dispute/messages/attachments`,
      {
        method: "POST",
        body: formData,
        headers,
        credentials: "include",
      }
    );

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({
        detail: "An error occurred during upload",
      }));
      throw new Error(error.detail);
    }

    return response.json() as Promise<PaymentDispute>;
  }

  // Maintenance (Tenant Side)
  async getTenantMaintenanceRequests() {
    return this.request<MaintenanceRequestListResponse>("/tenant-auth/maintenance");
  }

  async createTenantMaintenanceRequest(data: {
    category: MaintenanceCategory;
    urgency: MaintenanceUrgency;
    title: string;
    description: string;
    preferred_entry_time?: string;
  }) {
    return this.request<MaintenanceRequest>("/tenant-auth/maintenance", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async getTenantMaintenanceRequest(requestId: string) {
    return this.request<MaintenanceRequest>(`/tenant-auth/maintenance/${requestId}`);
  }

  async addTenantMaintenanceComment(requestId: string, body: string) {
    return this.request<MaintenanceRequest>(
      `/tenant-auth/maintenance/${requestId}/comments`,
      {
        method: "POST",
        body: JSON.stringify({ body }),
      }
    );
  }

  async addTenantMaintenanceAttachment(requestId: string, file: File, body?: string) {
    const formData = new FormData();
    formData.append("file", file);
    if (body) {
      formData.append("body", body);
    }

    const response = await fetch(
      `${API_BASE}/tenant-auth/maintenance/${requestId}/comments/attachments`,
      {
        method: "POST",
        body: formData,
        credentials: "include",
      }
    );

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({
        detail: "An error occurred during upload",
      }));
      throw new Error(error.detail);
    }

    return response.json() as Promise<MaintenanceRequest>;
  }

  async resolveTenantMaintenanceRequest(
    requestId: string,
    data?: { tenant_rating?: number; tenant_feedback?: string }
  ) {
    return this.request<MaintenanceRequest>(`/tenant-auth/maintenance/${requestId}/resolve`, {
      method: "PUT",
      body: JSON.stringify(data || {}),
    });
  }

  async reopenTenantMaintenanceRequest(requestId: string) {
    return this.request<MaintenanceRequest>(`/tenant-auth/maintenance/${requestId}/reopen`, {
      method: "PUT",
    });
  }

  // Payment Schedule
  async createPaymentSchedule(
    tenantId: string,
    data: {
      amount: number;
      frequency: string;
      due_day: number;
      window_days: number;
      start_date: string;
    }
  ) {
    return this.request<PaymentSchedule>(`/tenants/${tenantId}/payment-schedule`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async updatePaymentSchedule(
    tenantId: string,
    data: { amount?: number; frequency?: string; due_day?: number; window_days?: number }
  ) {
    return this.request<PaymentSchedule>(`/tenants/${tenantId}/payment-schedule`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  // Payments
  async getPayments(filters?: {
    tenant_id?: string;
    property_id?: string;
    status?: string;
    start_date?: string;
    end_date?: string;
  }) {
    const params = new URLSearchParams();
    if (filters?.tenant_id) params.set("tenant_id", filters.tenant_id);
    if (filters?.property_id) params.set("property_id", filters.property_id);
    if (filters?.status) params.set("status", filters.status);
    if (filters?.start_date) params.set("start_date", filters.start_date);
    if (filters?.end_date) params.set("end_date", filters.end_date);
    const query = params.toString() ? `?${params.toString()}` : "";
    return this.request<PaymentListResponse>(`/payments${query}`);
  }

  async getPaymentsSummary(propertyId?: string) {
    const query = propertyId ? `?property_id=${propertyId}` : "";
    return this.request<PaymentSummary>(`/payments/summary${query}`);
  }

  async getUpcomingPayments(days?: number, propertyId?: string) {
    const params = new URLSearchParams();
    if (days) params.set("days", String(days));
    if (propertyId) params.set("property_id", propertyId);
    const query = params.toString() ? `?${params.toString()}` : "";
    return this.request<PaymentListResponse>(`/payments/upcoming${query}`);
  }

  async getOverduePayments(propertyId?: string) {
    const query = propertyId ? `?property_id=${propertyId}` : "";
    return this.request<PaymentListResponse>(`/payments/overdue${query}`);
  }

  async markPaymentPaid(
    id: string,
    data: { payment_reference: string; notes?: string }
  ) {
    return this.request<Payment>(`/payments/${id}/mark-paid`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async waivePayment(id: string, reason: string) {
    return this.request<Payment>(`/payments/${id}/waive`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    });
  }

  async rejectReceipt(id: string, reason: string) {
    return this.request<Payment>(`/payments/${id}/reject-receipt`, {
      method: "PUT",
      body: JSON.stringify({ reason }),
    });
  }

  async createManualPayment(data: {
    tenant_id: string;
    amount: number;
    period_start: string;
    period_end: string;
    due_date: string;
    notes?: string;
  }) {
    return this.request<Payment>("/payments/manual", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async getPaymentDispute(paymentId: string) {
    return this.request<PaymentDispute>(`/payments/${paymentId}/dispute`);
  }

  async postPaymentDisputeMessage(paymentId: string, body: string) {
    return this.request<PaymentDispute>(`/payments/${paymentId}/dispute/messages`, {
      method: "POST",
      body: JSON.stringify({ body }),
    });
  }

  async postPaymentDisputeAttachment(paymentId: string, file: File, body?: string) {
    const formData = new FormData();
    formData.append("file", file);
    if (body) {
      formData.append("body", body);
    }

    const token = this.getToken();
    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(
      `${API_BASE}/payments/${paymentId}/dispute/messages/attachments`,
      {
        method: "POST",
        body: formData,
        headers,
        credentials: "include",
      }
    );

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({
        detail: "An error occurred during upload",
      }));
      throw new Error(error.detail);
    }

    return response.json() as Promise<PaymentDispute>;
  }

  async resolvePaymentDispute(paymentId: string) {
    return this.request<PaymentDispute>(`/payments/${paymentId}/dispute/resolve`, {
      method: "PUT",
    });
  }

  async reopenPaymentDispute(paymentId: string) {
    return this.request<PaymentDispute>(`/payments/${paymentId}/dispute/reopen`, {
      method: "PUT",
    });
  }

  getPaymentDisputeAttachmentUrl(paymentId: string, messageId: string) {
    return `${API_BASE}/payments/${paymentId}/dispute/messages/${messageId}/attachment`;
  }

  getPublicAssetUrl(path?: string | null) {
    if (!path) return "";
    if (/^https?:\/\//i.test(path)) {
      return path;
    }
    const normalizedPath = path.startsWith("/") ? path : `/${path}`;
    return `${API_PUBLIC_BASE}${normalizedPath}`;
  }

  async uploadPaymentReceipt(paymentId: string, file: File) {
    const formData = new FormData();
    formData.append("file", file);

    const token = this.getToken();
    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}/payments/${paymentId}/upload-receipt`, {
      method: "POST",
      body: formData,
      headers,
      credentials: "include",
    });

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({
        detail: "An error occurred during upload",
      }));
      throw new Error(error.detail);
    }

    return response.json() as Promise<PaymentWithTenant>;
  }

  // Maintenance (Landlord Side)
  async getMaintenanceRequests(filters?: {
    status?: MaintenanceStatusValue;
    urgency?: MaintenanceUrgency;
    property_id?: string;
    search?: string;
  }) {
    const params = new URLSearchParams();
    if (filters?.status) params.set("status", filters.status);
    if (filters?.urgency) params.set("urgency", filters.urgency);
    if (filters?.property_id) params.set("property_id", filters.property_id);
    if (filters?.search) params.set("search", filters.search);
    const query = params.toString() ? `?${params.toString()}` : "";
    return this.request<MaintenanceRequestListResponse>(`/maintenance${query}`);
  }

  async getMaintenanceRequest(requestId: string) {
    return this.request<MaintenanceRequest>(`/maintenance/${requestId}`);
  }

  async updateMaintenanceRequest(
    requestId: string,
    data: {
      status?: MaintenanceStatusValue;
      assigned_to?: string;
      scheduled_visit_at?: string;
      estimated_cost?: number;
      actual_cost?: number;
      landlord_notes?: string;
    }
  ) {
    return this.request<MaintenanceRequest>(`/maintenance/${requestId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async addMaintenanceComment(requestId: string, body: string, isInternal = false) {
    return this.request<MaintenanceRequest>(`/maintenance/${requestId}/comments`, {
      method: "POST",
      body: JSON.stringify({ body, is_internal: isInternal }),
    });
  }

  async addMaintenanceAttachment(
    requestId: string,
    file: File,
    options?: { body?: string; is_internal?: boolean }
  ) {
    const formData = new FormData();
    formData.append("file", file);
    if (options?.body) {
      formData.append("body", options.body);
    }
    if (options?.is_internal !== undefined) {
      formData.append("is_internal", String(options.is_internal));
    }

    const response = await fetch(`${API_BASE}/maintenance/${requestId}/comments/attachments`, {
      method: "POST",
      body: formData,
      credentials: "include",
    });

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({
        detail: "An error occurred during upload",
      }));
      throw new Error(error.detail);
    }

    return response.json() as Promise<MaintenanceRequest>;
  }

  // Notifications
  async getNotifications(params?: { unreadOnly?: boolean; limit?: number; offset?: number }) {
    const queryParams = new URLSearchParams();
    if (params?.unreadOnly) queryParams.set("unread_only", "true");
    if (params?.limit) queryParams.set("limit", params.limit.toString());
    if (params?.offset) queryParams.set("offset", params.offset.toString());
    const query = queryParams.toString() ? `?${queryParams.toString()}` : "";
    return this.request<NotificationListResponse>(`/notifications${query}`);
  }

  async markNotificationRead(id: string) {
    return this.request<void>(`/notifications/${id}/read`, { method: "PUT" });
  }

  async markAllNotificationsRead() {
    return this.request<void>("/notifications/read-all", { method: "PUT" });
  }

  async sendPaymentReminder(paymentId: string, method: "email") {
    return this.request<{ message: string; results: Record<string, string> }>(
      `/notifications/send-reminder/${paymentId}?method=${method}`,
      { method: "POST" }
    );
  }

  // SSE Stream
  subscribeToNotifications(onMessage: (event: SSEEvent) => void): () => void {
    const eventSource = new EventSource(`${API_BASE}/notifications/stream`, {
      withCredentials: true,
    });
    const forwardEvent = (type: string) => (event: Event) => {
      onMessage({ type, data: JSON.parse((event as MessageEvent).data) });
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage({ type: event.type || "message", data });
      } catch (e) {
        console.error("SSE parse error:", e);
      }
    };

    eventSource.addEventListener("connected", () => {
      console.log("SSE connected");
    });

    eventSource.addEventListener("payment_due", (event) => {
      onMessage({ type: "payment_due", data: JSON.parse((event as MessageEvent).data) });
    });

    eventSource.addEventListener("payment_overdue", (event) => {
      onMessage({ type: "payment_overdue", data: JSON.parse((event as MessageEvent).data) });
    });

    eventSource.addEventListener("payment_received", (event) => {
      onMessage({ type: "payment_received", data: JSON.parse((event as MessageEvent).data) });
    });

    eventSource.addEventListener("payment_dispute_message", (event) => {
      onMessage({
        type: "payment_dispute_message",
        data: JSON.parse((event as MessageEvent).data),
      });
    });

    ["maintenance_request_created", "maintenance_request_updated", "maintenance_comment_created"].forEach(
      (type) => eventSource.addEventListener(type, forwardEvent(type))
    );

    eventSource.onerror = (error) => {
      console.error("SSE error:", error);
    };

    return () => eventSource.close();
  }

  subscribeToTenantNotifications(onMessage: (event: SSEEvent) => void): () => void {
    const eventSource = new EventSource(`${API_BASE}/tenant-auth/stream`, {
      withCredentials: true,
    });
    const forwardEvent = (type: string) => (event: Event) => {
      onMessage({ type, data: JSON.parse((event as MessageEvent).data) });
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage({ type: event.type || "message", data });
      } catch (e) {
        console.error("Tenant SSE parse error:", e);
      }
    };

    eventSource.addEventListener("connected", () => {
      console.log("Tenant SSE connected");
    });

    eventSource.addEventListener("payment_dispute_message", (event) => {
      onMessage({
        type: "payment_dispute_message",
        data: JSON.parse((event as MessageEvent).data),
      });
    });

    ["payment_receipt_rejected", "maintenance_request_updated", "maintenance_comment_created"].forEach(
      (type) => eventSource.addEventListener(type, forwardEvent(type))
    );

    eventSource.onerror = (error) => {
      console.error("Tenant SSE error:", error);
    };

    return () => eventSource.close();
  }

  // Analytics
  async getAnalytics() {
    return this.request<DashboardAnalytics>("/analytics/dashboard");
  }

  // Lease Agreements
  async getLeases(filters?: { property_id?: string; status?: string }) {
    const params = new URLSearchParams();
    if (filters?.property_id) params.set("property_id", filters.property_id);
    if (filters?.status) params.set("status", filters.status);
    const query = params.toString() ? `?${params.toString()}` : "";
    return this.request<LeaseAgreementListResponse>(`/leases${query}`);
  }

  async getLeaseSummary() {
    return this.request<LeaseStatusSummary>("/leases/summary");
  }

  async getLease(id: string) {
    return this.request<LeaseAgreementWithTenant>(`/leases/${id}`);
  }

  async uploadLeaseDocument(
    tenantId: string,
    file: File,
    data?: { start_date?: string; end_date?: string; rent_amount?: number }
  ) {
    const formData = new FormData();
    formData.append("file", file);
    if (data?.start_date) formData.append("start_date", data.start_date);
    if (data?.end_date) formData.append("end_date", data.end_date);
    if (data?.rent_amount) formData.append("rent_amount", data.rent_amount.toString());

    const token = this.getToken();
    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}/leases/upload-original/${tenantId}`, {
      method: "POST",
      body: formData,
      headers,
      credentials: "include",
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: "An error occurred during upload",
      }));
      throw new Error(error.detail);
    }

    return response.json() as Promise<LeaseAgreement>;
  }

  async uploadSignedLease(leaseId: string, file: File) {
    const formData = new FormData();
    formData.append("file", file);

    const token = this.getToken();
    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}/leases/${leaseId}/upload-signed`, {
      method: "POST",
      body: formData,
      headers,
      credentials: "include",
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: "An error occurred during upload",
      }));
      throw new Error(error.detail);
    }

    return response.json() as Promise<LeaseAgreement>;
  }

  async updateLease(
    id: string,
    data: { start_date?: string; end_date?: string; rent_amount?: number }
  ) {
    return this.request<LeaseAgreement>(`/leases/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async deleteLease(id: string) {
    return this.request<void>(`/leases/${id}`, { method: "DELETE" });
  }

  async downloadOriginalLease(leaseId: string) {
    return this.request<Blob>(`/leases/${leaseId}/download-original`, {
      method: "GET",
    });
  }

  async downloadSignedLease(leaseId: string) {
    return this.request<Blob>(`/leases/${leaseId}/download-signed`, {
      method: "GET",
    });
  }

  // Tenant Lease Endpoints
  async getMyLease() {
    return this.request<LeaseAgreement>("/leases/tenant/my-lease");
  }

  async tenantUploadSignedLease(file: File) {
    const formData = new FormData();
    formData.append("file", file);

    const token = this.getToken();
    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}/leases/tenant/my-lease/upload-signed`, {
      method: "POST",
      body: formData,
      headers,
      credentials: "include",
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: "An error occurred during upload",
      }));
      throw new Error(error.detail);
    }

    return response.json() as Promise<LeaseAgreement>;
  }

  async tenantDownloadLease(): Promise<Blob> {
    const token = this.getToken();
    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}/leases/tenant/my-lease/download`, {
      method: "GET",
      headers,
      credentials: "include",
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: "An error occurred during download",
      }));
      throw new Error(error.detail);
    }

    return response.blob();
  }

  // Export
  async exportPayments(params: {
    format: "excel" | "pdf";
    start_date?: string;
    end_date?: string;
    property_id?: string;
    tenant_id?: string;
    status?: string;
  }): Promise<Blob> {
    const queryParams = new URLSearchParams();
    queryParams.set("format", params.format);
    if (params.start_date) queryParams.set("start_date", params.start_date);
    if (params.end_date) queryParams.set("end_date", params.end_date);
    if (params.property_id) queryParams.set("property_id", params.property_id);
    if (params.tenant_id) queryParams.set("tenant_id", params.tenant_id);
    if (params.status) queryParams.set("status", params.status);

    const response = await fetch(
      `${API_BASE}/payments/export?${queryParams.toString()}`,
      {
        credentials: "include",
      }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: "Export failed",
      }));
      throw new Error(error.detail);
    }

    return response.blob();
  }
}

// Types
export interface Landlord {
  id: string;
  email: string;
  name: string;
  phone?: string;
  created_at: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  landlord: Landlord;
}

export interface Property {
  id: string;
  landlord_id: string;
  name: string;
  address: string;
  description?: string;
  grace_period_days: number;
  created_at: string;
  updated_at: string;
}

export interface PropertyWithStats extends Property {
  total_rooms: number;
  occupied_rooms: number;
  vacant_rooms: number;
  total_tenants: number;
  monthly_expected_income: number;
}

export interface PropertyListResponse {
  properties: PropertyWithStats[];
  total: number;
}

export interface Room {
  id: string;
  property_id: string;
  name: string;
  rent_amount: number;
  currency: string;
  is_occupied: boolean;
  created_at: string;
  updated_at: string;
}

export interface RoomWithTenant extends Room {
  tenant?: Tenant;
}

export interface RoomListResponse {
  rooms: RoomWithTenant[];
  total: number;
}

export interface BulkRoomResponse {
  created: Room[];
  total_created: number;
  warnings: string[];
}

export interface Tenant {
  id: string;
  room_id: string;
  name: string;
  email?: string;
  phone?: string;
  move_in_date: string;
  move_out_date?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TenantWithDetails extends Tenant {
  room: Room;
  property: Property;
  payment_schedule?: PaymentSchedule;
  payments: Payment[];
  has_portal_access: boolean;
}

export interface TenantLoginResponse {
  access_token: string;
  token_type: string;
  tenant: TenantPortalResponse;
}

export interface TenantPortalResponse {
  id: string;
  name: string;
  email: string;
  phone?: string;
  move_in_date: string;
  move_out_date?: string;
  is_active: boolean;
  room_name?: string;
  room_currency?: string;
  rent_amount?: number;
  property_name?: string;
  landlord_name?: string;
  has_portal_access: boolean;
}

export interface TenantListResponse {
  tenants: TenantWithDetails[];
  total: number;
}

export interface PaymentSchedule {
  id: string;
  tenant_id: string;
  amount: number;
  frequency: "MONTHLY" | "BI_MONTHLY" | "QUARTERLY";
  due_day: number;
  window_days: number;
  start_date: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export type PaymentStatus =
  | "UPCOMING"
  | "PENDING"
  | "ON_TIME"
  | "LATE"
  | "OVERDUE"
  | "WAIVED"
  | "VERIFYING";

export type DisputeStatus = "open" | "resolved" | "OPEN" | "RESOLVED";
export type DisputeActorType = "landlord" | "tenant" | "system";

export interface Payment {
  id: string;
  tenant_id: string;
  schedule_id?: string;
  period_start: string;
  period_end: string;
  amount_due: number;
  due_date: string;
  window_end_date: string;
  status: PaymentStatus;
  paid_date?: string;
  payment_reference?: string;
  receipt_url?: string;
  notes?: string;
  rejection_reason?: string;
  dispute_status?: DisputeStatus | null;
  dispute_unread_count?: number;
  last_dispute_message_at?: string | null;
  is_manual: boolean;
  created_at: string;
  updated_at: string;
}

export interface PaymentWithTenant extends Payment {
  tenant?: Tenant;
  room?: Room;
  property?: Property;
  tenant_name?: string;
  tenant_email?: string;
  tenant_phone?: string;
  room_name?: string;
  property_id?: string;
  property_name?: string;
  currency?: string;
  days_until_due?: number;
  days_overdue?: number;
}

export interface PaymentDisputeMessage {
  id: string;
  dispute_id: string;
  payment_id: string;
  author_type: DisputeActorType;
  author_id: string;
  body: string;
  attachment_name?: string | null;
  attachment_url?: string | null;
  attachment_content_type?: string | null;
  attachment_size_bytes?: number | null;
  created_at: string;
}

export interface PaymentDispute {
  id: string;
  payment_id: string;
  status: DisputeStatus;
  opened_by_type: DisputeActorType;
  opened_by_id: string;
  opened_at: string;
  resolved_by_type?: DisputeActorType | null;
  resolved_by_id?: string | null;
  resolved_at?: string | null;
  landlord_last_read_at?: string | null;
  tenant_last_read_at?: string | null;
  last_message_at?: string | null;
  unread_count: number;
  messages: PaymentDisputeMessage[];
}

export type MaintenanceCategory =
  | "plumbing"
  | "electrical"
  | "appliance"
  | "structural"
  | "other";

export type MaintenanceUrgency = "emergency" | "high" | "medium" | "low";

export type MaintenanceStatusValue =
  | "submitted"
  | "acknowledged"
  | "in_progress"
  | "completed"
  | "cancelled";

export type MaintenanceAuthorType = "landlord" | "tenant" | "system";

export interface MaintenanceComment {
  id: string;
  request_id: string;
  author_type: MaintenanceAuthorType;
  author_id: string;
  body: string;
  is_internal: boolean;
  attachment_name?: string | null;
  attachment_url?: string | null;
  attachment_content_type?: string | null;
  attachment_size_bytes?: number | null;
  created_at: string;
}

export interface MaintenanceRequest {
  id: string;
  tenant_id: string;
  property_id: string;
  room_id: string;
  category: MaintenanceCategory;
  urgency: MaintenanceUrgency;
  status: MaintenanceStatusValue;
  title: string;
  description: string;
  preferred_entry_time?: string | null;
  assigned_to?: string | null;
  scheduled_visit_at?: string | null;
  estimated_cost?: number | null;
  actual_cost?: number | null;
  landlord_notes?: string | null;
  completed_at?: string | null;
  tenant_rating?: number | null;
  tenant_feedback?: string | null;
  created_at: string;
  updated_at: string;
  tenant_name?: string | null;
  tenant_email?: string | null;
  tenant_phone?: string | null;
  property_name?: string | null;
  room_name?: string | null;
  comments_count: number;
  comments: MaintenanceComment[];
}

export interface MaintenanceRequestListResponse {
  requests: MaintenanceRequest[];
  total: number;
}

export interface PaymentListResponse {
  payments: PaymentWithTenant[];
  total: number;
}

export interface PaymentSummary {
  total_expected: number;
  total_received: number;
  total_outstanding: number;
  total_overdue: number;
  upcoming_count: number;
  pending_count: number;
  overdue_count: number;
  paid_count: number;
}

export interface Notification {
  id: string;
  landlord_id: string;
  type: string;
  title: string;
  message: string;
  is_read: boolean;
  payment_id?: string;
  tenant_id?: string;
  created_at: string;
}

export type NotificationItem = Notification;

export interface NotificationListResponse {
  notifications: Notification[];
  total: number;
  unread_count: number;
}

export interface SSEEvent {
  type: string;
  data: Record<string, unknown>;
}

// Analytics Types
export interface MonthlyStats {
  month: string; // Format: "YYYY-MM"
  expected: number;
  received: number;
  collection_rate: number; // Percentage 0-100
}

export interface CurrentMonthStats {
  expected: number;
  received: number;
  outstanding: number;
  collection_rate: number;
}

export interface VacancyStats {
  total_rooms: number;
  occupied: number;
  vacant: number;
  vacancy_rate: number; // Percentage 0-100
}

export interface OverdueSummary {
  count: number;
  total_amount: number;
  oldest_days: number; // Days since oldest overdue payment
}

export interface TrendComparison {
  current_value: number;
  previous_value: number;
  change_percent: number; // Positive = increase, Negative = decrease
  is_improvement: boolean; // True if change is good
}

export interface DashboardAnalytics {
  current_month: CurrentMonthStats;
  trend: MonthlyStats[]; // 3 months, oldest first
  vacancy: VacancyStats;
  overdue_summary: OverdueSummary;
  income_trend: TrendComparison;
  collection_trend: TrendComparison;
  vacancy_trend: TrendComparison;
  primary_currency: string;
  currency_note: string;
}

// Lease Agreement Types
export type LeaseStatus = "UNSIGNED" | "SIGNED";

export interface LeaseAgreement {
  id: string;
  tenant_id: string;
  property_id: string;
  original_url: string;
  signed_url?: string;
  status: LeaseStatus;
  start_date?: string;
  end_date?: string;
  rent_amount?: number;
  uploaded_by_landlord: boolean;
  signed_uploaded_by?: string;
  created_at: string;
  updated_at: string;
}

export interface LeaseAgreementWithTenant extends LeaseAgreement {
  tenant_name?: string;
  tenant_email?: string;
  tenant_phone?: string;
  room_name?: string;
  property_name?: string;
}

export interface LeaseAgreementListResponse {
  leases: LeaseAgreementWithTenant[];
  total: number;
}

export interface LeaseStatusSummary {
  total_unsigned: number;
  total_signed: number;
  total: number;
}

export const api = new ApiClient();
export default api;
