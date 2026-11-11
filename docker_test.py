import psycopg2
conn = psycopg2.connect(
    host='streamline-postgres',
    port=5432,
    user='streamline',
    password='streamline_local',
    dbname='streamline'
)
print('PostgreSQL connected!')
conn.close()