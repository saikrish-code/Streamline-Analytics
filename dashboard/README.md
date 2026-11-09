# Streamline Analytics dashboard

Next.js App Router dashboard using Tailwind, shadcn-style UI primitives, Recharts, and Neon’s serverless Postgres client. Queries run in server-only route handlers and read the `marts` schema. Do not expose `DATABASE_URL` to client code.

## Local setup

```sh
cd dashboard
npm install
copy .env.example .env.local  # PowerShell; edit the values
npm run dev
```

Set `DATABASE_URL` to a Postgres connection URL reachable from the dashboard. Neon pooled URLs are recommended for serverless deployments. Set `CHURN_API_URL` to the public base URL of the FastAPI service. Until the churn model/API is available, the KPI and cohort table indicate scores are unavailable.

After the raw tables have been loaded and `dbt run` has built the marts, apply the dashboard read-model SQL once:

```sh
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f sql/dashboard_views.sql
```

This creates indexed materialized views for revenue by day, product category revenue, and order funnel counts. `/api/analytics` reads those views and calculates RFM/review features from `marts.fact_orders` and `marts.fact_reviews`, then calls FastAPI `/predict` for up to 40 recently active customers in parallel and displays the ten highest scores. The at-risk KPI is for that scored sample.

## Routes and deployment

- `/api/analytics` serves dashboard metrics and chart data from Postgres.
- `/api/refresh` refreshes the three dashboard materialized views concurrently. Configure `CRON_SECRET` in Vercel; the handler checks `Authorization: Bearer <CRON_SECRET>`.
- `vercel.json` schedules the refresh every six hours. Vercel Hobby may restrict cron schedules to daily execution, so use a plan that supports a six-hour cadence or change the cron expression to a daily schedule.

For Vercel, import the repository and set the project root to `dashboard`. Add `DATABASE_URL`, `CHURN_API_URL`, and a long random `CRON_SECRET` to the deployment environment. Run `dbt run` and apply `sql/dashboard_views.sql` against the same database before exposing the dashboard. For local preview, use `npm run build` and `npm start`.

The chart/page components use a compact shadcn/ui-compatible card primitive. To expand with additional shadcn components, initialize the shadcn CLI from this directory and retain the existing Tailwind CSS variables.
