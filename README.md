Here’s your **complete `README.md` file** in one block of Markdown that you can copy-paste directly into your repo — cleanly formatted and with no missing code blocks.

---

### ✅ Full `README.md` (paste this as is)

````markdown
# Autonomous Hiring Pipeline

An end-to-end automated hiring pipeline built with Python and AI.  
This system crawls portfolio websites, evaluates candidates using rule-based and AI scoring, conducts HR screening via email, and displays live status on a dashboard.

---

## 🚀 What This Project Does

This system performs the full hiring evaluation process:

1. **Scrape portfolios** from URLs  
2. **Rule-based scoring** (backend + AI criteria)  
3. **AI evaluation** using OpenRouter LLMs (OpenAI compatible)  
4. **Shortlist candidates**  
5. **HR screening via email** (questions sent and answers received)  
6. **Evaluate HR responses with AI**  
7. **Display live results using FastAPI dashboard (auto-refresh)**

All steps can be run autonomously or as a pipeline.

---

## 🧠 Tech Stack

| Layer | Technology |
|-------|------------|
| Programming Language | Python |
| Web Framework | FastAPI |
| Web Scraping | Playwright + BeautifulSoup |
| Database | PostgreSQL |
| Asynchronous IO | asyncio, asyncpg |
| AI & LLM Evaluation | OpenRouter API |
| Email Automation | SMTP + IMAP |
| Frontend UI | TailwindCSS + Jinja2 templates |
| Notification / Real-Time | WebSockets |
| Deployment | Uvicorn |

---

## 🛠 Prerequisites

Before running the system, ensure the following are installed:

✔ Python 3.9+  
✔ PostgreSQL database  
✔ Git  
✔ Node + Playwright dependencies (for scraping)

---

## 🧩 Environment Setup

1. **Clone the repo:**

```bash
git clone https://github.com/rohithrajv007/autonomous-hiring-pipeline.git
cd autonomous-hiring-pipeline
````

2. **Create & activate a Python virtual environment:**

```bash
python -m venv venv
source venv/bin/activate    # Mac/Linux
venv\Scripts\activate       # Windows
```

3. **Install dependencies:**

```bash
pip install -r requirements.txt
```

4. **Environment variables:**

Copy the `.env.example` and fill in real credentials:

```bash
cp .env.example .env
```

Edit `.env` with your:

* Database config
* Email SMTP/IMAP credentials
* OpenRouter API key & model
* Any other secrets

> ⚠ DO NOT COMMIT `.env` to GitHub!

---

## 🗄 Database Setup

To reset and initialize the database with sample content:

```bash
python db_setup.py
```

This will:

✔ Drop the existing database
✔ Recreate it
✔ Create required tables
✔ Insert sample candidates
✔ Insert default HR questions

---

## 📌 Running the Full Pipeline

To run all agents sequentially:

```bash
python master_pipeline.py
```

This will execute:

* Scraper
* Rule-based scoring
* AI evaluation
* Shortlisting
* HR screening emails

---

## 🔁 Running Individual Agents

You can also run agents individually:

### Agent 1 — Scrape portfolios

```bash
python agents/agent1_scraper.py
```

### Agent 2 — Rule-based scoring

```bash
python agents/agent2_scoring.py
```

### Agent 3 — AI evaluation

```bash
python agents/agent3_ai_evaluator.py
```

### Agent 5 — Send HR screening

```bash
python agents/agent5_send_only_hr_screening.py
```

### Agent 6 — Receive HR replies (loop)

```bash
python agents/agent6_hr_receive_answers_loop.py
```

### Agent 7 — AI evaluate HR answers

```bash
python agents/agent7_hr_ai_evaluator.py
```

---

## 📊 Dashboard

To start the real-time dashboard:

```bash
uvicorn dashboard:app --reload
```

Open in a browser:

```
http://127.0.0.1:8000
```

The dashboard shows:

✔ Candidate names
✔ Backend scores & recommendations
✔ AI scores & recommendations
✔ Final hybrid scores
✔ HR answered counts
✔ Shortlist status

---

## 🧾 Data Models

### `portfolios`

Stores candidate details, scoring status, email, and URLs.

### `hr_questions`

Stores HR questions & criteria for evaluation.

### `hr_answers`

Stores email responses from candidates and AI evaluations.

---


---

## 💡 Tips & Best Practices

✔ Always fill `.env` before running
✔ Ensure Playwright dependencies are installed
✔ Use PostgreSQL for production (not SQLite)
✔ Monitor email throttling (avoid SMTP limits)

---

## ❓ Troubleshooting

If the dashboard does not update:

* Verify that the database has updated scores
* Make sure WebSockets are connected
* Call `/trigger_update` after agent runs

---

## 🛡 Security

✔ Never commit credentials
✔ Use environment variables for keys
✔ Use HTTPS for production deployment

---


---




```
