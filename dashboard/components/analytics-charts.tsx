"use client";
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const tick = { fill: "#8492a6", fontSize: 11 };
const tooltip = { contentStyle: { background: "#111923", border: "1px solid #293544", borderRadius: 12, color: "#e7eef5" }, itemStyle: { color: "#e7eef5" } };
export function RevenueChart({ data }: { data: { day: string; revenue: number }[] }) {
  return <ResponsiveContainer width="100%" height="100%"><LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}><CartesianGrid stroke="#25303d" vertical={false} /><XAxis dataKey="day" tick={tick} axisLine={false} tickLine={false} minTickGap={30} /><YAxis tick={tick} axisLine={false} tickLine={false} tickFormatter={(v) => `R$${Math.round(v / 1000)}k`} /><Tooltip {...tooltip} formatter={(v) => [`R$ ${Number(v).toLocaleString("pt-BR", { maximumFractionDigits: 0 })}`, "Revenue"]} /><Line type="monotone" dataKey="revenue" stroke="#2dd4a7" strokeWidth={2.5} dot={false} activeDot={{ r: 5 }} /></LineChart></ResponsiveContainer>;
}
export function ProductChart({ data }: { data: { product: string; revenue: number }[] }) {
  return <ResponsiveContainer width="100%" height="100%"><BarChart data={data} layout="vertical" margin={{ top: 0, right: 14, bottom: 0, left: 0 }}><CartesianGrid stroke="#25303d" horizontal={false} /><XAxis type="number" tick={tick} axisLine={false} tickLine={false} tickFormatter={(v) => `R$${Math.round(v / 1000)}k`} /><YAxis type="category" dataKey="product" width={104} tick={tick} axisLine={false} tickLine={false} /><Tooltip {...tooltip} formatter={(v) => [`R$ ${Number(v).toLocaleString("pt-BR", { maximumFractionDigits: 0 })}`, "Revenue"]} /><Bar dataKey="revenue" radius={[0, 5, 5, 0]}>{data.map((_, i) => <Cell key={i} fill={i === 0 ? "#2dd4a7" : "#208c79"} />)}</Bar></BarChart></ResponsiveContainer>;
}
