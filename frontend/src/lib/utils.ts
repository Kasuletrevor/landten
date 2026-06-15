/**
 * Shared formatting helpers used across the frontend.
 */

const ZERO_DECIMAL_CURRENCIES = new Set(["UGX", "KES", "TZS", "RWF"]);

/**
 * Format an amount as a human-readable currency string.
 *
 * For common zero-decimal East African currencies the output is rendered as
 * "CODE 1,234,567" (no fractional digits). All other currencies use the
 * browser's Intl.NumberFormat with the supplied currency code.
 */
export function formatCurrency(amount: number, currency: string = "UGX"): string {
  const safeAmount = Number.isFinite(amount) ? amount : 0;
  const code = (currency || "UGX").toUpperCase();

  if (ZERO_DECIMAL_CURRENCIES.has(code)) {
    return `${code} ${safeAmount.toLocaleString("en-US", {
      maximumFractionDigits: 0,
      minimumFractionDigits: 0,
    })}`;
  }

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: code,
    minimumFractionDigits: 0,
  }).format(safeAmount);
}
