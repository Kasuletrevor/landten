/**
 * API client for LandTen backend
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

interface ApiError {
  detail: string;
}

class ApiClient {
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
    if (typeof window !== "undefined") {
      if (token) {
        localStorage.setItem("landten_token", token);
      } else {
        localStorage.removeItem("landten_token");
      }
    }
  }

  getToken(): string | null {
    if (this.token) return this.token;
    if (typeof window !== "undefined") {
      this.token = localStorage.getItem("landten_token");
    }
    return this.token;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const token = this.getToken();
    const headers: HeadersInit = {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    };

    if (token) {
      (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
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
    });

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({
        detail: "An error occurred during upload",
      }));
      throw new Error(error.detail);
    }

    return response.json() as Promise<PaymentWithTenant>;
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

  async sendPaymentReminder(paymentId: string, method: "email" | "sms" | "both") {
    return this.request<{ message: string; results: Record<string, string> }>(
      `/notifications/send-reminder/${paymentId}?method=${method}`,
      { method: "POST" }
    );
  }

  // SSE Stream
  subscribeToNotifications(onMessage: (event: SSEEvent) => void): () => void {
    const token = this.getToken();
    if (!token) {
      console.error("No token for SSE");
      return () => {};
    }

    const eventSource = new EventSource(
      `${API_BASE}/notifications/stream?token=${token}`
    );

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage({ type: event.type || "message", data });
      } catch (e) {
        console.error("SSE parse error:", e);
      }
    };

    eventSource.addEventListener("connected", (event) => {
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

    eventSource.onerror = (error) => {
      console.error("SSE error:", error);
    };

    return () => eventSource.close();
  }

  // Analytics
  async getAnalytics() {
    return this.request<DashboardAnalytics>("/analytics/dashboard");
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
  is_manual: boolean;
  created_at: string;
  updated_at: string;
}

export interface PaymentWithTenant extends Payment {
  tenant: Tenant;
  room: Room;
  property: Property;
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

export const api = new ApiClient();
export default api;
