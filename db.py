import os
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

# Explicitly load the .env file from the current directory
load_dotenv(override=True)

def get_connection():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set in .env")
    return psycopg.connect(
        database_url,
        row_factory=dict_row
    )

def fetch_all(query, params=None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            return cur.fetchall()

def fetch_one(query, params=None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            return cur.fetchone()

def execute_query(query, params=None, fetch_id=False):
    with get_connection() as conn:
        with conn.cursor() as cur:
            if fetch_id:
                # If the query doesn't already have RETURNING, append it safely
                if "RETURNING" not in query.upper():
                    query = query.rstrip(";") + " RETURNING id"
                cur.execute(query, params or ())
                row = cur.fetchone()
                conn.commit()
                if row:
                    # Return whichever primary key value was returned (first column)
                    return list(row.values())[0]
                return None
            else:
                cur.execute(query, params or ())
                conn.commit()