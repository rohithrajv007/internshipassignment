from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Autonomous Hiring Dashboard")

# Templates + static for JS auto refresh
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

############################################
# DB CONFIG
############################################

DB_CONFIG = {
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 5432)),
}

############################################
# WEBSOCKET MANAGER
############################################

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for conn in self.active_connections:
            await conn.send_text(message)

manager = ConnectionManager()

############################################
# STARTUP/SHUTDOWN FOR DB POOL
############################################

@app.on_event("startup")
async def startup():
    app.state.pool = await asyncpg.create_pool(**DB_CONFIG)

@app.on_event("shutdown")
async def shutdown():
    await app.state.pool.close()

############################################
# DASHBOARD ROUTE
############################################

@app.get("/")
async def dashboard(request: Request):
    query = """
        SELECT
            p.id,
            p.candidate_name,

            -- Rule & AI scores
            p.backend_score,
            p.ai_score,
            p.ai_backend_score,
            p.final_backend_score,
            p.backend_recommendation,

            p.ai_ai_score,
            p.final_ai_score,
            p.ai_recommendation,
            p.shortlist_status,

            -- HR answered counts only
            COUNT(ha.id) FILTER (WHERE ha.responded = TRUE) AS answered_count,
            COUNT(ha.id) AS total_questions

        FROM portfolios p
        LEFT JOIN hr_answers ha ON ha.portfolio_id = p.id
        GROUP BY p.id
        ORDER BY COALESCE(p.final_backend_score, p.backend_score) DESC;
    """

    async with app.state.pool.acquire() as conn:
        rows = await conn.fetch(query)

    candidates = [dict(r) for r in rows]

    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "candidates": candidates}
    )

############################################
# WEBSOCKET ENDPOINT
############################################

@app.websocket("/ws/dashboard")
async def dashboard_ws(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

############################################
# TRIGGER UPDATE API
############################################

@app.post("/trigger_update")
async def trigger_update():
    """
    Call this endpoint after agents finish
    (scraping/scoring/AI/HR) to notify dashboard clients.
    """
    await manager.broadcast("update")
    return {"status": "notified"}
