"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Bell, Check, CheckCheck, X, ChevronRight, Loader2 } from "lucide-react";
import api, { NotificationItem } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import Link from "next/link";

const NOTIFICATION_ICONS = {
  payment_due: {
    icon: "💰",
    bg: "bg-[var(--warning-light)]",
    text: "text-[var(--warning)]",
  },
  payment_overdue: {
    icon: "⚠️",
    bg: "bg-[var(--error-light)]",
    text: "text-[var(--error)]",
  },
  payment_received: {
    icon: "✅",
    bg: "bg-[var(--success-light)]",
    text: "text-[var(--success)]",
  },
  tenant_added: {
    icon: "👤",
    bg: "bg-[var(--info-light)]",
    text: "text-[var(--info)]",
  },
  reminder_sent: {
    icon: "📧",
    bg: "bg-[var(--primary-100)]",
    text: "text-[var(--primary-700)]",
  },
  default: {
    icon: "🔔",
    bg: "bg-[var(--surface-inset)]",
    text: "text-[var(--text-secondary)]",
  },
};

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

export function NotificationBell() {
  const { isAuthenticated } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  const fetchNotifications = useCallback(async () => {
    if (!isAuthenticated) return;
    setIsLoading(true);
    try {
      const response = await api.getNotifications({ unreadOnly: false, limit: 10 });
      setNotifications(response.notifications);
      setUnreadCount(response.unread_count);
    } catch (error) {
      console.error("Failed to fetch notifications:", error);
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated]);

  const markAsRead = async (notificationId: string) => {
    try {
      await api.markNotificationRead(notificationId);
      setNotifications((prev) =>
        prev.map((n) => (n.id === notificationId ? { ...n, is_read: true } : n))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (error) {
      console.error("Failed to mark notification as read:", error);
    }
  };

  const markAllAsRead = async () => {
    try {
      await api.markAllNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (error) {
      console.error("Failed to mark all notifications as read:", error);
    }
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        !buttonRef.current?.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Fetch on open
  useEffect(() => {
    if (isOpen) {
      fetchNotifications();
    }
  }, [isOpen, fetchNotifications]);

  // Listen for real-time notifications
  useEffect(() => {
    if (!isAuthenticated) return;

    const handleNotification = (event: CustomEvent<NotificationItem>) => {
      const newNotification = event.detail;
      setNotifications((prev) => [newNotification, ...prev]);
      setUnreadCount((prev) => prev + 1);
    };

    window.addEventListener("new-notification", handleNotification as EventListener);
    return () =>
      window.removeEventListener("new-notification", handleNotification as EventListener);
  }, [isAuthenticated]);

  const getNotificationStyle = (type: string) => {
    return NOTIFICATION_ICONS[type as keyof typeof NOTIFICATION_ICONS] || NOTIFICATION_ICONS.default;
  };

  return (
    <div className="relative">
      {/* Bell Button */}
      <button
        ref={buttonRef}
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 rounded-xl hover:bg-[var(--surface-inset)] transition-all duration-200 group"
        aria-label="Notifications"
      >
        <Bell className="w-5 h-5 text-[var(--text-secondary)] group-hover:text-[var(--text-primary)] transition-colors" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] flex items-center justify-center px-1 py-0.5 bg-[var(--error)] text-white text-[10px] font-bold rounded-full animate-scale-in">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown Panel */}
      {isOpen && (
        <div
          ref={dropdownRef}
          className="absolute right-0 top-full mt-2 w-[380px] bg-[var(--surface)] rounded-2xl shadow-[var(--shadow-xl)] border border-[var(--border)] overflow-hidden animate-slide-down"
          style={{ animationDuration: "0.25s" }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border)] bg-[var(--surface-inset)]">
            <div className="flex items-center gap-2">
              <Bell className="w-4 h-4 text-[var(--primary-600)]" />
              <h3 className="font-semibold text-[var(--text-primary)]">Notifications</h3>
              {unreadCount > 0 && (
                <span className="px-2 py-0.5 bg-[var(--primary-100)] text-[var(--primary-700)] text-xs font-semibold rounded-full">
                  {unreadCount} new
                </span>
              )}
            </div>
            {unreadCount > 0 && (
              <button
                onClick={markAllAsRead}
                className="flex items-center gap-1.5 px-2 py-1 text-xs font-medium text-[var(--primary-600)] hover:bg-[var(--primary-50)] rounded-lg transition-colors"
              >
                <CheckCheck className="w-3.5 h-3.5" />
                Mark all read
              </button>
            )}
          </div>

          {/* Notification List */}
          <div className="max-h-[420px] overflow-y-auto">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-6 h-6 animate-spin text-[var(--primary-500)]" />
              </div>
            ) : notifications.length === 0 ? (
              <div className="empty-state py-12">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--surface-inset)] flex items-center justify-center">
                  <Bell className="w-8 h-8 text-[var(--text-muted)]" />
                </div>
                <p className="empty-state-title">All caught up!</p>
                <p className="empty-state-description text-sm">
                  You&apos;ll see notifications here when you receive them.
                </p>
              </div>
            ) : (
              <div className="divide-y divide-[var(--border)]">
                {notifications.map((notification) => {
                  const style = getNotificationStyle(notification.type);
                  return (
                    <div
                      key={notification.id}
                      className={`flex gap-3 p-4 hover:bg-[var(--surface-inset)] transition-colors cursor-pointer ${
                        !notification.is_read ? "bg-[var(--primary-50)]" : ""
                      }`}
                      onClick={() => {
                        if (!notification.is_read) {
                          markAsRead(notification.id);
                        }
                      }}
                    >
                      {/* Icon */}
                      <div
                        className={`flex-shrink-0 w-10 h-10 rounded-xl ${style.bg} flex items-center justify-center text-lg`}
                      >
                        {style.icon}
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2">
                          <p className={`font-medium text-sm ${!notification.is_read ? "text-[var(--text-primary)]" : "text-[var(--text-secondary)]"}`}>
                            {notification.title}
                          </p>
                          {!notification.is_read && (
                            <span className="flex-shrink-0 w-2 h-2 rounded-full bg-[var(--primary-500)] mt-1.5" />
                          )}
                        </div>
                        <p className="text-xs text-[var(--text-secondary)] mt-0.5 line-clamp-2">
                          {notification.message}
                        </p>
                        <p className="text-xs text-[var(--text-muted)] mt-1.5">
                          {formatRelativeTime(notification.created_at)}
                        </p>
                      </div>

                      {/* Action */}
                      {!notification.is_read && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            markAsRead(notification.id);
                          }}
                          className="flex-shrink-0 p-1.5 rounded-lg hover:bg-[var(--surface)] text-[var(--text-muted)] hover:text-[var(--success)] transition-colors"
                          aria-label="Mark as read"
                        >
                          <Check className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between px-4 py-3 border-t border-[var(--border)] bg-[var(--surface-inset)]">
            <Link
              href="/dashboard/notifications"
              onClick={() => setIsOpen(false)}
              className="flex items-center gap-1 text-sm font-medium text-[var(--primary-600)] hover:text-[var(--primary-700)] transition-colors"
            >
              View all notifications
              <ChevronRight className="w-4 h-4" />
            </Link>
            <span className="text-xs text-[var(--text-muted)]">
              Powered by SSE
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
