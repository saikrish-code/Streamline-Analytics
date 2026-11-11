"use client";
import useSWR from "swr";
import { Activity, ArrowDownRight, ArrowUpRight, Boxes, CircleAlert, RefreshCw, ShoppingBag, Users } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { RevenueChart, ProductChart } from "@/components/analytics-charts";

const fetcher = (url: string) => fetch(url).then(async r => { if (!r.ok) throw new Error("Analytics data is unavailable"); return r.json(); });
const money = (value: number) => `R$ ${value.toLocaleString("pt-BR", { maximumFractionDigits: 0 })}`;
const number = (value: number) => value.toLocaleString("en-US");
function Metric({ label, value, foot, icon: Icon, trend }: { label: string; value: string; foot: string; icon: typeof Activity; trend?: string }) { return <Card><CardContent className="flex items-start justify-between p-5"><div><p className="text-sm text-slate-400">{label}</p><p className="mt-3 text-2xl font-semibold tracking-tight">{value}</p><p className="mt-2 flex items-center gap-1 text-xs text-slate-400">{trend && <span className="text-emerald-400"><ArrowUpRight size={14} /></span>}{foot}</p></div><div className="rounded-lg bg-slate-800 p-2.5 text-emerald-300"><Icon size={18} /></div></CardContent></Card>; }

export default function Dashboard() {
  const { data, error, isLoading, mutate } = useSWR("/api/analytics", fetcher, { refreshInterval: 120000 });
  const metrics = data?.metrics;
  return <main className="mx-auto min-h-screen max-w-[1440px] px-5 py-8 md:px-10 md:py-10">
    <header className="mb-8 flex flex-wrap items-center justify-between gap-4"><div><div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-[.2em] text-emerald-300"><span className="h-2 w-2 rounded-full bg-emerald-400" /> Streamline</div><h1 className="text-3xl font-semibold tracking-tight">Commerce overview</h1><p className="mt-2 text-sm text-slate-400">Olist marketplace performance · Brazil</p></div><Button variant="outline" onClick={() => mutate()}><RefreshCw size={15} /> Refresh data</Button></header>
    {error && <div className="mb-5 flex items-center gap-2 rounded-lg border border-rose-900 bg-rose-950/40 p-3 text-sm text-rose-200"><CircleAlert size={16} /> Could not load analytics. Check DATABASE_URL and run dbt plus dashboard SQL setup.</div>}
    <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <Metric label="Gross merchandise value" value={metrics ? money(metrics.revenue) : "—"} foot="Delivered order items" icon={Activity} trend="" />
      <Metric label="Orders" value={metrics ? number(metrics.orders) : "—"} foot="Unique order IDs" icon={ShoppingBag} />
      <Metric label="Active customers" value={metrics ? number(metrics.customers) : "—"} foot="Customers with an order" icon={Users} />
      <Metric label="At-risk in sample" value={data?.model_version ? number(metrics.at_risk) : "—"} foot={data?.model_version ? "Elevated risk · up to 40 scored" : "Churn model unavailable"} icon={ArrowDownRight} />
    </section>
    <section className="mt-5 grid gap-5 xl:grid-cols-[1.65fr_1fr]">
      <Card><CardHeader className="flex-row items-start justify-between"><div><CardTitle>Revenue over time</CardTitle><p className="mt-1 text-sm text-slate-400">Daily delivered revenue · latest 90 days</p></div><span className="rounded-full bg-emerald-950 px-2.5 py-1 text-xs text-emerald-300">BRL</span></CardHeader><CardContent><div className="h-[280px]">{data && <RevenueChart data={data.revenue} />}</div></CardContent></Card>
      <Card><CardHeader><CardTitle>Top products</CardTitle><p className="text-sm text-slate-400">Revenue by product category</p></CardHeader><CardContent><div className="h-[280px]">{data && <ProductChart data={data.products} />}</div></CardContent></Card>
    </section>
    <section className="mt-5 grid gap-5 xl:grid-cols-[1.4fr_1fr]">
      <Card><CardHeader className="flex-row items-center justify-between"><div><CardTitle>Customer cohorts & churn risk</CardTitle><p className="mt-1 text-sm text-slate-400">Latest customer activity · 90-day churn probability</p></div><span className="flex items-center gap-1.5 text-xs text-slate-400"><span className="h-2 w-2 rounded-full bg-amber-400" /> High risk</span></CardHeader><CardContent><div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead className="text-xs text-slate-500"><tr><th className="pb-3 font-medium">Customer</th><th className="pb-3 font-medium">Cohort</th><th className="pb-3 font-medium">Last order</th><th className="pb-3 font-medium">Orders</th><th className="pb-3 text-right font-medium">Churn risk</th></tr></thead><tbody>{(data?.risk ?? []).map((row: any) => <tr key={row.customer_id} className="border-t"><td className="py-3 font-mono text-xs text-slate-300">{row.customer_id.slice(0, 8)}…</td><td className="py-3 text-slate-400">{row.cohort}</td><td className="py-3 text-slate-400">{row.recency_days}d ago</td><td className="py-3 text-slate-300">{row.frequency}</td><td className="py-3 text-right"><span className={`rounded-full px-2 py-1 text-xs ${row.churn_probability >= 0.65 ? "bg-amber-950 text-amber-300" : "bg-slate-800 text-slate-300"}`}>{Math.round(row.churn_probability * 100)}%</span></td></tr>)}{!data?.risk?.length && <tr><td colSpan={5} className="py-9 text-center text-slate-500">{isLoading ? "Loading customer scores…" : "No customer predictions available"}</td></tr>}</tbody></table></div><p className="mt-3 text-xs text-slate-500">{data?.model_version ? `Churn model v${data.model_version}` : "Churn API unavailable · scores omitted"}</p></CardContent></Card>
      <Card><CardHeader><CardTitle>Order funnel</CardTitle><p className="text-sm text-slate-400">Orders by fulfillment milestone</p></CardHeader><CardContent><div className="space-y-5">{(data?.funnel ?? []).map((stage: any, i: number) => { const max = data?.funnel?.[0]?.orders || 1; return <div key={stage.stage}><div className="mb-2 flex justify-between text-sm"><span className="flex items-center gap-2 text-slate-300"><span className="text-xs text-slate-500">0{i + 1}</span>{stage.stage}</span><span className="text-slate-400">{number(stage.orders)} <span className="text-slate-600">· {Math.round(stage.orders / max * 100)}%</span></span></div><div className="h-2 overflow-hidden rounded-full bg-slate-800"><div className="h-full rounded-full bg-emerald-400" style={{ width: `${stage.orders / max * 100}%`, opacity: 1 - i * 0.12 }} /></div></div>; })}{!data?.funnel?.length && <div className="py-9 text-center text-sm text-slate-500">{isLoading ? "Loading order funnel…" : "No funnel data"}</div>}</div></CardContent></Card>
    </section>
    <footer className="mt-8 flex items-center justify-between text-xs text-slate-600"><span className="flex items-center gap-2"><Boxes size={14} /> Data sourced from marts schema</span><span>{data?.updated_at ? `Updated ${new Date(data.updated_at).toLocaleTimeString()}` : ""}</span></footer>
  </main>;
}
