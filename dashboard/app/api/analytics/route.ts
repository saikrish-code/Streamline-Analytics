import { NextResponse } from "next/server";
import { getSql } from "@/lib/db";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const sql = getSql();
    const params = new URL(request.url).searchParams;
    const daysParam = Number(params.get("days"));
    const days = [30, 90, 180, 365].includes(daysParam) ? daysParam : 0; // 0 = all time
    const category = params.get("category")?.slice(0, 80) || null;
    // Windows are anchored to the latest order in the data (Olist is a historical snapshot).
    const inWindow = sql`(${days} = 0 or f.purchased_at::date > (select max(purchased_at)::date from marts.fact_orders) - ${days}::int)`;
    const inCategory = sql`(${category}::text is null or coalesce(nullif(p.category_name, ''), 'uncategorized') = ${category})`;
    const [revenue, products, funnel, metrics, categories, candidates] = await Promise.all([
      sql`select to_char(f.purchased_at::date, 'YYYY-MM-DD') as iso, to_char(f.purchased_at::date, 'Mon DD') as day,
            sum(f.item_total)::float8 as revenue, count(distinct f.order_id)::int as orders
          from marts.fact_orders f left join marts.dim_products p using (product_id)
          where f.order_status = 'delivered' and ${inWindow} and ${inCategory}
          group by f.purchased_at::date order by f.purchased_at::date`,
      sql`select initcap(replace(coalesce(nullif(p.category_name, ''), 'uncategorized'), '_', ' ')) as product,
            coalesce(nullif(p.category_name, ''), 'uncategorized') as category_key,
            sum(f.item_total)::float8 as revenue, count(distinct f.order_id)::int as orders
          from marts.fact_orders f left join marts.dim_products p using (product_id)
          where f.order_status = 'delivered' and ${inWindow}
          group by 2, 1 order by revenue desc limit 8`,
      sql`select stage, orders::int as orders from marts.dashboard_order_funnel order by case stage when 'Placed' then 1 when 'Approved' then 2 when 'Shipped' then 3 else 4 end`,
      sql`select coalesce(sum(f.item_total),0)::float8 as revenue, count(distinct f.order_id)::int as orders, count(distinct f.customer_unique_id)::int as customers
          from marts.fact_orders f left join marts.dim_products p using (product_id)
          where f.order_status = 'delivered' and ${inWindow} and ${inCategory}`,
      sql`select coalesce(nullif(category_name, ''), 'uncategorized') as key,
            initcap(replace(coalesce(nullif(category_name, ''), 'uncategorized'), '_', ' ')) as label
          from marts.dashboard_product_revenue order by revenue desc limit 40`,
      sql`with customer_orders as (
        select customer_unique_id, order_id, min(purchased_at) as purchased_at,
          sum(item_total)::float8 as order_total
        from marts.fact_orders where customer_unique_id is not null and order_status not in ('canceled','unavailable')
        group by customer_unique_id, order_id
      ), anchor as (select max(purchased_at)::date as as_of from customer_orders), rfm as (
        select c.customer_unique_id, min(c.purchased_at)::date as first_order,
          max(c.purchased_at)::date as last_order, count(*) filter (where c.purchased_at >= a.as_of - interval '180 days')::int as frequency,
          coalesce(sum(c.order_total) filter (where c.purchased_at >= a.as_of - interval '180 days'),0)::float8 as monetary,
          (a.as_of - max(c.purchased_at)::date)::int as recency_days
        from customer_orders c cross join anchor a group by c.customer_unique_id,a.as_of
      ), reviews as (
        select customer_unique_id, avg((review_score::float8 - 3) / 2) as mean_review_sentiment_180d,
          avg(review_score::float8) as mean_review_score_180d,
          avg(case when review_score <= 2 then 1.0 else 0.0 end) as negative_review_share_180d,
          count(*)::int as review_count_180d
        from marts.fact_reviews, anchor where review_created_at::date >= anchor.as_of - interval '180 days'
        group by customer_unique_id
      ) select r.customer_unique_id, to_char(r.first_order, 'Mon YYYY') as cohort, r.recency_days,
        r.frequency, r.monetary, v.mean_review_sentiment_180d::float8 as mean_review_sentiment_180d,
        v.mean_review_score_180d::float8 as mean_review_score_180d,
        v.negative_review_share_180d::float8 as negative_review_share_180d,
        coalesce(v.review_count_180d,0)::int as review_count_180d
        from rfm r left join reviews v using(customer_unique_id)
        where r.frequency > 0 order by r.recency_days desc limit 40`,
    ]);

    const endpoint = process.env.CHURN_API_URL?.replace(/\/$/, "");
    let modelVersion: string | null = null;
    let risk: Record<string, unknown>[] = [];
    let atRiskCount = 0;
    if (endpoint) {
      const scored = await Promise.allSettled(candidates.map(async (c: any) => {
        const response = await fetch(`${endpoint}/predict`, {
          method: "POST", headers: { "content-type": "application/json" },
          body: JSON.stringify({
            recency_days: c.recency_days, frequency_180d: c.frequency, monetary_180d: c.monetary,
            average_order_value_180d: c.monetary / c.frequency,
            mean_review_sentiment_180d: c.mean_review_sentiment_180d,
            negative_review_share_180d: c.negative_review_share_180d,
            mean_review_score_180d: c.mean_review_score_180d,
            review_count_180d: c.review_count_180d,
          }),
          signal: AbortSignal.timeout(5000), cache: "no-store",
        });
        if (!response.ok) throw new Error("Churn prediction failed");
        const prediction = await response.json();
        modelVersion = prediction.model_version;
        return { customer_id: c.customer_unique_id, cohort: c.cohort, recency_days: c.recency_days, frequency: c.frequency, monetary: c.monetary, review_score: c.mean_review_score_180d, churn_probability: prediction.churn_probability };
      }));
      const predictions = scored.filter((s): s is PromiseFulfilledResult<any> => s.status === "fulfilled").map(s => s.value).sort((a,b) => b.churn_probability - a.churn_probability);
      atRiskCount = predictions.filter(r => r.churn_probability >= 0.65).length;
      risk = predictions.slice(0,25);
    }

    return NextResponse.json({
      revenue, products, funnel, categories, filters: { days, category }, metrics: { ...metrics[0], at_risk: atRiskCount },
      risk, model_version: modelVersion, updated_at: new Date().toISOString(),
    }, { headers: { "Cache-Control": "private, max-age=60, stale-while-revalidate=120" } });
  } catch (error) {
    console.error("Dashboard analytics query failed", error);
    return NextResponse.json({ error: "Analytics data is unavailable" }, { status: 503 });
  }
}
