"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import api, { PropertyWithStats } from "@/lib/api";
import {
  Building2,
  Plus,
  MapPin,
  Users,
  DoorOpen,
  CreditCard,
  MoreVertical,
  Pencil,
  Trash2,
  X,
} from "lucide-react";

export default function PropertiesPage() {
  const [properties, setProperties] = useState<PropertyWithStats[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [editProperty, setEditProperty] = useState<PropertyWithStats | null>(null);
  const [deleteProperty, setDeleteProperty] = useState<PropertyWithStats | null>(null);

  useEffect(() => {
    loadProperties();
  }, []);

  const loadProperties = async () => {
    try {
      const res = await api.getProperties();
      setProperties(res.properties);
    } catch (error) {
      console.error("Failed to load properties:", error);
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

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title" style={{ fontFamily: "var(--font-outfit)" }}>
            Properties
          </h1>
          <p className="page-subtitle">Manage your rental properties and rooms.</p>
        </div>
        <button onClick={() => setShowAddModal(true)} className="btn btn-primary">
          <Plus className="w-4 h-4" />
          Add Property
        </button>
      </div>

      {/* Properties Grid */}
      {properties.length === 0 ? (
        <div className="card empty-state">
          <div className="empty-state-icon">
            <Building2 className="w-full h-full" />
          </div>
          <p className="empty-state-title">No properties yet</p>
          <p className="empty-state-description">
            Add your first property to start managing rooms and tenants.
          </p>
          <button onClick={() => setShowAddModal(true)} className="btn btn-primary">
            <Plus className="w-4 h-4" />
            Add Property
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {properties.map((property, i) => (
            <div
              key={property.id}
              className="card card-interactive animate-slide-up"
              style={{ animationDelay: `${i * 0.05}s` }}
            >
              <div className="p-5">
                <div className="flex items-start justify-between mb-4">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[var(--primary-100)] to-[var(--primary-200)] flex items-center justify-center">
                    <Building2 className="w-6 h-6 text-[var(--primary-600)]" />
                  </div>
                  <div className="relative group">
                    <button className="btn btn-ghost p-2">
                      <MoreVertical className="w-4 h-4" />
                    </button>
                    <div className="absolute right-0 top-full mt-1 w-36 bg-[var(--surface)] border border-[var(--border)] rounded-lg shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10">
                      <button
                        onClick={() => setEditProperty(property)}
                        className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left hover:bg-[var(--neutral-100)] rounded-t-lg"
                      >
                        <Pencil className="w-4 h-4" />
                        Edit
                      </button>
                      <button
                        onClick={() => setDeleteProperty(property)}
                        className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left text-[var(--error)] hover:bg-[var(--error-light)] rounded-b-lg"
                      >
                        <Trash2 className="w-4 h-4" />
                        Delete
                      </button>
                    </div>
                  </div>
                </div>

                <h3
                  className="font-semibold text-lg mb-1"
                  style={{ fontFamily: "var(--font-outfit)" }}
                >
                  {property.name}
                </h3>
                <p className="text-sm text-[var(--text-muted)] flex items-center gap-1 mb-4">
                  <MapPin className="w-3.5 h-3.5" />
                  {property.address}
                </p>

                <div className="grid grid-cols-3 gap-3 pt-4 border-t border-[var(--border)]">
                  <div className="text-center">
                    <div className="flex items-center justify-center gap-1 text-[var(--text-muted)] mb-1">
                      <DoorOpen className="w-3.5 h-3.5" />
                    </div>
                    <p className="font-semibold">{property.total_rooms}</p>
                    <p className="text-xs text-[var(--text-muted)]">Rooms</p>
                  </div>
                  <div className="text-center">
                    <div className="flex items-center justify-center gap-1 text-[var(--text-muted)] mb-1">
                      <Users className="w-3.5 h-3.5" />
                    </div>
                    <p className="font-semibold">{property.total_tenants}</p>
                    <p className="text-xs text-[var(--text-muted)]">Tenants</p>
                  </div>
                  <div className="text-center">
                    <div className="flex items-center justify-center gap-1 text-[var(--text-muted)] mb-1">
                      <CreditCard className="w-3.5 h-3.5" />
                    </div>
                    <p className="font-semibold text-sm">
                      {formatCurrency(property.monthly_expected_income)}
                    </p>
                    <p className="text-xs text-[var(--text-muted)]">Monthly</p>
                  </div>
                </div>

                <div className="mt-4">
                  <div className="flex items-center justify-between text-xs text-[var(--text-muted)] mb-1">
                    <span>Occupancy</span>
                    <span>
                      {property.occupied_rooms}/{property.total_rooms}
                    </span>
                  </div>
                  <div className="h-2 bg-[var(--neutral-200)] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-[var(--primary-500)] to-[var(--primary-600)] rounded-full transition-all"
                      style={{
                        width: `${
                          property.total_rooms > 0
                            ? (property.occupied_rooms / property.total_rooms) * 100
                            : 0
                        }%`,
                      }}
                    />
                  </div>
                </div>
              </div>

              <Link
                href={`/dashboard/properties/${property.id}`}
                className="block px-5 py-3 text-sm font-medium text-center text-[var(--primary-600)] border-t border-[var(--border)] hover:bg-[var(--primary-50)] transition-colors"
              >
                View Details
              </Link>
            </div>
          ))}
        </div>
      )}

      {/* Add/Edit Modal */}
      {(showAddModal || editProperty) && (
        <PropertyModal
          property={editProperty}
          onClose={() => {
            setShowAddModal(false);
            setEditProperty(null);
          }}
          onSave={loadProperties}
        />
      )}

      {/* Delete Confirmation */}
      {deleteProperty && (
        <DeleteModal
          property={deleteProperty}
          onClose={() => setDeleteProperty(null)}
          onDelete={loadProperties}
        />
      )}
    </div>
  );
}

function PropertyModal({
  property,
  onClose,
  onSave,
}: {
  property: PropertyWithStats | null;
  onClose: () => void;
  onSave: () => void;
}) {
  const [formData, setFormData] = useState({
    name: property?.name || "",
    address: property?.address || "",
    description: property?.description || "",
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      if (property) {
        await api.updateProperty(property.id, formData);
      } else {
        await api.createProperty(formData);
      }
      onSave();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save");
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
            {property ? "Edit Property" : "Add Property"}
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
                placeholder="e.g., Sunset Apartments"
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
                placeholder="e.g., 123 Main St, City, State"
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
                placeholder="Brief description of the property..."
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
              ) : property ? (
                "Save Changes"
              ) : (
                "Add Property"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function DeleteModal({
  property,
  onClose,
  onDelete,
}: {
  property: PropertyWithStats;
  onClose: () => void;
  onDelete: () => void;
}) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleDelete = async () => {
    setError("");
    setIsLoading(true);

    try {
      await api.deleteProperty(property.id);
      onDelete();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete");
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
            Delete Property
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
            <strong className="text-[var(--text-primary)]">{property.name}</strong>?
            This action cannot be undone.
          </p>
          {property.total_rooms > 0 && (
            <p className="mt-2 text-sm text-[var(--warning)]">
              Note: You must delete all rooms first before deleting this property.
            </p>
          )}
        </div>

        <div className="modal-footer">
          <button onClick={onClose} className="btn btn-secondary">
            Cancel
          </button>
          <button
            onClick={handleDelete}
            disabled={isLoading || property.total_rooms > 0}
            className="btn btn-danger"
          >
            {isLoading ? (
              <>
                <div className="spinner" />
                Deleting...
              </>
            ) : (
              "Delete Property"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
