import type { NextConfig } from "next";
const nextConfig: NextConfig = {
  output: "standalone",
  // /api/refresh reads this file at runtime; make sure it ships in the function bundle
  outputFileTracingIncludes: { "/api/refresh": ["./sql/**/*"] },
};
export default nextConfig;
