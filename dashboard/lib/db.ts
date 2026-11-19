import postgres from "postgres";

// One shared pool per server process. Creating a client per request leaks
// connections and exhausts Postgres ("too many clients"), especially under dev HMR.
const globalForSql = globalThis as unknown as { __sql?: ReturnType<typeof postgres> };

export function getSql() {
  const url = process.env.DATABASE_URL;
  if (!url) throw new Error("DATABASE_URL is not configured");
  if (!globalForSql.__sql) {
    globalForSql.__sql = postgres(url, { prepare: false, max: 5, idle_timeout: 20, connect_timeout: 10 });
  }
  return globalForSql.__sql;
}
