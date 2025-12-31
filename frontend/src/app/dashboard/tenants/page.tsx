"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import api, { TenantWithDetails, PropertyWithStats } from "@/lib/api";
import {
  Users,
  Plus,
  Search,
  Filter,
  Mail,
  Phone,
  Calendar,
  Home,
  ChevronRight,
  MoreVertical,
  UserMinus,
  Pencil,
  X,
  Clock,
  CreditCard,
} from "lucide-react";

export default function TenantsPage() {
  const [tenants, setTenants] = useState<TenantWithDetails[]>([]);
  const [properties, setProperties] = useState<PropertyWithStats[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterProperty, setFilterProperty] = useState("");
  const [showActiveOnly, setShowActiveOnly] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);

  useEffect(() => {
    loadData();
  }, [filterProperty, showActiveOnly]);

  const loadData = async () => {
    try {
      const [tenantsRes, propertiesRes] = await Promise.all([
        api.getTenants({
          property_id: filterProperty || undefined,
          active_only: showActiveOnly,
        }),
        api.getProperties(),
      ]);
      setTenants(tenantsRes.tenants);
      setProperties(propertiesRes.properties);
    } catch (error) {
      console.error("Failed to load tenants:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const filteredTenants = tenants.filter(
    (tenant) =>
      tenant.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      tenant.email?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      tenant.phone?.includes(searchQuery)
  );

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const getPaymentStatus = (tenant: TenantWithDetails) => {
    if (!tenant.payments || tenant.payments.length === 0) return null;
    const latestPayment = tenant.payments[0];
    return latestPayment.status;
  };

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
            Tenants
          </h1>
          <p className="page-subtitle">
            Manage your tenants and their payment schedules.
          </p>
        </div>
        <button onClick={() => setShowAddModal(true)} className="btn btn-primary">
          <Plus className="w-4 h-4" />
          Add Tenant
        </button>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        {[
          {
            label: "Total Tenants",
            value: tenants.length,
            icon: Users,
            color: "primary",
          },
          {
            label: "Active",
            value: tenants.filter((t) => t.is_active).length,
            icon: Home,
            color: "success",
          },
          {
            label: "Properties",
            value: new Set(tenants.map((t) => t.property?.id)).size,
            icon: Home,
            color: "info",
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
                    : "bg-[var(--info-light)]"
                }`}
              >
                <stat.icon
                  className={`w-6 h-6 ${
                    stat.color === "primary"
                      ? "text-[var(--primary-600)]"
                      : stat.color === "success"
                      ? "text-[var(--success)]"
                      : "text-[var(--info)]"
                  }`}
                />
              </div>
              <div>
                <p className="stat-label">{stat.label}</p>
                <p className="stat-value">{stat.value}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="card p-4 mb-6 animate-slide-up stagger-2">
        <div className="flex flex-col md:flex-row gap-4">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by name, email, or phone..."
              className="input pl-10"
            />
          </div>

          {/* Property Filter */}
          <div className="w-full md:w-48">
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

          {/* Active Toggle */}
          <button
            onClick={() => setShowActiveOnly(!showActiveOnly)}
            className={`btn ${showActiveOnly ? "btn-primary" : "btn-secondary"}`}
          >
            <Filter className="w-4 h-4" />
            {showActiveOnly ? "Active Only" : "All Tenants"}
          </button>
        </div>
      </div>

      {/* Tenants List */}
      {filteredTenants.length === 0 ? (
        <div className="card empty-state animate-slide-up stagger-3">
          <div className="empty-state-icon">
            <Users className="w-full h-full" />
          </div>
          <p className="empty-state-title">
            {searchQuery || filterProperty ? "No tenants found" : "No tenants yet"}
          </p>
          <p className="empty-state-description">
            {searchQuery || filterProperty
              ? "Try adjusting your search or filters."
              : "Add your first tenant to start tracking rent payments."}
          </p>
          {!searchQuery && !filterProperty && (
            <button onClick={() => setShowAddModal(true)} className="btn btn-primary">
              <Plus className="w-4 h-4" />
              Add Tenant
            </button>
          )}
        </div>
      ) : (
        <div className="grid gap-4 animate-slide-up stagger-3">
          {filteredTenants.map((tenant, i) => (
            <TenantCard
              key={tenant.id}
              tenant={tenant}
              onUpdate={loadData}
              style={{ animationDelay: `${(i + 3) * 0.05}s` }}
            />
          ))}
        </div>
      )}

      {/* Add Modal */}
      {showAddModal && (
        <AddTenantModal
          properties={properties}
          onClose={() => setShowAddModal(false)}
          onSave={loadData}
        />
      )}
    </div>
  );
}

function TenantCard({
  tenant,
  onUpdate,
  style,
}: {
  tenant: TenantWithDetails;
  onUpdate: () => void;
  style?: React.CSSProperties;
}) {
  const [showMenu, setShowMenu] = useState(false);

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const statusBadge = (status: string) => {
    const badges: Record<string, { class: string; label: string }> = {
      UPCOMING: { class: "badge-info", label: "Upcoming" },
      PENDING: { class: "badge-warning", label: "Pending" },
      ON_TIME: { class: "badge-success", label: "Paid" },
      LATE: { class: "badge-warning", label: "Late" },
      OVERDUE: { class: "badge-error", label: "Overdue" },
      WAIVED: { class: "badge-neutral", label: "Waived" },
    };
    return badges[status] || { class: "badge-neutral", label: status };
  };

  const latestPayment = tenant.payments?.[0];

  return (
    <div className="card animate-slide-up" style={style}>
      <div className="p-5">
        <div className="flex items-start gap-4">
          {/* Avatar */}
          <div className="avatar avatar-lg avatar-primary">
            {tenant.name.charAt(0).toUpperCase()}
          </div>

          {/* Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="font-semibold text-lg mb-1">{tenant.name}</h3>
                <div className="flex items-center gap-4 text-sm text-[var(--text-secondary)]">
                  <span className="flex items-center gap-1.5">
                    <Home className="w-3.5 h-3.5" />
                    {tenant.property?.name} — {tenant.room?.name}
                  </span>
                  {!tenant.is_active && (
                    <span className="badge badge-neutral">Inactive</span>
                  )}
                </div>
              </div>

              {/* Actions */}
              <div className="relative">
                <button
                  onClick={() => setShowMenu(!showMenu)}
                  className="btn btn-ghost p-2"
                >
                  <MoreVertical className="w-4 h-4" />
                </button>
                {showMenu && (
                  <>
                    <div
                      className="fixed inset-0 z-10"
                      onClick={() => setShowMenu(false)}
                    />
                    <div className="absolute right-0 top-full mt-1 w-44 bg-[var(--surface)] border border-[var(--border)] rounded-xl shadow-lg z-20 overflow-hidden animate-scale-in">
                      <Link
                        href={`/dashboard/tenants/${tenant.id}`}
                        className="flex items-center gap-2 px-4 py-2.5 text-sm hover:bg-[var(--surface-inset)] transition-colors"
                      >
                        <ChevronRight className="w-4 h-4" />
                        View Details
                      </Link>
                      <button className="w-full flex items-center gap-2 px-4 py-2.5 text-sm hover:bg-[var(--surface-inset)] transition-colors">
                        <Pencil className="w-4 h-4" />
                        Edit Tenant
                      </button>
                      {tenant.is_active && (
                        <button className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-[var(--error)] hover:bg-[var(--error-light)] transition-colors">
                          <UserMinus className="w-4 h-4" />
                          Move Out
                        </button>
                      )}
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* Contact & Details */}
            <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="flex items-center gap-2 text-sm">
                <div className="w-8 h-8 rounded-lg bg-[var(--surface-inset)] flex items-center justify-center">
                  <Mail className="w-4 h-4 text-[var(--text-muted)]" />
                </div>
                <span className="text-[var(--text-secondary)] truncate">
                  {tenant.email || "No email"}
                </span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <div className="w-8 h-8 rounded-lg bg-[var(--surface-inset)] flex items-center justify-center">
                  <Phone className="w-4 h-4 text-[var(--text-muted)]" />
                </div>
                <span className="text-[var(--text-secondary)]">
                  {tenant.phone || "No phone"}
                </span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <div className="w-8 h-8 rounded-lg bg-[var(--surface-inset)] flex items-center justify-center">
                  <Calendar className="w-4 h-4 text-[var(--text-muted)]" />
                </div>
                <span className="text-[var(--text-secondary)]">
                  Since {formatDate(tenant.move_in_date)}
                </span>
              </div>
            </div>

            {/* Payment Status */}
            {latestPayment && (
              <div className="mt-4 pt-4 border-t border-[var(--border)] flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <CreditCard className="w-4 h-4 text-[var(--text-muted)]" />
                  <span className="text-sm text-[var(--text-secondary)]">
                    Latest payment:
                  </span>
                  <span className={`badge ${statusBadge(latestPayment.status).class}`}>
                    {statusBadge(latestPayment.status).label}
                  </span>
                </div>
                {tenant.payment_schedule && (
                  <span className="text-sm font-medium">
                    ${tenant.payment_schedule.amount.toLocaleString()}/
                    {tenant.payment_schedule.frequency.toLowerCase().replace("_", "-")}
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function AddTenantModal({
  properties,
  onClose,
  onSave,
}: {
  properties: PropertyWithStats[];
  onClose: () => void;
  onSave: () => void;
}) {
  const [step, setStep] = useState(1);
  const [selectedProperty, setSelectedProperty] = useState("");
  const [rooms, setRooms] = useState<{ id: string; name: string; rent_amount: number }[]>([]);
  const [formData, setFormData] = useState({
    room_id: "",
    name: "",
    email: "",
    phone: "",
    move_in_date: new Date().toISOString().split("T")[0],
  });
  const [scheduleData, setScheduleData] = useState({
    amount: 0,
    frequency: "MONTHLY",
    due_day: 1,
    window_days: 5,
    start_date: new Date().toISOString().split("T")[0],
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (selectedProperty) {
      loadRooms();
    }
  }, [selectedProperty]);

  const loadRooms = async () => {
    try {
      const res = await api.getRooms(selectedProperty);
      // Only show vacant rooms
      const vacantRooms = res.rooms.filter((r) => !r.is_occupied);
      setRooms(vacantRooms);
      if (vacantRooms.length > 0) {
        setFormData((prev) => ({ ...prev, room_id: vacantRooms[0].id }));
        setScheduleData((prev) => ({ ...prev, amount: vacantRooms[0].rent_amount }));
      }
    } catch (error) {
      console.error("Failed to load rooms:", error);
    }
  };

  const handleSubmit = async () => {
    setError("");
    setIsLoading(true);

    try {
      // Create tenant
      const tenant = await api.createTenant(formData);

      // Create payment schedule
      await api.createPaymentSchedule(tenant.id, scheduleData);

      onSave();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create tenant");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold" style={{ fontFamily: "var(--font-outfit)" }}>
              Add New Tenant
            </h2>
            <p className="text-sm text-[var(--text-secondary)] mt-1">
              Step {step} of 2: {step === 1 ? "Tenant Details" : "Payment Schedule"}
            </p>
          </div>
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

          {step === 1 ? (
            <div className="space-y-4">
              <div>
                <label className="label">Property</label>
                <select
                  value={selectedProperty}
                  onChange={(e) => setSelectedProperty(e.target.value)}
                  className="input"
                  required
                >
                  <option value="">Select a property</option>
                  {properties.map((prop) => (
                    <option key={prop.id} value={prop.id}>
                      {prop.name}
                    </option>
                  ))}
                </select>
              </div>

              {selectedProperty && (
                <div>
                  <label className="label">Room</label>
                  {rooms.length === 0 ? (
                    <p className="text-sm text-[var(--warning)]">
                      No vacant rooms in this property.
                    </p>
                  ) : (
                    <select
                      value={formData.room_id}
                      onChange={(e) => {
                        const room = rooms.find((r) => r.id === e.target.value);
                        setFormData((prev) => ({ ...prev, room_id: e.target.value }));
                        if (room) {
                          setScheduleData((prev) => ({
                            ...prev,
                            amount: room.rent_amount,
                          }));
                        }
                      }}
                      className="input"
                      required
                    >
                      {rooms.map((room) => (
                        <option key={room.id} value={room.id}>
                          {room.name} — ${room.rent_amount}/month
                        </option>
                      ))}
                    </select>
                  )}
                </div>
              )}

              <div className="divider" />

              <div>
                <label className="label">Full Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, name: e.target.value }))
                  }
                  className="input"
                  placeholder="John Doe"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="label">Email</label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, email: e.target.value }))
                    }
                    className="input"
                    placeholder="john@example.com"
                  />
                </div>
                <div>
                  <label className="label">Phone</label>
                  <input
                    type="tel"
                    value={formData.phone}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, phone: e.target.value }))
                    }
                    className="input"
                    placeholder="+1 555 123 4567"
                  />
                </div>
              </div>

              <div>
                <label className="label">Move-in Date</label>
                <input
                  type="date"
                  value={formData.move_in_date}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, move_in_date: e.target.value }))
                  }
                  className="input"
                  required
                />
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="label">Rent Amount</label>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]">
                      $
                    </span>
                    <input
                      type="number"
                      value={scheduleData.amount}
                      onChange={(e) =>
                        setScheduleData((prev) => ({
                          ...prev,
                          amount: parseFloat(e.target.value) || 0,
                        }))
                      }
                      className="input pl-8"
                      min="0"
                      required
                    />
                  </div>
                </div>
                <div>
                  <label className="label">Frequency</label>
                  <select
                    value={scheduleData.frequency}
                    onChange={(e) =>
                      setScheduleData((prev) => ({ ...prev, frequency: e.target.value }))
                    }
                    className="input"
                  >
                    <option value="MONTHLY">Monthly</option>
                    <option value="BI_MONTHLY">Bi-Monthly</option>
                    <option value="QUARTERLY">Quarterly</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="label">Due Day of Month</label>
                  <input
                    type="number"
                    value={scheduleData.due_day}
                    onChange={(e) =>
                      setScheduleData((prev) => ({
                        ...prev,
                        due_day: parseInt(e.target.value) || 1,
                      }))
                    }
                    className="input"
                    min="1"
                    max="28"
                    required
                  />
                  <p className="text-xs text-[var(--text-muted)] mt-1">
                    Payment is due on this day each period
                  </p>
                </div>
                <div>
                  <label className="label">Grace Period (days)</label>
                  <input
                    type="number"
                    value={scheduleData.window_days}
                    onChange={(e) =>
                      setScheduleData((prev) => ({
                        ...prev,
                        window_days: parseInt(e.target.value) || 0,
                      }))
                    }
                    className="input"
                    min="0"
                    max="15"
                  />
                  <p className="text-xs text-[var(--text-muted)] mt-1">
                    Days after due date before marked overdue
                  </p>
                </div>
              </div>

              <div>
                <label className="label">Schedule Start Date</label>
                <input
                  type="date"
                  value={scheduleData.start_date}
                  onChange={(e) =>
                    setScheduleData((prev) => ({ ...prev, start_date: e.target.value }))
                  }
                  className="input"
                  required
                />
              </div>
            </div>
          )}
        </div>

        <div className="modal-footer">
          {step === 1 ? (
            <>
              <button onClick={onClose} className="btn btn-secondary">
                Cancel
              </button>
              <button
                onClick={() => setStep(2)}
                disabled={!formData.room_id || !formData.name}
                className="btn btn-primary"
              >
                Next: Payment Schedule
                <ChevronRight className="w-4 h-4" />
              </button>
            </>
          ) : (
            <>
              <button onClick={() => setStep(1)} className="btn btn-secondary">
                Back
              </button>
              <button
                onClick={handleSubmit}
                disabled={isLoading}
                className="btn btn-primary"
              >
                {isLoading ? (
                  <>
                    <div className="spinner" />
                    Creating...
                  </>
                ) : (
                  "Add Tenant"
                )}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
