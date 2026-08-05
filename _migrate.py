import psycopg2

dsn = 'postgresql://neondb_owner:npg_C5LbMZvuyRh4@ep-ancient-voice-azieelp5-pooler.c-3.ap-southeast-1.aws.neon.tech/neondb?sslmode=require'
conn = psycopg2.connect(dsn)

sql = open(r'D:\marketgate\db\migrations\0004_auth_users.sql', 'r', encoding='utf-8').read()
with conn.cursor() as cur:
    cur.execute(sql)
conn.commit()

with conn.cursor() as cur:
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name LIKE 'auth%'")
    for row in cur.fetchall():
        print(f'Table: {row[0]}')
conn.close()
print('Migration OK')
