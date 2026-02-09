import os
import asyncio
import asyncpg
import httpx
import json
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = os.getenv("MODEL_NAME")

DB_CONFIG = {
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT",5432)),
}

############################################
# BUILD PROMPT FOR HR EVAL
############################################

def build_hr_prompt(question, answer, criteria_json):

    trimmed_answer = answer[:3000]

    return f"""
You are a senior HR evaluator.

Question:
{question}

Candidate Answer:
{trimmed_answer}

Criteria:
{criteria_json}

Evaluate how well the answer matches the criteria.
Return JSON only:

{{
  "score": float,
  "decision": "Pass | Review | Fail"
}}
"""

############################################
# CALL AI
############################################

async def call_ai(prompt):

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": MODEL,
                "messages":[{"role":"user","content":prompt}]
            }
        )
        result = response.json()
        return result["choices"][0]["message"]["content"]


############################################
# SAFE JSON PARSE
############################################

def parse_json(content):
    try:
        start = content.find("{")
        end = content.rfind("}") + 1
        return json.loads(content[start:end])
    except:
        return None


############################################
# MAIN AI EVALUATOR
############################################

async def run_hr_ai_evaluator():

    conn = await asyncpg.connect(**DB_CONFIG)

    rows = await conn.fetch("""
        SELECT h.id,
               h.raw_answer,
               q.question,
               q.criteria
        FROM hr_answers h
        JOIN hr_questions q
          ON h.question_id = q.id
        WHERE h.raw_answer IS NOT NULL
          AND (h.ai_score IS NULL OR h.ai_decision IS NULL);
    """)

    if not rows:
        print("⚠️ No HR answers need AI evaluation.")
        await conn.close()
        return

    print("\n🚀 Evaluating HR Answers with AI...\n")

    for r in rows:

        question = r["question"]
        answer   = r["raw_answer"]
        criteria = r["criteria"]

        prompt = build_hr_prompt(question, answer, json.dumps(criteria))

        content = await call_ai(prompt)

        parsed = parse_json(content)

        if not parsed:
            print("⚠️ JSON parse failed, skipping.")
            continue

        ai_score    = parsed.get("score", 0)
        ai_decision = parsed.get("decision", "Fail")

        await conn.execute("""
            UPDATE hr_answers
            SET processed_answer = $1,
                ai_score = $2,
                ai_decision = $3
            WHERE id = $4;
        """, answer, ai_score, ai_decision, r["id"])

        print(f"🧠 Evaluated answer {r['id']} → {ai_score},{ai_decision}")

    await conn.close()

if __name__ == "__main__":
    asyncio.run(run_hr_ai_evaluator())
