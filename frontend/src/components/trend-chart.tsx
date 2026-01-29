"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { MonthlyStats } from "@/lib/api";

interface TrendChartProps {
  data: MonthlyStats[];
  currency: string;
}

/**
 * Format month string "YYYY-MM" to short month name
 */
function formatMonth(monthStr: string): string {
  const [year, month] = monthStr.split("-");
  const date = new Date(parseInt(year), parseInt(month) - 1);
  return date.toLocaleDateString("en-US", { month: "short" });
}

/**
 * Format currency amount with proper locale
 */
function formatAmount(amount: number, currency: string): string {
  if (currency === "UGX" || currency === "KES" || currency === "TZS" || currency === "RWF") {
    return `${currency} ${amount.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

/**
 * Custom tooltip for the chart
 */
function CustomTooltip({
  active,
  payload,
  currency,
}: {
  active?: boolean;
  payload?: Array<{ value: number; dataKey: string; payload: MonthlyStats & { monthLabel: string } }>;
  currency: string;
}) {
  if (!active || !payload || !payload.length) return null;

  const data = payload[0].payload;

  return (
    <div
      className="card"
      style={{
        padding: "0.875rem 1rem",
        minWidth: "180px",
        boxShadow: "var(--shadow-lg)",
        border: "1px solid var(--border-strong)",
      }}
    >
      <p
        style={{
          fontFamily: "var(--font-outfit)",
          fontWeight: 600,
          fontSize: "0.875rem",
          color: "var(--text-primary)",
          marginBottom: "0.5rem",
        }}
      >
        {data.monthLabel}
      </p>
      <div style={{ display: "flex", flexDirection: "column", gap: "0.375rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem" }}>
          <span style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>
            Expected
          </span>
          <span style={{ fontSize: "0.8125rem", fontWeight: 500, color: "var(--text-secondary)" }}>
            {formatAmount(data.expected, currency)}
          </span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem" }}>
          <span style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>
            Received
          </span>
          <span style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--success)" }}>
            {formatAmount(data.received, currency)}
          </span>
        </div>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: "1rem",
            paddingTop: "0.375rem",
            borderTop: "1px solid var(--border)",
            marginTop: "0.25rem",
          }}
        >
          <span style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>
            Collection
          </span>
          <span
            style={{
              fontSize: "0.8125rem",
              fontWeight: 600,
              color: data.collection_rate >= 80 ? "var(--success)" : data.collection_rate >= 50 ? "var(--warning)" : "var(--error)",
            }}
          >
            {data.collection_rate.toFixed(0)}%
          </span>
        </div>
      </div>
    </div>
  );
}

export default function TrendChart({ data, currency }: TrendChartProps) {
  // Transform data for the chart
  const chartData = data.map((item) => ({
    ...item,
    monthLabel: formatMonth(item.month),
  }));

  // Get the primary color for the chart bars
  const barColor = "var(--primary-500)";
  const barColorHover = "var(--primary-600)";

  return (
    <div style={{ width: "100%", height: 240 }}>
      <ResponsiveContainer>
        <BarChart
          data={chartData}
          margin={{ top: 8, right: 8, left: 0, bottom: 8 }}
          barCategoryGap="25%"
        >
          <defs>
            <linearGradient id="barGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#c67652" stopOpacity={1} />
              <stop offset="100%" stopColor="#b85d3b" stopOpacity={1} />
            </linearGradient>
            <linearGradient id="expectedGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#d4d1c9" stopOpacity={0.6} />
              <stop offset="100%" stopColor="#b5b1a6" stopOpacity={0.4} />
            </linearGradient>
          </defs>
          <CartesianGrid
            strokeDasharray="4 4"
            stroke="var(--border)"
            vertical={false}
          />
          <XAxis
            dataKey="monthLabel"
            axisLine={false}
            tickLine={false}
            tick={{
              fill: "var(--text-muted)",
              fontSize: 12,
              fontWeight: 500,
            }}
            dy={8}
          />
          <YAxis
            axisLine={false}
            tickLine={false}
            tick={{
              fill: "var(--text-muted)",
              fontSize: 11,
            }}
            tickFormatter={(value) => {
              if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
              if (value >= 1000) return `${(value / 1000).toFixed(0)}K`;
              return value.toString();
            }}
            width={48}
          />
          <Tooltip
            content={<CustomTooltip currency={currency} />}
            cursor={{ fill: "var(--surface-inset)", radius: 6 }}
          />
          {/* Expected amount bar (background) */}
          <Bar
            dataKey="expected"
            fill="url(#expectedGradient)"
            radius={[6, 6, 0, 0]}
            name="Expected"
          />
          {/* Received amount bar (foreground overlay effect using stacked positioning) */}
          <Bar
            dataKey="received"
            fill="url(#barGradient)"
            radius={[6, 6, 0, 0]}
            name="Received"
          >
            {chartData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill="url(#barGradient)"
                style={{ filter: "drop-shadow(0 2px 4px rgba(198, 118, 82, 0.25))" }}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
