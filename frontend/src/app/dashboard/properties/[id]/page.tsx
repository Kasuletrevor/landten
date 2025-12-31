"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import api, { PropertyWithStats, RoomWithTenant } from "@/lib/api";
import { useToast } from "@/components/toast-provider";
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
  ChevronDown,
  Layers,
  AlertTriangle,
} from "lucide-react";

// Supported currencies
const CURRENCIES = [
  { code: "UGX", symbol: "UGX", name: "Ugandan Shilling" },
  { code: "USD", symbol: "$", name: "US Dollar" },
  { code: "KES", symbol: "KES", name: "Kenyan Shilling" },
  { code: "TZS", symbol: "TZS", name: "Tanzanian Shilling" },
  { code: "RWF", symbol: "RWF", name: "Rwandan Franc" },
  { code: "EUR", symbol: "€", name: "Euro" },
  { code: "GBP", symbol: "£", name: "British Pound" },
];

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
  const [showBulkModal, setShowBulkModal] = useState(false);
  const [showRoomDropdown, setShowRoomDropdown] = useState(false);
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

  const formatCurrency = (amount: number, currencyCode: string = "UGX") => {
    const currency = CURRENCIES.find(c => c.code === currencyCode) || CURRENCIES[0];
    // For currencies with special symbols, use them; otherwise use the code
    if (["$", "€", "£"].includes(currency.symbol)) {
      return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: currencyCode,
        minimumFractionDigits: 0,
      }).format(amount);
    }
    // For currencies like UGX, KES, etc., format as "UGX 1,000,000"
    return `${currency.symbol} ${new Intl.NumberFormat("en-US", {
      minimumFractionDigits: 0,
    }).format(amount)}`;
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
        <div className="relative">
          <div className="flex">
            <button
              onClick={() => setShowAddRoom(true)}
              className="btn btn-primary rounded-r-none border-r-0"
            >
              <Plus className="w-4 h-4" />
              Add Room
            </button>
            <button
              onClick={() => setShowRoomDropdown(!showRoomDropdown)}
              className="btn btn-primary rounded-l-none px-2 border-l border-[var(--primary-700)]"
            >
              <ChevronDown className="w-4 h-4" />
            </button>
          </div>
          {showRoomDropdown && (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={() => setShowRoomDropdown(false)}
              />
              <div className="absolute right-0 top-full mt-1 w-48 bg-[var(--surface)] border border-[var(--border)] rounded-lg shadow-lg z-20">
                <button
                  onClick={() => {
                    setShowAddRoom(true);
                    setShowRoomDropdown(false);
                  }}
                  className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-left hover:bg-[var(--surface-hover)] rounded-t-lg"
                >
                  <Plus className="w-4 h-4" />
                  Single Room
                </button>
                <button
                  onClick={() => {
                    setShowBulkModal(true);
                    setShowRoomDropdown(false);
                  }}
                  className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-left hover:bg-[var(--surface-hover)] rounded-b-lg"
                >
                  <Layers className="w-4 h-4" />
                  Multiple Rooms
                </button>
              </div>
            </>
          )}
        </div>
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
                        {formatCurrency(room.rent_amount, room.currency)}/month
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

      {/* Bulk Room Modal */}
      {showBulkModal && (
        <BulkRoomModal
          propertyId={propertyId}
          onClose={() => setShowBulkModal(false)}
          onSave={loadData}
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
    currency: room?.currency || "UGX",
  });
  const [showCurrencyDropdown, setShowCurrencyDropdown] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const selectedCurrency = CURRENCIES.find(c => c.code === formData.currency) || CURRENCIES[0];

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
              <div className="flex gap-2">
                {/* Currency Dropdown */}
                <div className="relative">
                  <button
                    type="button"
                    onClick={() => setShowCurrencyDropdown(!showCurrencyDropdown)}
                    className="flex items-center gap-2 h-full px-3 border border-[var(--border)] rounded-xl bg-[var(--surface)] hover:bg-[var(--surface-hover)] transition-colors min-w-[100px]"
                  >
                    <span className="font-medium">{selectedCurrency.symbol}</span>
                    <ChevronDown className="w-4 h-4 text-[var(--text-muted)]" />
                  </button>
                  {showCurrencyDropdown && (
                    <div className="absolute top-full left-0 mt-1 w-56 max-h-60 overflow-y-auto bg-[var(--surface)] border border-[var(--border)] rounded-xl shadow-lg z-50">
                      {CURRENCIES.map((currency) => (
                        <button
                          key={currency.code}
                          type="button"
                          onClick={() => {
                            setFormData(prev => ({ ...prev, currency: currency.code }));
                            setShowCurrencyDropdown(false);
                          }}
                          className={`w-full flex items-center gap-3 px-4 py-2.5 hover:bg-[var(--surface-hover)] transition-colors text-left ${
                            formData.currency === currency.code ? "bg-[var(--primary-50)]" : ""
                          }`}
                        >
                          <span className="font-medium w-12">{currency.symbol}</span>
                          <span className="text-sm text-[var(--text-secondary)]">{currency.name}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                {/* Amount Input */}
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
                  className="input flex-1"
                  min="0"
                  step="0.01"
                  placeholder="0"
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

interface PriceRange {
  from: number;
  to: number;
  amount: number;
}

function BulkRoomModal({
  propertyId,
  onClose,
  onSave,
}: {
  propertyId: string;
  onClose: () => void;
  onSave: () => void;
}) {
  const { addToast } = useToast();
  const [formData, setFormData] = useState({
    prefix: "",
    fromNumber: "1",
    toNumber: "10",
    currency: "UGX",
  });
  const [priceRanges, setPriceRanges] = useState<PriceRange[]>([
    { from: 1, to: 10, amount: 0 },
  ]);
  const [showCurrencyDropdown, setShowCurrencyDropdown] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const selectedCurrency =
    CURRENCIES.find((c) => c.code === formData.currency) || CURRENCIES[0];

  // Detect padding from input (e.g., "01" -> 2, "001" -> 3, "1" -> 0)
  const detectPadding = (input: string): number => {
    if (input.startsWith("0") && input.length > 1) return input.length;
    return 0;
  };

  // Generate room name with padding
  const generateRoomName = (
    prefix: string,
    num: number,
    padding: number
  ): string => {
    const paddedNum =
      padding > 0 ? num.toString().padStart(padding, "0") : num.toString();
    return `${prefix}${paddedNum}`;
  };

  // Calculate total rooms
  const fromNum = parseInt(formData.fromNumber) || 0;
  const toNum = parseInt(formData.toNumber) || 0;
  const totalRooms = Math.max(0, toNum - fromNum + 1);
  const padding = detectPadding(formData.fromNumber);

  // Find gaps in price range coverage
  const findGaps = (): [number, number][] => {
    if (priceRanges.length === 0) return [[fromNum, toNum]];

    const gaps: [number, number][] = [];
    const sorted = [...priceRanges].sort((a, b) => a.from - b.from);

    let currentEnd = fromNum - 1;
    for (const range of sorted) {
      if (range.from > currentEnd + 1) {
        gaps.push([currentEnd + 1, range.from - 1]);
      }
      currentEnd = Math.max(currentEnd, range.to);
    }

    if (currentEnd < toNum) {
      gaps.push([currentEnd + 1, toNum]);
    }

    return gaps;
  };

  // Get next available range for smart pre-fill
  const getNextAvailableRange = (): { from: number; to: number } => {
    if (priceRanges.length === 0) return { from: fromNum, to: toNum };

    const maxTo = Math.max(...priceRanges.map((r) => r.to));
    if (maxTo < toNum) {
      return { from: maxTo + 1, to: toNum };
    }
    return { from: toNum, to: toNum };
  };

  const gaps = findGaps();
  const hasGaps = gaps.length > 0 && totalRooms > 0;

  // Generate preview
  const generatePreview = (): string => {
    if (totalRooms <= 0) return "";
    if (totalRooms <= 5) {
      return Array.from({ length: totalRooms }, (_, i) =>
        generateRoomName(formData.prefix, fromNum + i, padding)
      ).join(", ");
    }
    const first = generateRoomName(formData.prefix, fromNum, padding);
    const second = generateRoomName(formData.prefix, fromNum + 1, padding);
    const third = generateRoomName(formData.prefix, fromNum + 2, padding);
    const last = generateRoomName(formData.prefix, toNum, padding);
    return `${first}, ${second}, ${third} ... ${last}`;
  };

  const handleAddPriceRange = () => {
    const nextRange = getNextAvailableRange();
    setPriceRanges([...priceRanges, { ...nextRange, amount: 0 }]);
  };

  const handleRemovePriceRange = (index: number) => {
    setPriceRanges(priceRanges.filter((_, i) => i !== index));
  };

  const handlePriceRangeChange = (
    index: number,
    field: keyof PriceRange,
    value: number
  ) => {
    setPriceRanges(
      priceRanges.map((range, i) =>
        i === index ? { ...range, [field]: value } : range
      )
    );
  };

  // Sync first price range with form data
  const handleFromToChange = (field: "fromNumber" | "toNumber", value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    const newFrom = field === "fromNumber" ? parseInt(value) || 0 : fromNum;
    const newTo = field === "toNumber" ? parseInt(value) || 0 : toNum;
    
    // Update first price range to match
    if (priceRanges.length === 1) {
      setPriceRanges([{ ...priceRanges[0], from: newFrom, to: newTo }]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (totalRooms <= 0 || totalRooms > 500) return;

    setError("");
    setIsLoading(true);

    try {
      const response = await api.createRoomsBulk(propertyId, {
        prefix: formData.prefix,
        from_number: fromNum,
        to_number: toNum,
        currency: formData.currency,
        price_ranges: priceRanges.map((r) => ({
          from_number: r.from,
          to_number: r.to,
          rent_amount: r.amount,
        })),
        padding,
      });

      addToast({
        type: "success",
        title: `${response.total_created} rooms created`,
        message:
          response.warnings.length > 0 ? response.warnings[0] : undefined,
      });

      onSave();
      onClose();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to create rooms"
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal max-w-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header flex items-center justify-between">
          <h2
            className="text-xl font-semibold"
            style={{ fontFamily: "var(--font-outfit)" }}
          >
            Add Multiple Rooms
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

            {/* Room Numbers */}
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label htmlFor="prefix" className="label">
                  Prefix <span className="text-[var(--text-muted)]">(optional)</span>
                </label>
                <input
                  id="prefix"
                  type="text"
                  value={formData.prefix}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, prefix: e.target.value }))
                  }
                  className="input"
                  placeholder="e.g., Room, L"
                />
              </div>
              <div>
                <label htmlFor="fromNumber" className="label">
                  From
                </label>
                <input
                  id="fromNumber"
                  type="text"
                  value={formData.fromNumber}
                  onChange={(e) => handleFromToChange("fromNumber", e.target.value)}
                  className="input"
                  placeholder="1"
                />
              </div>
              <div>
                <label htmlFor="toNumber" className="label">
                  To
                </label>
                <input
                  id="toNumber"
                  type="text"
                  value={formData.toNumber}
                  onChange={(e) => handleFromToChange("toNumber", e.target.value)}
                  className="input"
                  placeholder="10"
                />
              </div>
            </div>

            {/* Room count warning */}
            {totalRooms > 500 && (
              <div className="flex items-center gap-2 p-3 bg-[var(--error-light)] text-[var(--error)] rounded-lg text-sm">
                <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                <span>Maximum 500 rooms per batch. Please reduce the range.</span>
              </div>
            )}

            {/* Preview */}
            {totalRooms > 0 && totalRooms <= 500 && (
              <div className="p-3 bg-[var(--surface-inset)] rounded-lg">
                <p className="text-sm text-[var(--text-muted)] mb-1">
                  Preview ({totalRooms} rooms):
                </p>
                <p className="text-sm font-medium">{generatePreview()}</p>
              </div>
            )}

            {/* Currency and First Price */}
            <div>
              <label className="label">Monthly Rent</label>
              <div className="flex gap-2">
                {/* Currency Dropdown */}
                <div className="relative">
                  <button
                    type="button"
                    onClick={() => setShowCurrencyDropdown(!showCurrencyDropdown)}
                    className="flex items-center gap-2 h-full px-3 border border-[var(--border)] rounded-xl bg-[var(--surface)] hover:bg-[var(--surface-hover)] transition-colors min-w-[100px]"
                  >
                    <span className="font-medium">{selectedCurrency.symbol}</span>
                    <ChevronDown className="w-4 h-4 text-[var(--text-muted)]" />
                  </button>
                  {showCurrencyDropdown && (
                    <div className="absolute top-full left-0 mt-1 w-56 max-h-60 overflow-y-auto bg-[var(--surface)] border border-[var(--border)] rounded-xl shadow-lg z-50">
                      {CURRENCIES.map((currency) => (
                        <button
                          key={currency.code}
                          type="button"
                          onClick={() => {
                            setFormData((prev) => ({
                              ...prev,
                              currency: currency.code,
                            }));
                            setShowCurrencyDropdown(false);
                          }}
                          className={`w-full flex items-center gap-3 px-4 py-2.5 hover:bg-[var(--surface-hover)] transition-colors text-left ${
                            formData.currency === currency.code
                              ? "bg-[var(--primary-50)]"
                              : ""
                          }`}
                        >
                          <span className="font-medium w-12">
                            {currency.symbol}
                          </span>
                          <span className="text-sm text-[var(--text-secondary)]">
                            {currency.name}
                          </span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                {/* Amount Input for first range */}
                <input
                  type="number"
                  value={priceRanges[0]?.amount || 0}
                  onChange={(e) =>
                    handlePriceRangeChange(
                      0,
                      "amount",
                      parseFloat(e.target.value) || 0
                    )
                  }
                  className="input flex-1"
                  min="0"
                  step="0.01"
                  placeholder="0"
                />
              </div>
            </div>

            {/* Additional Price Ranges */}
            {priceRanges.length > 1 && (
              <div className="space-y-3">
                <p className="text-sm font-medium text-[var(--text-secondary)]">
                  Different prices for specific rooms:
                </p>
                {priceRanges.slice(1).map((range, idx) => (
                  <div
                    key={idx + 1}
                    className="flex items-center gap-2 p-3 bg-[var(--surface-inset)] rounded-lg"
                  >
                    <div className="flex-1 grid grid-cols-3 gap-2">
                      <div>
                        <label className="text-xs text-[var(--text-muted)]">
                          From
                        </label>
                        <input
                          type="number"
                          value={range.from}
                          onChange={(e) =>
                            handlePriceRangeChange(
                              idx + 1,
                              "from",
                              parseInt(e.target.value) || 0
                            )
                          }
                          className="input py-1.5 text-sm"
                          min={fromNum}
                          max={toNum}
                        />
                      </div>
                      <div>
                        <label className="text-xs text-[var(--text-muted)]">
                          To
                        </label>
                        <input
                          type="number"
                          value={range.to}
                          onChange={(e) =>
                            handlePriceRangeChange(
                              idx + 1,
                              "to",
                              parseInt(e.target.value) || 0
                            )
                          }
                          className="input py-1.5 text-sm"
                          min={fromNum}
                          max={toNum}
                        />
                      </div>
                      <div>
                        <label className="text-xs text-[var(--text-muted)]">
                          Amount
                        </label>
                        <input
                          type="number"
                          value={range.amount}
                          onChange={(e) =>
                            handlePriceRangeChange(
                              idx + 1,
                              "amount",
                              parseFloat(e.target.value) || 0
                            )
                          }
                          className="input py-1.5 text-sm"
                          min="0"
                          step="0.01"
                        />
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleRemovePriceRange(idx + 1)}
                      className="btn btn-ghost p-1.5 text-[var(--text-muted)] hover:text-[var(--error)]"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Add Price Range Button */}
            <button
              type="button"
              onClick={handleAddPriceRange}
              className="text-sm text-[var(--primary-600)] hover:text-[var(--primary-700)] font-medium"
            >
              + Add another price range
            </button>

            {/* Gap Warning */}
            {hasGaps && (
              <div className="flex items-start gap-2 p-3 bg-[var(--warning-light)] text-[var(--warning-dark)] rounded-lg text-sm">
                <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium">Some rooms have no price set</p>
                  <p className="text-xs mt-0.5">
                    Rooms {gaps.map(([f, t]) => (f === t ? f : `${f}-${t}`)).join(", ")}{" "}
                    will use the default price (first range).
                  </p>
                </div>
              </div>
            )}
          </div>

          <div className="modal-footer">
            <button type="button" onClick={onClose} className="btn btn-secondary">
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading || totalRooms <= 0 || totalRooms > 500}
              className="btn btn-primary"
            >
              {isLoading ? (
                <>
                  <div className="spinner" />
                  Creating...
                </>
              ) : (
                `Create ${totalRooms} Room${totalRooms !== 1 ? "s" : ""}`
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
