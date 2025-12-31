"use client";

import { createContext, useContext, useState, useCallback, useEffect, ReactNode } from "react";
import { CheckCircle, AlertTriangle, AlertCircle, Info, X } from "lucide-react";
import api, { SSEEvent } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export type ToastType = "success" | "error" | "warning" | "info";

interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
}

interface ToastContextType {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, "id">) => void;
  removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const { isAuthenticated } = useAuth();

  const addToast = useCallback((toast: Omit<Toast, "id">) => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { ...toast, id }]);

    // Auto-remove after duration
    const duration = toast.duration || 5000;
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, duration);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // SSE Subscription for real-time notifications
  useEffect(() => {
    if (!isAuthenticated) return;

    const handleSSEEvent = (event: SSEEvent) => {
      switch (event.type) {
        case "payment_due":
          addToast({
            type: "warning",
            title: "Payment Due Soon",
            message: `Payment for ${event.data.tenant_name || "a tenant"} is due soon.`,
          });
          break;
        case "payment_overdue":
          addToast({
            type: "error",
            title: "Payment Overdue",
            message: `Payment for ${event.data.tenant_name || "a tenant"} is now overdue.`,
          });
          break;
        case "payment_received":
          addToast({
            type: "success",
            title: "Payment Received",
            message: `Payment from ${event.data.tenant_name || "a tenant"} has been recorded.`,
          });
          break;
        default:
          // Handle generic messages
          if (event.data.title && event.data.message) {
            addToast({
              type: "info",
              title: event.data.title as string,
              message: event.data.message as string,
            });
          }
      }
    };

    const unsubscribe = api.subscribeToNotifications(handleSSEEvent);
    return () => unsubscribe();
  }, [isAuthenticated, addToast]);

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </ToastContext.Provider>
  );
}

function ToastContainer({
  toasts,
  onRemove,
}: {
  toasts: Toast[];
  onRemove: (id: string) => void;
}) {
  if (toasts.length === 0) return null;

  return (
    <div className="toast-container">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onRemove={onRemove} />
      ))}
    </div>
  );
}

function ToastItem({
  toast,
  onRemove,
}: {
  toast: Toast;
  onRemove: (id: string) => void;
}) {
  const icons = {
    success: CheckCircle,
    error: AlertCircle,
    warning: AlertTriangle,
    info: Info,
  };

  const colors = {
    success: "text-[var(--success)]",
    error: "text-[var(--error)]",
    warning: "text-[var(--warning)]",
    info: "text-[var(--info)]",
  };

  const borderColors = {
    success: "toast-success",
    error: "toast-error",
    warning: "toast-warning",
    info: "toast-info",
  };

  const Icon = icons[toast.type];

  return (
    <div className={`toast ${borderColors[toast.type]}`}>
      <div className={`flex-shrink-0 ${colors[toast.type]}`}>
        <Icon className="w-5 h-5" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-sm">{toast.title}</p>
        {toast.message && (
          <p className="text-sm text-[var(--text-secondary)] mt-0.5">{toast.message}</p>
        )}
      </div>
      <button
        onClick={() => onRemove(toast.id)}
        className="flex-shrink-0 p-1 rounded-lg hover:bg-[var(--surface-inset)] transition-colors"
      >
        <X className="w-4 h-4 text-[var(--text-muted)]" />
      </button>
    </div>
  );
}
