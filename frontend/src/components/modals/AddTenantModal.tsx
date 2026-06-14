"use client";

import { useState, useCallback, useEffect } from "react";
import api, { PropertyWithStats } from "@/lib/api";
import { X, ChevronRight } from "lucide-react";

export function AddTenantModal({
  properties,
  initialPropertyId = "",
  initialRoomId = "",
  onClose,
  onSave,
}: {
  properties: PropertyWithStats[];
  initialPropertyId?: string;
  initialRoomId?: string;
  onClose: () => void;
  onSave: () => void;
}) {
  const [step, setStep] = useState(1);
  const [selectedProperty, setSelectedProperty] = useState(initialPropertyId);
  const [rooms, setRooms] = useState<{ id: string; name: string; rent_amount: number; currency: string }[]>([]);
  const [formData, setFormData] = useState({
    room_id: initialRoomId,
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

  const loadRooms = useCallback(async () => {
    try {
      const res = await api.getRooms(selectedProperty);
      // Only show vacant rooms, unless initialRoomId is provided and we want to ensure it's in the list
      const vacantRooms = res.rooms.filter((r) => !r.is_occupied || r.id === initialRoomId);
      setRooms(vacantRooms);
      
      // If we have an initialRoomId, ensure it's selected and we grab its rent amount
      if (initialRoomId) {
        const room = vacantRooms.find(r => r.id === initialRoomId);
        if (room) {
          setFormData((prev) => ({ ...prev, room_id: room.id }));
          setScheduleData((prev) => ({ ...prev, amount: room.rent_amount }));
        }
      } else if (vacantRooms.length > 0) {
        setFormData((prev) => ({ ...prev, room_id: vacantRooms[0].id }));
        setScheduleData((prev) => ({ ...prev, amount: vacantRooms[0].rent_amount }));
      } else {
        setFormData((prev) => ({ ...prev, room_id: "" }));
        setScheduleData((prev) => ({ ...prev, amount: 0 }));
      }
    } catch (error) {
      console.error("Failed to load rooms:", error);
    }
  }, [selectedProperty, initialRoomId]);

  useEffect(() => {
    if (selectedProperty) {
      void loadRooms();
    } else {
      setRooms([]);
      setFormData((prev) => ({ ...prev, room_id: "" }));
    }
  }, [loadRooms, selectedProperty]);

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
                  onChange={(e) => {
                    setSelectedProperty(e.target.value);
                  }}
                  className="input"
                  required
                  disabled={!!initialPropertyId}
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
                      disabled={!!initialRoomId}
                    >
                      <option value="" disabled>Select a room</option>
                      {rooms.map((room) => (
                        <option key={room.id} value={room.id}>
                          {room.name} — {room.currency} {room.rent_amount.toLocaleString()}/month
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
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)] font-medium text-sm">
                      {rooms.find(r => r.id === formData.room_id)?.currency || "UGX"}
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
                      className="input !pl-16"
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
