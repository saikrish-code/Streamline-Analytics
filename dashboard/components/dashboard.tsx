"use client";
import { useMemo, useState } from "react";
import useSWR from "swr";
import { Activity, ArrowDownRight, ArrowUpDown, Boxes, CircleAlert, Download, Radio, RefreshCw, Search, ShoppingBag, Users, X } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { RevenueChart, ProductChart, type RevenueMode } from "@/components/analytics-charts";

const fetcher = (url: string) => fetch(url).then(async r => { if (!r.ok) throw new Error("Data is unavailable"); return r.json(); });
const money = (value: number) => `R$ ${value.toLocaleString("pt-BR", { maximumFractionDigits: 0 })}`;
const number = (value: number) => value.toLocaleString("en-US");

function Metric({ label, value, foot, icon: Icon }: { label: string; value: string; foot: string; icon: typeof Activity }) {
  return <Card><CardContent className="flex items-start justify-between p-5"><div><p className="text-sm text-slate-400">{label}</p><p className="mt-3 text-2xl font-semibold tracking-tight">{value}</p><p className="mt-2 text-xs text-slate-400">{foot}</p></div><div className="rounded-lg bg-slate-800 p-2.5 text-emerald-300"><Icon size={18} /></div></CardContent></Card>;
}

const RANGES = [{ label: "30D", days: 30 }, { label: "90D", days: 90 }, { label: "6M", days: 180 }, { label: "1Y", days: 365 }, { label: "All", days: 0 }];
const MODES: { key: RevenueMode; label: string }[] = [{ key: "daily", label: "Daily" }, { key: "avg7", label: "7-day avg" }, { key: "cumulative", label: "Cumulative" }];
const chip = (active: boolean) => `rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${active ? "bg-emerald-400 text-slate-950" : "bg-slate-800 text-slate-300 hover:bg-slate-700"}`;
type SortKey = "churn_probability" | "recency_days" | "frequency";

function downloadCsv(rows: any[]) {
  const head = ["customer_id", "cohort", "recency_days", "orders", "spend_180d", "churn_probability"];
  const body = rows.map(r => [r.customer_id, r.cohort, r.recency_days, r.frequency, r.monetary?.toFixed(2), r.churn_probability.toFixed(4)].join(","));
  const url = URL.createObjectURL(new Blob([[head.join(","), ...body].join("\n")], { type: "text/csv" }));
  Object.assign(document.createElement("a"), { href: url, download: "churn-risk.csv" }).click();
  URL.revokeObjectURL(url);
}

export default function Dashboard() {
  const [days, setDays] = useState(90);
  const [category, setCategory] = useState<string | null>(null);
  const [mode, setMode] = useState<RevenueMode>("daily");
  const [auto, setAuto] = useState(true);
  const [live, setLive] = useState(true);
  const [query, setQuery] = useState("");
  const [threshold, setThreshold] = useState(0);
  const [sort, setSort] = useState<{ key: SortKey; dir: 1 | -1 }>({ key: "churn_probability", dir: -1 });
  const [selected, setSelected] = useState<any>(null);

  const url = `/api/analytics?days=${days}${category ? `&category=${encodeURIComponent(category)}` : ""}`;
  const { data, error, isLoading, isValidating, mutate } = useSWR(url, fetcher, { refreshInterval: auto ? 120000 : 0, keepPreviousData: true });
  const { data: feed } = useSWR(live ? "/api/events" : null, fetcher, { refreshInterval: 5000 });
  const metrics = data?.metrics;
  const categoryLabel = data?.categories?.find((c: any) => c.key === category)?.label ?? category;

  const rows = useMemo(() => [...(data?.risk ?? [])]
    .filter((r: any) => r.churn_probability >= threshold / 100 && r.customer_id.toLowerCase().includes(query.trim().toLowerCase()))
    .sort((a: any, b: any) => (a[sort.key] - b[sort.key]) * sort.dir), [data, threshold, query, sort]);
  const toggleSort = (key: SortKey) => setSort(s => s.key === key ? { key, dir: (-s.dir) as 1 | -1 } : { key, dir: -1 });
  const sortHead = (k: SortKey, text: string, right?: boolean) => (
    <th className={`pb-3 font-medium ${right ? "text-right" : ""}`}>
      <button onClick={() => toggleSort(k)} className={`inline-flex items-center gap-1 hover:text-slate-200 ${sort.key === k ? "text-emerald-300" : ""}`}>{text}<ArrowUpDown size={11} /></button>
    </th>
  );

  return <main className="mx-auto min-h-screen max-w-[1440px] px-5 py-8 md:px-10 md:py-10">
    <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
      <div>
        <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-[.2em] text-emerald-300"><span className="h-2 w-2 rounded-full bg-emerald-400" /> Streamline</div>
        <h1 className="text-3xl font-semibold tracking-tight">Commerce overview</h1>
        <p className="mt-2 text-sm text-slate-400">Olist marketplace performance · Brazil</p>
      </div>
      <div className="flex items-center gap-3">
        <label className="flex cursor-pointer items-center gap-2 text-xs text-slate-400"><input type="checkbox" checked={auto} onChange={e => setAuto(e.target.checked)} className="accent-emerald-400" /> Auto-refresh</label>
        <Button variant="outline" onClick={() => mutate()}><RefreshCw size={15} className={isValidating ? "animate-spin" : ""} /> Refresh data</Button>
      </div>
    </header>

    <section className="mb-5 flex flex-wrap items-center gap-3 rounded-xl border bg-slate-900/40 p-3">
      <span className="text-xs uppercase tracking-wider text-slate-500">Period</span>
      <div className="flex gap-1.5">{RANGES.map(r => <button key={r.label} onClick={() => setDays(r.days)} className={chip(days === r.days)}>{r.label}</button>)}</div>
      <span className="ml-2 text-xs uppercase tracking-wider text-slate-500">Category</span>
      <select value={category ?? ""} onChange={e => setCategory(e.target.value || null)} className="rounded-md border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-xs text-slate-200">
        <option value="">All categories</option>
        {(data?.categories ?? []).map((c: any) => <option key={c.key} value={c.key}>{c.label}</option>)}
      </select>
      {category && <button onClick={() => setCategory(null)} className="flex items-center gap-1 rounded-full bg-emerald-950 px-3 py-1 text-xs text-emerald-300">{categoryLabel} <X size={12} /></button>}
      <span className="ml-auto text-xs text-slate-500">Tip: click a bar in Top products to filter everything</span>
    </section>

    {error && <div className="mb-5 flex items-center gap-2 rounded-lg border border-rose-900 bg-rose-950/40 p-3 text-sm text-rose-200"><CircleAlert size={16} /> Could not load analytics. Check DATABASE_URL and run dbt plus dashboard SQL setup.</div>}

    <section className={`grid gap-4 transition-opacity sm:grid-cols-2 xl:grid-cols-4 ${isValidating ? "opacity-70" : ""}`}>
      <Metric label="Gross merchandise value" value={metrics ? money(metrics.revenue) : "—"} foot={category ? categoryLabel : "Delivered order items"} icon={Activity} />
      <Metric label="Orders" value={metrics ? number(metrics.orders) : "—"} foot="Unique order IDs" icon={ShoppingBag} />
      <Metric label="Active customers" value={metrics ? number(metrics.customers) : "—"} foot="Customers with an order" icon={Users} />
      <Metric label="At-risk in sample" value={data?.model_version ? number(metrics.at_risk) : "—"} foot={data?.model_version ? "Elevated risk · up to 40 scored" : "Churn model unavailable"} icon={ArrowDownRight} />
    </section>

    <section className="mt-5 grid gap-5 xl:grid-cols-[1.65fr_1fr]">
      <Card>
        <CardHeader className="flex-row flex-wrap items-start justify-between gap-3">
          <div><CardTitle>Revenue over time</CardTitle><p className="mt-1 text-sm text-slate-400">Delivered revenue · {days ? `last ${days} days of data` : "all time"}{category ? ` · ${categoryLabel}` : ""} · drag the slider to zoom</p></div>
          <div className="flex gap-1.5">{MODES.map(m => <button key={m.key} onClick={() => setMode(m.key)} className={chip(mode === m.key)}>{m.label}</button>)}</div>
        </CardHeader>
        <CardContent><div className="h-[300px]">{data && <RevenueChart data={data.revenue} mode={mode} />}</div></CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>Top products</CardTitle><p className="text-sm text-slate-400">Revenue by category · click to filter</p></CardHeader>
        <CardContent><div className="h-[300px]">{data && <ProductChart data={data.products} selected={category} onSelect={setCategory} />}</div></CardContent>
      </Card>
    </section>

    <section className="mt-5 grid gap-5 xl:grid-cols-[1.4fr_1fr]">
      <Card>
        <CardHeader className="flex-row flex-wrap items-center justify-between gap-3">
          <div><CardTitle>Customer cohorts & churn risk</CardTitle><p className="mt-1 text-sm text-slate-400">90-day churn probability · click a row for detail</p></div>
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative"><Search size={13} className="absolute left-2.5 top-2 text-slate-500" /><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search customer ID" className="w-44 rounded-md border border-slate-700 bg-slate-900 py-1.5 pl-8 pr-2 text-xs text-slate-200 placeholder:text-slate-500" /></div>
            <label className="flex items-center gap-2 text-xs text-slate-400">Min risk <input type="range" min={0} max={100} step={5} value={threshold} onChange={e => setThreshold(Number(e.target.value))} className="w-24 accent-emerald-400" /><span className="w-8 text-slate-200">{threshold}%</span></label>
            <Button variant="outline" onClick={() => downloadCsv(rows)} disabled={!rows.length}><Download size={14} /> CSV</Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto"><table className="w-full text-left text-sm">
            <thead className="text-xs text-slate-500"><tr><th className="pb-3 font-medium">Customer</th><th className="pb-3 font-medium">Cohort</th>{sortHead("recency_days", "Last order")}{sortHead("frequency", "Orders")}{sortHead("churn_probability", "Churn risk", true)}</tr></thead>
            <tbody>
              {rows.map((row: any) => <tr key={row.customer_id} onClick={() => setSelected(row)} className={`cursor-pointer border-t hover:bg-slate-800/50 ${selected?.customer_id === row.customer_id ? "bg-slate-800/60" : ""}`}>
                <td className="py-3 font-mono text-xs text-slate-300">{row.customer_id.slice(0, 8)}…</td><td className="py-3 text-slate-400">{row.cohort}</td><td className="py-3 text-slate-400">{row.recency_days}d ago</td><td className="py-3 text-slate-300">{row.frequency}</td>
                <td className="py-3 text-right"><span className={`rounded-full px-2 py-1 text-xs ${row.churn_probability >= 0.65 ? "bg-amber-950 text-amber-300" : "bg-slate-800 text-slate-300"}`}>{Math.round(row.churn_probability * 100)}%</span></td></tr>)}
              {!rows.length && <tr><td colSpan={5} className="py-9 text-center text-slate-500">{isLoading ? "Loading customer scores…" : data?.risk?.length ? "No customers match the filters" : "No customer predictions available"}</td></tr>}
            </tbody></table></div>
          {selected && <div className="mt-4 rounded-lg border border-slate-700 bg-slate-900/60 p-4">
            <div className="mb-3 flex items-center justify-between"><span className="font-mono text-xs text-slate-300">{selected.customer_id}</span><button onClick={() => setSelected(null)} className="text-slate-500 hover:text-slate-200"><X size={14} /></button></div>
            <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
              {[["Churn risk", `${Math.round(selected.churn_probability * 100)}%`], ["Days since order", selected.recency_days], ["Orders (180d)", selected.frequency], ["Spend (180d)", money(selected.monetary ?? 0)], ["Avg review", selected.review_score != null ? `${selected.review_score.toFixed(1)} / 5` : "—"], ["Cohort", selected.cohort]].map(([k, v]) => <div key={String(k)}><p className="text-xs text-slate-500">{k}</p><p className="mt-1 text-slate-100">{v}</p></div>)}
            </div></div>}
          <p className="mt-3 text-xs text-slate-500">{data?.model_version ? `Churn model ${data.model_version} · showing ${rows.length} of ${data.risk.length}` : "Churn API unavailable · scores omitted"}</p>
        </CardContent>
      </Card>

      <div className="space-y-5">
        <Card>
          <CardHeader><CardTitle>Order funnel</CardTitle><p className="text-sm text-slate-400">Orders by fulfillment milestone</p></CardHeader>
          <CardContent><div className="space-y-5">
            {(data?.funnel ?? []).map((stage: any, i: number) => { const max = Math.max(...data.funnel.map((f: any) => f.orders), 1); return <div key={stage.stage} title={`${number(stage.orders)} orders`}><div className="mb-2 flex justify-between text-sm"><span className="flex items-center gap-2 text-slate-300"><span className="text-xs text-slate-500">0{i + 1}</span>{stage.stage}</span><span className="text-slate-400">{number(stage.orders)} <span className="text-slate-600">· {Math.round(stage.orders / max * 100)}%</span></span></div><div className="h-2 overflow-hidden rounded-full bg-slate-800"><div className="h-full rounded-full bg-emerald-400 transition-all duration-500" style={{ width: `${stage.orders / max * 100}%`, opacity: 1 - i * 0.12 }} /></div></div>; })}
            {!data?.funnel?.length && <div className="py-9 text-center text-sm text-slate-500">{isLoading ? "Loading order funnel…" : "No funnel data"}</div>}
          </div></CardContent>
        </Card>
        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <div><CardTitle className="flex items-center gap-2"><Radio size={15} className={live ? "text-emerald-400" : "text-slate-500"} /> Live order events</CardTitle><p className="mt-1 text-sm text-slate-400">{feed?.stats ? `${number(feed.stats.total)} ingested · ${number(feed.stats.last_hour)} in the last hour` : "Kafka stream"}</p></div>
            <button onClick={() => setLive(v => !v)} className={chip(live)}>{live ? "Live" : "Paused"}</button>
          </CardHeader>
          <CardContent><ul className="space-y-2.5">
            {(feed?.events ?? []).slice(0, 8).map((e: any) => <li key={e.event_id} className="flex items-center justify-between text-xs"><span className="flex items-center gap-2"><span className={`rounded px-1.5 py-0.5 ${e.event_type === "new_order" ? "bg-emerald-950 text-emerald-300" : "bg-slate-800 text-slate-300"}`}>{e.event_type === "new_order" ? "new order" : e.status}</span><span className="font-mono text-slate-400">{e.order_id.slice(0, 8)}</span></span><span className="text-slate-500">{e.order_total ? `${money(e.order_total)} · ` : ""}{new Date(e.event_timestamp).toLocaleTimeString()}</span></li>)}
            {!feed?.events?.length && <li className="py-6 text-center text-xs text-slate-500">{feed?.error ? "Event feed unavailable" : "No events yet — start the generator"}</li>}
          </ul></CardContent>
        </Card>
      </div>
    </section>
    <footer className="mt-8 flex items-center justify-between text-xs text-slate-600"><span className="flex items-center gap-2"><Boxes size={14} /> Data sourced from marts schema</span><span>{data?.updated_at ? `Updated ${new Date(data.updated_at).toLocaleTimeString()}` : ""}</span></footer>
  </main>;
}
