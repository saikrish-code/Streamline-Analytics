import { NextResponse } from "next/server";
import { getSql } from "@/lib/db";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Latest streamed order events (Kafka -> raw.streaming_events) for the live feed.
export async function GET() {
  try {
    const sql = getSql();
    const [events, stats] = await Promise.all([
      sql`select event_id, event_type, order_id, event_timestamp,
            payload->'data'->>'status' as status,
            (payload->'data'->>'order_total')::float8 as order_total
          from raw.streaming_events order by event_timestamp desc limit 12`,
      sql`select count(*)::int as total,
            count(*) filter (where event_timestamp > now() - interval '1 hour')::int as last_hour,
            max(event_timestamp) as latest from raw.streaming_events`,
    ]);
    return NextResponse.json({ events, stats: stats[0] }, { headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    console.error("Live events query failed", error);
    return NextResponse.json({ error: "Live events unavailable" }, { status: 503 });
  }
}
