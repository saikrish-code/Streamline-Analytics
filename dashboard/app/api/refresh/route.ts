import { NextRequest, NextResponse } from "next/server";
import { getSql } from "@/lib/db";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const secret = process.env.CRON_SECRET;
  if (secret && request.headers.get("authorization") !== `Bearer ${secret}`) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  try {
    const sql = getSql();
    await sql`refresh materialized view concurrently marts.dashboard_revenue_daily`;
    await sql`refresh materialized view concurrently marts.dashboard_product_revenue`;
    await sql`refresh materialized view concurrently marts.dashboard_order_funnel`;
    return NextResponse.json({ refreshed: ["dashboard_revenue_daily", "dashboard_product_revenue", "dashboard_order_funnel"], refreshed_at: new Date().toISOString() });
  } catch (error) {
    console.error("Dashboard materialized view refresh failed", error);
    return NextResponse.json({ error: "Refresh failed; apply dashboard/sql/dashboard_views.sql after dbt run" }, { status: 503 });
  }
}
