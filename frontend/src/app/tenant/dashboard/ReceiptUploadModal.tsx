import { useState } from "react";
import api, { Payment, PaymentStatus } from "@/lib/api";
import { Upload, X, FileText, CheckCircle, AlertCircle } from "lucide-react";

interface ReceiptUploadModalProps {
  payment: Payment;
  onClose: () => void;
  onSuccess: (payment: Payment) => void;
}

export default function ReceiptUploadModal({
  payment,
  onClose,
  onSuccess,
}: ReceiptUploadModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState("");

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError("");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setIsUploading(true);
    setError("");

    try {
      const updatedPayment = await api.uploadPaymentReceipt(payment.id, file);
      onSuccess(updatedPayment);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Failed to upload receipt");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 backdrop-blur-sm animate-fade-in">
      <div className="bg-[var(--surface)] rounded-2xl w-full max-w-md shadow-2xl border border-[var(--border)] overflow-hidden animate-scale-up">
        <div className="p-6 border-b border-[var(--border)] flex items-center justify-between bg-[var(--surface-inset)]">
          <h3 className="text-lg font-semibold" style={{ fontFamily: "var(--font-outfit)" }}>
            Upload Proof of Payment
          </h3>
          <button
            onClick={onClose}
            className="p-2 hover:bg-[var(--background)] rounded-full transition-colors text-[var(--text-muted)] hover:text-[var(--text-primary)]"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6">
          {error && (
            <div className="mb-6 p-4 bg-[var(--error-light)] text-[var(--error)] rounded-xl flex items-start gap-3 text-sm">
              <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <div className="mb-6">
             <div className="p-4 bg-[var(--primary-100)] rounded-xl mb-4">
                 <p className="text-sm text-[var(--primary-700)] font-medium mb-1">Payment Details</p>
                 <div className="flex justify-between items-center">
                    <span className="text-2xl font-bold text-[var(--primary-900)]">
                        {new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(payment.amount_due)}
                    </span>
                    <span className="text-xs bg-white/50 px-2 py-1 rounded-md text-[var(--primary-800)]">
                        Due: {new Date(payment.due_date).toLocaleDateString()}
                    </span>
                 </div>
             </div>
             
             <p className="text-sm text-[var(--text-secondary)] mb-4">
               Please upload a screenshot or PDF of your bank transfer receipt. Once uploaded, the landlord will verify the payment.
             </p>

            <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-[var(--border)] rounded-2xl cursor-pointer hover:bg-[var(--surface-inset)] transition-colors group relative overflow-hidden">
                {file ? (
                    <div className="flex flex-col items-center justify-center text-[var(--success)] z-10">
                        <CheckCircle className="w-8 h-8 mb-2" />
                        <span className="text-sm font-medium truncate max-w-[200px]">{file.name}</span>
                    </div>
                ) : (
                    <div className="flex flex-col items-center justify-center pt-5 pb-6 text-[var(--text-muted)] group-hover:text-[var(--primary-500)] transition-colors z-10">
                        <Upload className="w-8 h-8 mb-2" />
                        <p className="text-sm font-medium">Click to upload receipt</p>
                        <p className="text-xs mt-1 text-[var(--text-secondary)]">PNG, JPG or PDF</p>
                    </div>
                )}
                <input 
                    type="file" 
                    className="hidden" 
                    accept="image/png, image/jpeg, application/pdf"
                    onChange={handleFileChange}
                />
            </label>
          </div>

          <div className="flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="btn btn-ghost flex-1"
              disabled={isUploading}
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={!file || isUploading}
              className="btn btn-primary flex-1 flex items-center justify-center gap-2"
            >
              {isUploading ? (
                <>
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Uploading...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" />
                  Submit Receipt
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
