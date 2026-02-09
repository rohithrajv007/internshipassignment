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
    "port": os.getenv("DB_PORT"),
}


############################################
# ROLE → SKILL MAP
############################################

ROLE_SKILLS = {

    "backend": {

        "must_have": [
            "python",
            "fastapi",
            "django",
            "node",
            "sql",
            "mongodb",
            "api",
            "backend"
        ],

        "good_to_have": [
            "docker",
            "kubernetes",
            "aws",
            "redis",
            "postgres",
            "microservices"
        ]
    },

    "ai": {

        "must_have": [
            "python",
            "machine learning",
            "deep learning",
            "llm",
            "tensorflow",
            "pytorch",
            "ai",
        ],

        "good_to_have": [
            "rag",
            "vector database",
            "transformers",
            "nlp",
            "computer vision",
            "genai"
        ]
    }
}


############################################
# SCORING FUNCTION
############################################

def score_candidate(cleaned_text, role):

    if not cleaned_text:
        return 0

    role_data = ROLE_SKILLS[role]

    text = cleaned_text.lower()

    score = 0

    MUST_WEIGHT = 12
    GOOD_WEIGHT = 5

    must_hits = 0
    good_hits = 0

    # MUST SKILLS
    for skill in role_data["must_have"]:
        if skill in text:
            score += MUST_WEIGHT
            must_hits += 1

    # GOOD SKILLS
    for skill in role_data["good_to_have"]:
        if skill in text:
            score += GOOD_WEIGHT
            good_hits += 1


    ########################################
    # BONUS SIGNALS (VERY IMPORTANT)
    ########################################

    if "project" in text:
        score += 8

    if "experience" in text:
        score += 6

    if "github" in text:
        score += 4

    if "deployed" in text or "production" in text:
        score += 6


    ########################################
    # NORMALIZATION
    ########################################

    max_score = (
        len(role_data["must_have"]) * MUST_WEIGHT +
        len(role_data["good_to_have"]) * GOOD_WEIGHT +
        24
    )

    normalized = round((score / max_score) * 100, 2)

    return normalized


############################################
# FETCH CANDIDATES
############################################

async def fetch_candidates(conn):

    rows = await conn.fetch("""
        SELECT id, candidate_name, cleaned_data
        FROM portfolios
        WHERE status='completed';
    """)

    return rows


############################################
# UPDATE SCORES
############################################

async def update_scores(conn, candidate_id, backend_score, ai_score):

    await conn.execute("""
        UPDATE portfolios
        SET backend_score=$1,
            ai_score=$2
        WHERE id=$3;
    """, backend_score, ai_score, candidate_id)


############################################
# LEADERBOARD
############################################

async def print_leaderboard(conn):

    print("\n==============================")
    print("🏆 BACKEND ENGINEER RANKING")
    print("==============================\n")

    rows = await conn.fetch("""
        SELECT candidate_name, backend_score
        FROM portfolios
        WHERE backend_score > 0
        ORDER BY backend_score DESC;
    """)

    for i, r in enumerate(rows, start=1):
        print(f"{i}. {r['candidate_name']} → {r['backend_score']}")



    print("\n==============================")
    print("🤖 AI ENGINEER RANKING")
    print("==============================\n")

    rows = await conn.fetch("""
        SELECT candidate_name, ai_score
        FROM portfolios
        WHERE ai_score > 0
        ORDER BY ai_score DESC;
    """)

    for i, r in enumerate(rows, start=1):
        print(f"{i}. {r['candidate_name']} → {r['ai_score']}")


############################################
# MAIN AGENT
############################################

async def scoring_agent():

    conn = await asyncpg.connect(**DB_CONFIG)

    candidates = await fetch_candidates(conn)

    print("\n🚀 Starting Role-Based Scoring...\n")

    for c in candidates:

        backend_score = score_candidate(
            c["cleaned_data"],
            "backend"
        )

        ai_score = score_candidate(
            c["cleaned_data"],
            "ai"
        )

        await update_scores(
            conn,
            c["id"],
            backend_score,
            ai_score
        )

        print(
            f"✅ {c['candidate_name']} | "
            f"Backend={backend_score} | AI={ai_score}"
        )

    await print_leaderboard(conn)

    await conn.close()


############################################

if __name__ == "__main__":
    asyncio.run(scoring_agent())
