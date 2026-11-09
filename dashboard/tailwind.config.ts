import type { Config } from "tailwindcss";
const config: Config = { content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"], theme: { extend: { colors: { background: "hsl(var(--background))", foreground: "hsl(var(--foreground))", card: "hsl(var(--card))", primary: "hsl(var(--primary))", muted: "hsl(var(--muted))", border: "hsl(var(--border))" }, borderRadius: { xl: "calc(var(--radius) + 2px)", lg: "var(--radius)" } } }, plugins: [] };
export default config;
