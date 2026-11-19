"use client";
import { Area, AreaChart, Bar, BarChart, Brush, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const tick = { fill: "#8492a6", fontSize: 11 };
const tooltip = { contentStyle: { background: "#111923", border: "1px solid #293544", borderRadius: 12, color: "#e7eef5" }, itemStyle: { color: "#e7eef5" } };
const brl = (v: number) => `R$ ${Number(v).toLocaleString("pt-BR", { maximumFractionDigits: 0 })}`;
const compact = (v: number) => (v >= 1e6 ? `R$${(v / 1e6).toFixed(1)}M` : `R$${Math.round(v / 1000)}k`);

export type RevenueMode = "daily" | "avg7" | "cumulative";

export function toSeries(data: { iso: string; day: string; revenue: number; orders: number }[], mode: RevenueMode) {
  let running = 0;
  return data.map((d, i) => {
    running += d.revenue;
    const win = data.slice(Math.max(0, i - 6), i + 1);
    const avg = win.reduce((a, r) => a + r.revenue, 0) / win.length;
    return { ...d, value: mode === "daily" ? d.revenue : mode === "avg7" ? avg : running };
  });
}

export function RevenueChart({ data, mode }: { data: any[]; mode: RevenueMode }) {
  const series = toSeries(data, mode);
  const label = mode === "daily" ? "Revenue" : mode === "avg7" ? "7-day average" : "Cumulative revenue";
  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={series} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="rev" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#2dd4a7" stopOpacity={0.35} />
            <stop offset="100%" stopColor="#2dd4a7" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="#25303d" vertical={false} />
        <XAxis dataKey="day" tick={tick} axisLine={false} tickLine={false} minTickGap={30} />
        <YAxis tick={tick} axisLine={false} tickLine={false} tickFormatter={compact} />
        <Tooltip {...tooltip} formatter={(v) => [brl(Number(v)), label]} labelFormatter={(l, p: any) => `${l}${p?.[0] ? ` · ${p[0].payload.orders} orders` : ""}`} />
        <Area type="monotone" dataKey="value" stroke="#2dd4a7" strokeWidth={2.5} fill="url(#rev)" dot={false} activeDot={{ r: 5 }} animationDuration={400} />
        {series.length > 20 && <Brush dataKey="day" height={22} stroke="#2dd4a7" fill="#0f1720" travellerWidth={8} />}
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function ProductChart({ data, selected, onSelect }: { data: { product: string; category_key: string; revenue: number }[]; selected: string | null; onSelect: (key: string | null) => void }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} layout="vertical" margin={{ top: 0, right: 14, bottom: 0, left: 0 }}>
        <CartesianGrid stroke="#25303d" horizontal={false} />
        <XAxis type="number" tick={tick} axisLine={false} tickLine={false} tickFormatter={compact} />
        <YAxis type="category" dataKey="product" width={110} tick={tick} axisLine={false} tickLine={false} />
        <Tooltip {...tooltip} cursor={{ fill: "#ffffff10" }} formatter={(v) => [brl(Number(v)), "Revenue"]} />
        <Bar dataKey="revenue" radius={[0, 5, 5, 0]} cursor="pointer" onClick={(d: any) => onSelect(selected === d.category_key ? null : d.category_key)}>
          {data.map((d, i) => <Cell key={i} fill={selected ? (selected === d.category_key ? "#2dd4a7" : "#2b4a49") : i === 0 ? "#2dd4a7" : "#208c79"} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
