"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import api, { PropertyWithStats, RoomWithTenant } from "@/lib/api";
import {
  Building2,
  MapPin,
  ArrowLeft,
  Plus,
  DoorOpen,
  Users,
  CreditCard,
  Pencil,
  Trash2,
  X,
  MoreVertical,
  User,
  AlertCircle,
} from "lucide-react";

export default function PropertyDetailPage() {
  const params = useParams();
  const router = useRouter();
  const propertyId = params.id as string;

  const [property, setProperty] = useState<PropertyWithStats | null>(null);
  const [rooms, setRooms] = useState<RoomWithTenant[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  // Modals
  const [showAddRoom, setShowAddRoom] = useState(false);
  const [editRoom, setEditRoom] = useState<RoomWithTenant | null>(null);
  const [deleteRoom, setDeleteRoom] = useState<RoomWithTenant | null>(null);
  const [showEditProperty, setShowEditProperty] = useState(false);

  useEffect(() => {
    loadData();
  }, [propertyId]);

  const loadData = async () => {
    try {
      const [propertyRes, roomsRes] = await Promise.all([
        api.getProperty(propertyId),
        api.getRooms(propertyId),
      ]);
      setProperty(propertyRes);
      setRooms(roomsRes.rooms);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load property");
    } finally {
      setIsLoading(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
    }).format(amount);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="spinner" />
      </div>
    );
  }

  if (error || !property) {
    return (
      <div className="animate-fade-in">
        <Link
          href="/dashboard/properties"
          className="inline-flex items-center gap-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Properties
        </Link>
        <div className="card p-8 text-center">
          <AlertCircle className="w-12 h-12 text-[var(--error)] mx-auto mb-4" />
          <h2 className="text-xl font-semibold mb-2">Property Not Found</h2>
          <p className="text-[var(--text-secondary)]">{error || "The property you're looking for doesn't exist."}</p>
        </div>
      </div>
    );
  }

  const occupancyRate = property.total_rooms > 0 
    ? Math.round((property.occupied_rooms / property.total_rooms) * 100) 
    : 0;

  return (
    <div className="animate-fade-in">
      {/* Back Link */}
      <Link
        href="/dashboard/properties"
        className="inline-flex items-center gap-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] mb-6 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Properties
      </Link>

      {/* Property Header Card */}
      <div className="card mb-8 animate-slide-up">
        <div className="p-6">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-4">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-[var(--primary-100)] to-[var(--primary-200)] flex items-center justify-center">
                <Building2 className="w-8 h-8 text-[var(--primary-600)]" />
              </div>
              <div>
                <h1
                  className="text-2xl font-bold mb-1"
                  style={{ fontFamily: "var(--font-outfit)" }}
                >
                  {property.name}
                </h1>
                <p className="flex items-center gap-1.5 text-[var(--text-secondary)]">
                  <MapPin className="w-4 h-4" />
                  {property.address}
                </p>
                {property.description && (
                  <p className="mt-2 text-sm text-[var(--text-muted)]">
                    {property.description}
                  </p>
                )}
              </div>
            </div>
            <button
              onClick={() => setShowEditProperty(true)}
              className="btn btn-secondary"
            >
              <Pencil className="w-4 h-4" />
              Edit
            </button>
          </div>
        </div>

        {/* Stats Bar */}
        <div className="grid grid-cols-4 border-t border-[var(--border)]">
          {[
            {
              label: "Total Rooms",
              value: property.total_rooms,
              icon: DoorOpen,
            },
            {
              label: "Occupied",
              value: property.occupied_rooms,
              icon: Users,
              sub: `${occupancyRate}%`,
            },
            {
              label: "Vacant",
              value: property.vacant_rooms,
              icon: DoorOpen,
            },
            {
              label: "Monthly Income",
              value: formatCurrency(property.monthly_expected_income),
              icon: CreditCard,
            },
          ].map((stat, i) => (
            <div
              key={stat.label}
              className={`p-4 text-center ${i < 3 ? "border-r border-[var(--border)]" : ""}`}
            >
              <div className="flex items-center justify-center gap-2 text-[var(--text-muted)] mb-1">
                <stat.icon className="w-4 h-4" />
                <span className="text-xs font-medium uppercase tracking-wide">
                  {stat.label}
                </span>
              </div>
              <p
                className="text-xl font-bold"
                style={{ fontFamily: "var(--font-outfit)" }}
              >
                {stat.value}
              </p>
              {stat.sub && (
                <p className="text-xs text-[var(--text-muted)]">{stat.sub}</p>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Rooms Section */}
      <div className="flex items-center justify-between mb-6 animate-slide-up stagger-1">
        <div>
          <h2
            className="text-xl font-semibold"
            style={{ fontFamily: "var(--font-outfit)" }}
          >
            Rooms
          </h2>
          <p className="text-sm text-[var(--text-muted)]">
            Manage rooms and tenants in this property
          </p>
        </div>
        <button onClick={() => setShowAddRoom(true)} className="btn btn-primary">
          <Plus className="w-4 h-4" />
          Add Room
        </button>
      </div>

      {/* Rooms Grid */}
      {rooms.length === 0 ? (
        <div className="card empty-state animate-slide-up stagger-2">
          <div className="empty-state-icon">
            <DoorOpen className="w-full h-full" />
          </div>
          <p className="empty-state-title">No rooms yet</p>
          <p className="empty-state-description">
            Add rooms to this property to start managing tenants.
          </p>
          <button onClick={() => setShowAddRoom(true)} className="btn btn-primary">
            <Plus className="w-4 h-4" />
            Add Room
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 animate-slide-up stagger-2">
          {rooms.map((room, i) => (
            <div
              key={room.id}
              className={`card animate-slide-up ${
                room.is_occupied ? "" : "border-dashed"
              }`}
              style={{ animationDelay: `${(i + 2) * 0.05}s` }}
            >
              <div className="p-5">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div
                      className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                        room.is_occupied
                          ? "bg-[var(--success-light)]"
                          : "bg-[var(--surface-inset)]"
                      }`}
                    >
                      <DoorOpen
                        className={`w-5 h-5 ${
                          room.is_occupied
                            ? "text-[var(--success)]"
                            : "text-[var(--text-muted)]"
                        }`}
                      />
                    </div>
                    <div>
                      <h3 className="font-semibold">{room.name}</h3>
                      <p className="text-sm text-[var(--text-muted)]">
                        {formatCurrency(room.rent_amount)}/month
                      </p>
                    </div>
                  </div>

                  <div className="relative group">
                    <button className="btn btn-ghost p-2">
                      <MoreVertical className="w-4 h-4" />
                    </button>
                    <div className="absolute right-0 top-full mt-1 w-36 bg-[var(--surface)] border border-[var(--border)] rounded-lg shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10">
                      <button
                        onClick={() => setEditRoom(room)}
                        className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left hover:bg-[var(--neutral-100)] rounded-t-lg"
                      >
                        <Pencil className="w-4 h-4" />
                        Edit
                      </button>
                      <button
                        onClick={() => setDeleteRoom(room)}
                        disabled={room.is_occupied}
                        className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left text-[var(--error)] hover:bg-[var(--error-light)] rounded-b-lg disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <Trash2 className="w-4 h-4" />
                        Delete
                      </button>
                    </div>
                  </div>
                </div>

                {/* Tenant Info */}
                {room.tenant ? (
                  <Link
                    href={`/dashboard/tenants/${room.tenant.id}`}
                    className="block p-3 bg-[var(--surface-inset)] rounded-xl hover:bg-[var(--neutral-200)] transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className="avatar avatar-sm avatar-primary">
                        {room.tenant.name.charAt(0).toUpperCase()}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium truncate">{room.tenant.name}</p>
                        <p className="text-xs text-[var(--text-muted)]">
                          Since {new Date(room.tenant.move_in_date).toLocaleDateString("en-US", {
                            month: "short",
                            year: "numeric",
                          })}
                        </p>
                      </div>
                      <span className="badge badge-success">Active</span>
                    </div>
                  </Link>
                ) : (
                  <div className="p-3 border-2 border-dashed border-[var(--border)] rounded-xl text-center">
                    <User className="w-5 h-5 text-[var(--text-muted)] mx-auto mb-1" />
                    <p className="text-sm text-[var(--text-muted)]">Vacant</p>
                    <Link
                      href="/dashboard/tenants"
                      className="text-xs text-[var(--primary-600)] hover:underline"
                    >
                      Add tenant
                    </Link>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add/Edit Room Modal */}
      {(showAddRoom || editRoom) && (
        <RoomModal
          propertyId={propertyId}
          room={editRoom}
          onClose={() => {
            setShowAddRoom(false);
            setEditRoom(null);
          }}
          onSave={loadData}
        />
      )}

      {/* Delete Room Modal */}
      {deleteRoom && (
        <DeleteRoomModal
          propertyId={propertyId}
          room={deleteRoom}
          onClose={() => setDeleteRoom(null)}
          onDelete={loadData}
        />
      )}

      {/* Edit Property Modal */}
      {showEditProperty && (
        <EditPropertyModal
          property={property}
          onClose={() => setShowEditProperty(false)}
          onSave={() => {
            loadData();
            setShowEditProperty(false);
          }}
        />
      )}
    </div>
  );
}

function RoomModal({
  propertyId,
  room,
  onClose,
  onSave,
}: {
  propertyId: string;
  room: RoomWithTenant | null;
  onClose: () => void;
  onSave: () => void;
}) {
  const [formData, setFormData] = useState({
    name: room?.name || "",
    rent_amount: room?.rent_amount || 0,
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      if (room) {
        await api.updateRoom(propertyId, room.id, formData);
      } else {
        await api.createRoom(propertyId, formData);
      }
      onSave();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save room");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header flex items-center justify-between">
          <h2
            className="text-xl font-semibold"
            style={{ fontFamily: "var(--font-outfit)" }}
          >
            {room ? "Edit Room" : "Add Room"}
          </h2>
          <button onClick={onClose} className="btn btn-ghost p-2">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body space-y-4">
            {error && (
              <div className="p-3 bg-[var(--error-light)] text-[var(--error)] rounded-lg text-sm">
                {error}
              </div>
            )}

            <div>
              <label htmlFor="name" className="label">
                Room Name
              </label>
              <input
                id="name"
                type="text"
                value={formData.name}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, name: e.target.value }))
                }
                className="input"
                placeholder="e.g., Room 101, Unit A"
                required
              />
            </div>

            <div>
              <label htmlFor="rent" className="label">
                Monthly Rent
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]">
                  $
                </span>
                <input
                  id="rent"
                  type="number"
                  value={formData.rent_amount}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      rent_amount: parseFloat(e.target.value) || 0,
                    }))
                  }
                  className="input pl-8"
                  min="0"
                  step="0.01"
                  required
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
                  Saving...
                </>
              ) : room ? (
                "Save Changes"
              ) : (
                "Add Room"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function DeleteRoomModal({
  propertyId,
  room,
  onClose,
  onDelete,
}: {
  propertyId: string;
  room: RoomWithTenant;
  onClose: () => void;
  onDelete: () => void;
}) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleDelete = async () => {
    setError("");
    setIsLoading(true);

    try {
      await api.deleteRoom(propertyId, room.id);
      onDelete();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete room");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2
            className="text-xl font-semibold"
            style={{ fontFamily: "var(--font-outfit)" }}
          >
            Delete Room
          </h2>
        </div>

        <div className="modal-body">
          {error && (
            <div className="p-3 mb-4 bg-[var(--error-light)] text-[var(--error)] rounded-lg text-sm">
              {error}
            </div>
          )}
          <p className="text-[var(--text-secondary)]">
            Are you sure you want to delete{" "}
            <strong className="text-[var(--text-primary)]">{room.name}</strong>?
            This action cannot be undone.
          </p>
        </div>

        <div className="modal-footer">
          <button onClick={onClose} className="btn btn-secondary">
            Cancel
          </button>
          <button
            onClick={handleDelete}
            disabled={isLoading}
            className="btn btn-danger"
          >
            {isLoading ? (
              <>
                <div className="spinner" />
                Deleting...
              </>
            ) : (
              "Delete Room"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

function EditPropertyModal({
  property,
  onClose,
  onSave,
}: {
  property: PropertyWithStats;
  onClose: () => void;
  onSave: () => void;
}) {
  const [formData, setFormData] = useState({
    name: property.name,
    address: property.address,
    description: property.description || "",
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      await api.updateProperty(property.id, formData);
      onSave();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update property");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header flex items-center justify-between">
          <h2
            className="text-xl font-semibold"
            style={{ fontFamily: "var(--font-outfit)" }}
          >
            Edit Property
          </h2>
          <button onClick={onClose} className="btn btn-ghost p-2">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body space-y-4">
            {error && (
              <div className="p-3 bg-[var(--error-light)] text-[var(--error)] rounded-lg text-sm">
                {error}
              </div>
            )}

            <div>
              <label htmlFor="name" className="label">
                Property Name
              </label>
              <input
                id="name"
                type="text"
                value={formData.name}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, name: e.target.value }))
                }
                className="input"
                required
              />
            </div>

            <div>
              <label htmlFor="address" className="label">
                Address
              </label>
              <input
                id="address"
                type="text"
                value={formData.address}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, address: e.target.value }))
                }
                className="input"
                required
              />
            </div>

            <div>
              <label htmlFor="description" className="label">
                Description{" "}
                <span className="text-[var(--text-muted)]">(optional)</span>
              </label>
              <textarea
                id="description"
                value={formData.description}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, description: e.target.value }))
                }
                className="input min-h-[100px]"
              />
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
                  Saving...
                </>
              ) : (
                "Save Changes"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
