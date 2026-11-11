import { NextResponse } from "next/server";
import { getSql } from "@/lib/db";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  // Simple secret-based protection for Vercel Cron
  const authHeader = request.headers.get("authorization");
  if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    const sql = getSql();
    // Drop and recreate materialized views
    await sql`DROP MATERIALIZED VIEW IF EXISTS marts.dashboard_revenue_daily`;
    await sql`DROP MATERIALIZED VIEW IF EXISTS marts.dashboard_product_revenue`;
    await sql`DROP MATERIALIZED VIEW IF EXISTS marts.dashboard_order_funnel`;
    // Apply fresh views from SQL file
    const { readFileSync } = await import('fs');
    const { resolve } = await import('path');
    const sqlContent = readFileSync(resolve(__dirname, '..', '..', 'sql', 'dashboard_views.sql'), 'utf-8');
    // Execute SQL in chunks (simplified for readability)
    await sql`SET statement_timeout = '5min'`;
    await sql`${sqlContent}`;

    return NextResponse.json({ message: "Dashboard views refreshed successfully", timestamp: new Date().toISOString() });
  } catch (error) {
    console.error("Failed to refresh dashboard materialized views:", error);
    return NextResponse.json(
      { error: "Failed to refresh dashboard materialized views", details: (error as Error).message },
      { status: 500 }
    );
  }
}