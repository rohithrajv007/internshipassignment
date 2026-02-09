import os
import asyncio
import asyncpg
import httpx
import json
from dotenv import load_dotenv

load_dotenv()

############################################
# ENV CONFIG
############################################

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = os.getenv("MODEL_NAME")

DB_CONFIG = {
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 5432)),  # type-safe
}

FINAL_RULE_WEIGHT = 0.65
FINAL_AI_WEIGHT = 0.35

DELAY_BETWEEN_CALLS = 4
MAX_RETRIES = 3


############################################
# FETCH TOP UNEVALUATED CANDIDATES
############################################

async def fetch_candidates(conn):

    rows = await conn.fetch("""
        SELECT id,
               candidate_name,
               cleaned_data,
               backend_score,
               ai_score
        FROM portfolios
        WHERE final_backend_score IS NULL
        AND cleaned_data IS NOT NULL
        ORDER BY GREATEST(
            COALESCE(backend_score,0),
            COALESCE(ai_score,0)
        ) DESC
        LIMIT 5;
    """)

    return rows


############################################
# PROMPT
############################################

def build_prompt(text):

    trimmed = text[:6000]

    return f"""
You are a senior engineering hiring manager.

Evaluate this candidate for TWO roles:

1. Backend Engineer
2. AI Engineer

Score each category from 1-10.

Return ONLY valid JSON.

FORMAT:

{{
 "backend_engineer": {{
    "technical_depth": int,
    "production_readiness": int,
    "system_design": int,
    "recommendation": "Strong Hire | Hire | Lean Hire | No Hire"
 }},
 "ai_engineer": {{
    "ml_depth": int,
    "llm_understanding": int,
    "project_complexity": int,
    "recommendation": "Strong Hire | Hire | Lean Hire | No Hire"
 }}
}}

CANDIDATE DATA:
{trimmed}
"""


############################################
# CALL AI (Retry Protected)
############################################

async def call_ai(prompt):

    for attempt in range(MAX_RETRIES):

        try:

            async with httpx.AsyncClient(timeout=60) as client:

                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": MODEL,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ]
                    }
                )

                if response.status_code != 200:
                    print("⚠️ API Error:", response.text)
                    await asyncio.sleep(5)
                    continue

                result = response.json()

                return result["choices"][0]["message"]["content"]

        except Exception as e:

            print("⚠️ Retry due to:", e)
            await asyncio.sleep(5)

    return None


############################################
# SAFE JSON PARSE
############################################

def parse_json(content):

    if not content:
        return None

    try:
        start = content.find("{")
        end = content.rfind("}") + 1

        return json.loads(content[start:end])

    except Exception:
        print("⚠️ JSON parse failed")
        return None


############################################
# COMPUTE SCORES + RECOMMENDATIONS
############################################

def compute_ai_scores(data):

    backend_vals = data["backend_engineer"]
    ai_vals = data["ai_engineer"]

    backend_score = (
        backend_vals["technical_depth"] +
        backend_vals["production_readiness"] +
        backend_vals["system_design"]
    ) / 3 * 10

    ai_score = (
        ai_vals["ml_depth"] +
        ai_vals["llm_understanding"] +
        ai_vals["project_complexity"]
    ) / 3 * 10

    backend_rec = backend_vals["recommendation"]
    ai_rec = ai_vals["recommendation"]

    return (
        round(backend_score, 2),
        round(ai_score, 2),
        backend_rec,
        ai_rec
    )


############################################
# FINAL HYBRID SCORE
############################################

def final_score(rule, ai):

    rule = rule or 0
    ai = ai or 0

    return round(
        (rule * FINAL_RULE_WEIGHT) +
        (ai * FINAL_AI_WEIGHT), 2
    )


############################################
# UPDATE DB
############################################

async def update_scores(
    conn,
    candidate_id,
    ai_backend,
    ai_ai,
    final_backend,
    final_ai,
    backend_rec,
    ai_rec
):

    await conn.execute("""
        UPDATE portfolios
        SET ai_backend_score=$1,
            ai_ai_score=$2,
            final_backend_score=$3,
            final_ai_score=$4,
            backend_recommendation=$5,
            ai_recommendation=$6
        WHERE id=$7;
    """,
        ai_backend,
        ai_ai,
        final_backend,
        final_ai,
        backend_rec,
        ai_rec,
        candidate_id
    )


############################################
# LEADERBOARD
############################################

async def leaderboard(conn):

    print("\n🏆 FINAL BACKEND RANKING\n")

    rows = await conn.fetch("""
        SELECT candidate_name,
               COALESCE(final_backend_score, backend_score) AS score,
               backend_recommendation
        FROM portfolios
        ORDER BY score DESC;
    """)

    for i, r in enumerate(rows, 1):
        print(f"{i}. {r['candidate_name']} → {r['score']} ({r['backend_recommendation']})")


    print("\n🤖 FINAL AI RANKING\n")

    rows = await conn.fetch("""
        SELECT candidate_name,
               COALESCE(final_ai_score, ai_score) AS score,
               ai_recommendation
        FROM portfolios
        ORDER BY score DESC;
    """)

    for i, r in enumerate(rows, 1):
        print(f"{i}. {r['candidate_name']} → {r['score']} ({r['ai_recommendation']})")


############################################
# MAIN AGENT
############################################

async def ai_agent():

    conn = await asyncpg.connect(**DB_CONFIG)

    candidates = await fetch_candidates(conn)

    if not candidates:
        print("\n✅ No candidates require AI evaluation.\n")
        await conn.close()
        return

    print("\n🚀 Starting AI Evaluation...\n")

    for c in candidates:

        print(f"Evaluating → {c['candidate_name']}")

        prompt = build_prompt(c["cleaned_data"])

        content = await call_ai(prompt)

        parsed = parse_json(content)

        if not parsed:
            print("⚠️ Skipping candidate\n")
            continue

        ai_backend, ai_ai, backend_rec, ai_rec = compute_ai_scores(parsed)

        final_backend = final_score(c["backend_score"], ai_backend)
        final_ai = final_score(c["ai_score"], ai_ai)

        await update_scores(
            conn,
            c["id"],
            ai_backend,
            ai_ai,
            final_backend,
            final_ai,
            backend_rec,
            ai_rec
        )

        print("✅ Done\n")

        await asyncio.sleep(DELAY_BETWEEN_CALLS)

    await leaderboard(conn)

    await conn.close()


############################################

if __name__ == "__main__":
    asyncio.run(ai_agent())
