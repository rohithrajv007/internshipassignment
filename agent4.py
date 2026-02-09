import os
import asyncio
import asyncpg
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 5432)),
}


def decide_shortlist(backend_final, ai_final, backend_rec, ai_rec):

    # Normalize to uppercase for safety
    br = (backend_rec or "").lower()
    ar = (ai_rec or "").lower()

    # If either role says strong hire → SELECTED
    if "strong hire" in br or "strong hire" in ar:
        return "SELECTED"

    # If backend says hire AND backend score is good
    if "hire" in br and backend_final >= 55:
        return "SELECTED"

    # If AI says hire AND ai score is good
    if "hire" in ar and ai_final >= 55:
        return "SELECTED"

    # HOLD conditions
    if "lean hire" in br and backend_final >= 60:
        return "HOLD"
    if "lean hire" in ar and ai_final >= 60:
        return "HOLD"

    # Otherwise reject
    return "REJECT"


async def fetch_candidates(conn):
    return await conn.fetch("""
        SELECT id,
               candidate_name,
               COALESCE(final_backend_score, backend_score) as bf,
               COALESCE(final_ai_score, ai_score) as af,
               backend_recommendation,
               ai_recommendation
        FROM portfolios;
    """)


async def update_shortlist(conn, shortlist, candidate_id):
    await conn.execute("""
        UPDATE portfolios
        SET shortlist_status = $1
        WHERE id = $2
    """, shortlist, candidate_id)


async def main():
    conn = await asyncpg.connect(**DB_CONFIG)

    candidates = await fetch_candidates(conn)

    print("\n🚀 Running Auto Shortlist Agent...\n")

    for c in candidates:

        backend_final = c["bf"] or 0
        ai_final = c["af"] or 0

        backend_rec = c["backend_recommendation"] or ""
        ai_rec = c["ai_recommendation"] or ""

        shortlist = decide_shortlist(
            backend_final,
            ai_final,
            backend_rec,
            ai_rec
        )

        await update_shortlist(conn, shortlist, c["id"])

        print(f"{c['candidate_name']}: {shortlist}")

    await conn.close()

    print("\n🎉 Shortlisting Complete!\n")


if __name__ == "__main__":
    asyncio.run(main())
