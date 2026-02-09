import os
import asyncpg
import asyncio
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
}


# --------------------------------
# LIST ALL COMPLETED
# --------------------------------
async def list_completed(conn):
    rows = await conn.fetch("""
        SELECT id, candidate_name, portfolio_url,
               LENGTH(cleaned_data) as text_size
        FROM portfolios
        WHERE status='completed'
        ORDER BY id;
    """)

    if not rows:
        print("\n⚠️ No completed portfolios.\n")
        return

    print("\n✅ Completed Scrapes:\n")

    for r in rows:
        print(
            f"ID: {r['id']} | "
            f"Name: {r['candidate_name']} | "
            f"Text Size: {r['text_size']} chars"
        )


# --------------------------------
# VIEW FULL TEXT
# --------------------------------
async def view_full_text(conn, portfolio_id):
    row = await conn.fetchrow("""
        SELECT candidate_name, cleaned_data
        FROM portfolios
        WHERE id=$1;
    """, portfolio_id)

    if not row:
        print("❌ Portfolio not found.")
        return

    text = row["cleaned_data"]

    if not text:
        print("⚠️ No cleaned data available.")
        return

    print("\n" + "="*100)
    print(f"FULL TEXT FOR: {row['candidate_name']}")
    print("="*100 + "\n")

    print(text)


# --------------------------------
# EXPORT TO FILE (BEST FOR DEBUG)
# --------------------------------
async def export_to_file(conn, portfolio_id):
    row = await conn.fetchrow("""
        SELECT candidate_name, cleaned_data
        FROM portfolios
        WHERE id=$1;
    """, portfolio_id)

    if not row or not row["cleaned_data"]:
        print("❌ Nothing to export.")
        return

    filename = f"{row['candidate_name'].replace(' ', '_')}.txt"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(row["cleaned_data"])

    print(f"\n✅ Exported to {filename}\n")


# --------------------------------
# FAILED SCRAPES
# --------------------------------
async def show_failed(conn):
    rows = await conn.fetch("""
        SELECT id, portfolio_url
        FROM portfolios
        WHERE status='failed';
    """)

    if not rows:
        print("\n✅ No failed scrapes.\n")
        return

    print("\n❌ Failed Portfolios:\n")

    for r in rows:
        print(f"ID {r['id']} -> {r['portfolio_url']}")


# --------------------------------
# MAIN MENU
# --------------------------------
async def main():
    conn = await asyncpg.connect(**DB_CONFIG)

    while True:

        print("""
========= SCRAPER DATA INSPECTOR =========

1️⃣  List completed portfolios
2️⃣  View FULL cleaned text
3️⃣  Export cleaned text to file
4️⃣  Show failed scrapes
5️⃣  Exit

=========================================
""")

        choice = input("Select option: ")

        if choice == "1":
            await list_completed(conn)

        elif choice == "2":
            pid = int(input("Enter portfolio ID: "))
            await view_full_text(conn, pid)

        elif choice == "3":
            pid = int(input("Enter portfolio ID: "))
            await export_to_file(conn, pid)

        elif choice == "4":
            await show_failed(conn)

        elif choice == "5":
            break

        else:
            print("Invalid option.")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
