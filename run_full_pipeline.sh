#!/bin/bash
# Full pipeline setup script

# Step 1: Ensure docker is running
if ! docker ps | grep -q "streamline-postgres"; then
    echo "Starting Docker services..."
    docker compose up -d
    sleep 10
fi

# Step 2: Set environment variables
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_USER=streamline
export POSTGRES_PASSWORD=streamline_local
export POSTGRES_DB=streamline
export DATABASE_URL="postgresql://streamline:streamline_local@localhost:5432/streamline"

# Step 3: Download Olist dataset (manual step required)
echo "
=== STEP 3: Download Olist Dataset ===
Download from: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce/download/brazilian-ecommerce-csv.zip
Extract the 6 CSV files (customers, orders, order_items, payments, reviews, products) into data/raw/
Press Enter when ready..."
read -p ""

# Step 4: Run ingestion with fallback loader
echo "
=== STEP 4: Running Ingestion ==="
python -m ingestion.load_olist

# Step 5: Run dbt build
echo "
=== STEP 5: Running dbt Build ==="
cd dbt_project
dbt build --profiles-dir . --vars "postgres_host=localhost"
cd ..

# Step 6: Apply dashboard materialized views
echo "
=== STEP 6: Applying Dashboard Views ==="
psql "$DATABASE_URL" -f dashboard/sql/dashboard_views.sql

# Step 7: Verify everything
echo "
=== VERIFICATION ==="

# Test DB connection
python -c "import psycopg2; conn = psycopg2.connect('$DATABASE_URL'); print('DB OK')"

# Test API endpoint
curl -s http://localhost:3000/api/analytics | python -m json.tool

# Open dashboard
echo "Dashboard available at: http://localhost:3000"
