import { NextResponse } from "next/server";
import { getSql } from "@/lib/db";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  // Simple secret-based protection for Vercel Cron
  const authHeader = request.headers.get("authorization");
  if (!process.env.CRON_SECRET || authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    const sql = getSql();
    // Ensure the views exist (idempotent), then refresh them in place so
    // readers never see a missing view if the refresh fails part-way.
    const { readFileSync } = await import("fs");
    const { join } = await import("path");
    const sqlContent = readFileSync(join(process.cwd(), "sql", "dashboard_views.sql"), "utf-8");
    await sql.unsafe(sqlContent);
    for (const view of ["dashboard_revenue_daily", "dashboard_product_revenue", "dashboard_order_funnel"]) {
      await sql.unsafe(`refresh materialized view marts.${view}`);
    }

    return NextResponse.json({ message: "Dashboard views refreshed successfully", timestamp: new Date().toISOString() });
  } catch (error) {
    console.error("Failed to refresh dashboard materialized views:", error);
    return NextResponse.json(
      { error: "Failed to refresh dashboard materialized views", details: (error as Error).message },
      { status: 500 }
    );
  }
}