from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
import psycopg2.extras
import os
from urllib.parse import urlparse

app = FastAPI(title="Biasa Born API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:biasa2026@localhost:5432/biasa_born")

def get_conn():
    url = urlparse(DATABASE_URL)
    return psycopg2.connect(
        host=url.hostname,
        port=url.port or 5432,
        dbname=url.path[1:],
        user=url.username,
        password=url.password,
        cursor_factory=psycopg2.extras.RealDictCursor
    )

@app.on_event("startup")
def create_tables():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS biasa_born (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            first_name VARCHAR(100),
            last_name VARCHAR(100),
            phone_number VARCHAR(30) UNIQUE,
            email VARCHAR(150),
            birth_year INTEGER,
            gender VARCHAR(20),
            source VARCHAR(20) DEFAULT 'phone',
            notes TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

@app.get("/")
def root():
    return {"message": "Biasa Born API OK"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/biasa-born/batch")
def batch_create(payload: dict):
    conn = get_conn()
    cur = conn.cursor()
    created = 0
    skipped = 0
    for c in payload.get("contacts", []):
        try:
            cur.execute("""
                INSERT INTO biasa_born (name, first_name, last_name, phone_number, email, birth_year, gender, source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (c.get("name"), c.get("firstName"), c.get("lastName"),
                  c.get("phoneNumber"), c.get("email"), c.get("birthYear"),
                  c.get("gender"), c.get("source", "phone")))
            created += 1
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            skipped += 1
            continue
    conn.commit()
    cur.close()
    conn.close()
    return {"created": created, "skipped": skipped}

@app.post("/biasa-born")
def create_one(payload: dict):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO biasa_born (name, first_name, last_name, phone_number, email, birth_year, gender, source)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING *
    """, (payload.get("name"), payload.get("firstName"), payload.get("lastName"),
          payload.get("phoneNumber"), payload.get("email"), payload.get("birthYear"),
          payload.get("gender"), payload.get("source", "manual")))
    conn.commit()
    result = cur.fetchone()
    cur.close()
    conn.close()
    return dict(result)

@app.get("/biasa-born")
def list_all(skip: int = 0, limit: int = 50):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM biasa_born ORDER BY created_at DESC LIMIT %s OFFSET %s", (limit, skip))
    results = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in results]

@app.get("/biasa-born/stats")
def stats():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as total FROM biasa_born")
    total = cur.fetchone()["total"]
    cur.execute("SELECT COUNT(*) as week FROM biasa_born WHERE created_at >= NOW() - INTERVAL '7 days'")
    this_week = cur.fetchone()["week"]
    cur.execute("SELECT COUNT(*) as n FROM biasa_born WHERE source = 'phone'")
    from_phone = cur.fetchone()["n"]
    cur.execute("SELECT COUNT(*) as n FROM biasa_born WHERE source = 'manual'")
    manual = cur.fetchone()["n"]
    cur.execute("SELECT * FROM biasa_born ORDER BY created_at DESC LIMIT 5")
    recent = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return {"total": total, "this_week": this_week, "from_phone": from_phone, "manual": manual, "recent": recent}