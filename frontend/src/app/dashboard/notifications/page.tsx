"use client";

import { useState, useEffect, useCallback } from "react";
import { Bell, Filter, Check, CheckCheck, Search, X, Loader2, Download } from "lucide-react";
import api, { NotificationItem } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

const NOTIFICATION_ICONS = {
  payment_due: { icon: "💰", label: "Payment Due" },
  payment_overdue: { icon: "⚠️", label: "Payment Overdue" },
  payment_received: { icon: "✅", label: "Payment Received" },
  tenant_added: { icon: "👤", label: "New Tenant" },
  reminder_sent: { icon: "📧", label: "Reminder Sent" },
};

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function NotificationsPage() {
  const { isAuthenticated } = useAuth();
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "unread">("all");
  const [searchQuery, setSearchQuery] = useState("");

  const fetchNotifications = useCallback(async () => {
    if (!isAuthenticated) return;
    setIsLoading(true);
    try {
      const response = await api.getNotifications({
        unreadOnly: filter === "unread",
        limit: 50,
      });
      setNotifications(response.notifications);
    } catch (error) {
      console.error("Failed to fetch notifications:", error);
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated, filter]);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  const markAsRead = async (notificationId: string) => {
    try {
      await api.markNotificationRead(notificationId);
      setNotifications((prev) =>
        prev.map((n) => (n.id === notificationId ? { ...n, is_read: true } : n))
      );
    } catch (error) {
      console.error("Failed to mark notification as read:", error);
    }
  };

  const markAllAsRead = async () => {
    try {
      await api.markAllNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch (error) {
      console.error("Failed to mark all notifications as read:", error);
    }
  };

  const filteredNotifications = notifications.filter((n) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      n.title.toLowerCase().includes(query) ||
      n.message.toLowerCase().includes(query)
    );
  });

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  return (
    <div className="animate-fade-in">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Notifications</h1>
          <p className="page-subtitle">
            Stay updated with payments, tenants, and property activity
          </p>
        </div>
        <div className="flex items-center gap-3">
          {unreadCount > 0 && (
            <button
              onClick={markAllAsRead}
              className="btn btn-secondary btn-sm"
            >
              <CheckCheck className="w-4 h-4" />
              Mark all as read
            </button>
          )}
        </div>
      </div>

      {/* Filters & Search */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
        {/* Filter Tabs */}
        <div className="flex items-center bg-[var(--surface)] border border-[var(--border)] rounded-xl p-1">
          <button
            onClick={() => setFilter("all")}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-all ${
              filter === "all"
                ? "bg-[var(--primary-100)] text-[var(--primary-700)]"
                : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            }`}
          >
            All
          </button>
          <button
            onClick={() => setFilter("unread")}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-all flex items-center gap-2 ${
              filter === "unread"
                ? "bg-[var(--primary-100)] text-[var(--primary-700)]"
                : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            }`}
          >
            Unread
            {unreadCount > 0 && (
              <span className="px-1.5 py-0.5 bg-[var(--primary-500)] text-white text-xs font-bold rounded-full">
                {unreadCount}
              </span>
            )}
          </button>
        </div>

        {/* Search */}
        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
          <input
            type="text"
            placeholder="Search notifications..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input pl-10 pr-10"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)] hover:text-[var(--text-primary)]"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Notification List */}
      <div className="card">
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-[var(--primary-500)]" />
          </div>
        ) : filteredNotifications.length === 0 ? (
          <div className="empty-state py-16">
            <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-[var(--surface-inset)] flex items-center justify-center">
              <Bell className="w-10 h-10 text-[var(--text-muted)]" />
            </div>
            <h3 className="empty-state-title">No notifications</h3>
            <p className="empty-state-description">
              {filter === "unread"
                ? "You have no unread notifications."
                : "You don't have any notifications yet."}
            </p>
          </div>
        ) : (
          <div className="divide-y divide-[var(--border)]">
            {filteredNotifications.map((notification) => {
              const iconInfo = NOTIFICATION_ICONS[notification.type as keyof typeof NOTIFICATION_ICONS];
              return (
                <div
                  key={notification.id}
                  className={`flex items-start gap-4 p-5 hover:bg-[var(--surface-inset)] transition-colors ${
                    !notification.is_read ? "bg-[var(--primary-50)]" : ""
                  }`}
                >
                  {/* Icon */}
                  <div
                    className={`flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center text-xl ${
                      !notification.is_read
                        ? "bg-[var(--primary-100)]"
                        : "bg-[var(--surface-inset)]"
                    }`}
                  >
                    {iconInfo?.icon || "🔔"}
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <h4 className={`font-semibold text-[var(--text-primary)] ${!notification.is_read ? "" : "font-medium"}`}>
                          {notification.title}
                        </h4>
                        <p className="text-[var(--text-secondary)] mt-1">
                          {notification.message}
                        </p>
                        {iconInfo && (
                          <span className="inline-flex items-center gap-1 mt-2 px-2 py-0.5 bg-[var(--surface-inset)] text-[var(--text-muted)] text-xs rounded-full">
                            {iconInfo.icon}
                            {iconInfo.label}
                          </span>
                        )}
                      </div>
                      <div className="flex-shrink-0 flex items-center gap-2">
                        <span className="text-xs text-[var(--text-muted)]">
                          {formatDate(notification.created_at)}
                        </span>
                        {!notification.is_read && (
                          <button
                            onClick={() => markAsRead(notification.id)}
                            className="p-1.5 rounded-lg hover:bg-[var(--surface)] text-[var(--text-muted)] hover:text-[var(--success)] transition-colors"
                            title="Mark as read"
                          >
                            <Check className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Unread indicator */}
                  {!notification.is_read && (
                    <div className="flex-shrink-0">
                      <span className="w-2.5 h-2.5 rounded-full bg-[var(--primary-500)] block" />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* SSE Info */}
      <div className="flex items-center justify-center gap-2 mt-6 text-xs text-[var(--text-muted)]">
        <span className="w-2 h-2 rounded-full bg-[var(--success)] animate-pulse" />
        Real-time updates enabled via Server-Sent Events
      </div>
    </div>
  );
}
