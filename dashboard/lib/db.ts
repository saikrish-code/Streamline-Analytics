import postgres from "postgres";

export function getSql() {
  const url = process.env.DATABASE_URL;
  if (!url) throw new Error("DATABASE_URL is not configured");
  // Use postgres (legacy) - no C-extension dependency
  return postgres(url, { prepare: false });
}
