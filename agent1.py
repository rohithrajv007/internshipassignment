import os
import asyncio
from urllib.parse import urljoin, urlparse
from dotenv import load_dotenv
import asyncpg
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from datetime import datetime

load_dotenv()

DB_CONFIG = {
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
}

BATCH_SIZE = 3
TEXT_LIMIT = 30000
MAX_PAGES = 8


# -----------------------------
# CLEAN HTML (SAFE VERSION)
# -----------------------------
def clean_html(html):
    soup = BeautifulSoup(html, "html.parser")

    # REMOVE ONLY TRUE JUNK
    for tag in soup(["script", "style", "noscript"]):
        tag.extract()

    text = soup.get_text(separator=" ", strip=True)

    return text


# -----------------------------
# STRONG AUTO SCROLL
# (handles lazy + animated sites)
# -----------------------------
async def auto_scroll(page):
    previous_height = 0

    while True:
        current_height = await page.evaluate(
            "document.body.scrollHeight"
        )

        if current_height == previous_height:
            break

        previous_height = current_height

        await page.evaluate(
            "window.scrollTo(0, document.body.scrollHeight)"
        )

        await page.wait_for_timeout(2000)


# -----------------------------
# EXTRACT INTERNAL LINKS
# -----------------------------
def get_internal_links(base_url, html):
    soup = BeautifulSoup(html, "html.parser")

    base_domain = urlparse(base_url).netloc
    links = set()

    for a in soup.find_all("a", href=True):

        href = a["href"]
        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)

        # stay inside domain
        if parsed.netloc == base_domain:

            # remove fragments
            cleaned = full_url.split("#")[0]

            # skip files/images
            if not any(cleaned.endswith(ext) for ext in [
                ".pdf", ".jpg", ".png", ".zip"
            ]):
                links.add(cleaned)

    return list(links)[:MAX_PAGES]


# -----------------------------
# CHECK IF CONTENT IS MEANINGFUL
# (better than dumb length check)
# -----------------------------
def has_signal(text):

    signals = [
        "project",
        "developer",
        "experience",
        "skills",
        "engineer",
        "portfolio",
        "work",
        "react",
        "python"
    ]

    text_lower = text.lower()

    return any(word in text_lower for word in signals)


# -----------------------------
# SCRAPE SINGLE PAGE
# -----------------------------
async def scrape_page(context, url):
    page = await context.new_page()

    try:
        await page.goto(
            url,
            wait_until="networkidle",
            timeout=60000
        )

        # WAIT for hydration / animations
        await page.wait_for_timeout(5000)

        # scroll fully
        await auto_scroll(page)

        # extra wait after scroll
        await page.wait_for_timeout(3000)

        html = await page.content()

        text = clean_html(html)

        print(f"   ✅ scraped: {url} | chars={len(text)}")

        return text

    except Exception as e:
        print(f"   ❌ failed page: {url} -> {e}")
        return ""

    finally:
        await page.close()


# -----------------------------
# MULTI PAGE PORTFOLIO
# -----------------------------
async def scrape_portfolio(context, record):

    id_, base_url = record["id"], record["portfolio_url"]

    try:
        print(f"\n🔎 Crawling portfolio: {base_url}")

        page = await context.new_page()

        await page.goto(
            base_url,
            wait_until="networkidle",
            timeout=60000
        )

        await page.wait_for_timeout(5000)
        await auto_scroll(page)
        await page.wait_for_timeout(3000)

        homepage_html = await page.content()

        internal_links = get_internal_links(base_url, homepage_html)

        await page.close()

        # Avoid duplicates
        pages_to_scrape = list(set([base_url] + internal_links))

        print(f"   👉 Found {len(pages_to_scrape)} pages")

        tasks = [
            scrape_page(context, url)
            for url in pages_to_scrape
        ]

        results = await asyncio.gather(*tasks)

        combined_text = "\n\n".join(results)[:TEXT_LIMIT]

        print("   📊 TOTAL TEXT:", len(combined_text))

        # SMART VALIDATION (not dumb length)
        if not has_signal(combined_text):
            print("   ⚠️ Low signal portfolio")

        return id_, combined_text, "completed"

    except Exception as e:

        print(f"❌ Portfolio failed: {base_url} -> {e}")

        return id_, None, "failed"


# -----------------------------
# FETCH
# -----------------------------
async def fetch_pending(conn):

    rows = await conn.fetch(f"""
        SELECT id, portfolio_url
        FROM portfolios
        WHERE status='pending'
        LIMIT {BATCH_SIZE}
        FOR UPDATE SKIP LOCKED;
    """)

    if rows:
        ids = [r["id"] for r in rows]

        await conn.execute("""
            UPDATE portfolios
            SET status='processing'
            WHERE id = ANY($1)
        """, ids)

    return rows


# -----------------------------
# UPDATE
# -----------------------------
async def update_results(conn, results):

    for id_, text, status in results:

        await conn.execute("""
            UPDATE portfolios
            SET cleaned_data=$1,
                status=$2,
                last_scraped=$3
            WHERE id=$4
        """, text, status, datetime.utcnow(), id_)


# -----------------------------
# WORKER
# -----------------------------
async def worker():

    conn = await asyncpg.connect(**DB_CONFIG)

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )

        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1400, "height": 900}
        )

        while True:

            records = await fetch_pending(conn)

            if not records:
                print("\n✅ No pending portfolios.")
                break

            tasks = [
                scrape_portfolio(context, dict(r))
                for r in records
            ]

            results = await asyncio.gather(*tasks)

            await update_results(conn, results)

        await browser.close()
        await conn.close()


if __name__ == "__main__":
    print("\n🚀 Starting PRO Multi-Page Portfolio Crawler...\n")
    asyncio.run(worker())
    print("\n🎉 Crawling Complete.\n")
