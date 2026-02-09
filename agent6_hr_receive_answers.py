import os
import imaplib
import email
import asyncpg
import asyncio
import re
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

##################################
# DB CONFIG
##################################

DB_CONFIG = {
    "user":    os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "host":    os.getenv("DB_HOST"),
    "port":    int(os.getenv("DB_PORT", 5432)),
}

##################################
# EMAIL CONFIG
##################################

IMAP_HOST = os.getenv("EMAIL_IMAP_HOST")
IMAP_PORT = int(os.getenv("EMAIL_IMAP_PORT", 993))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASSWORD")

##################################
# POLL INTERVAL (seconds)
##################################

POLL_INTERVAL = 30  # adjust as needed


##################################
# HELPER: Check Candidate Email
##################################

async def is_candidate_email(conn, email_addr):
    """Return True if this sender matches a portfolio email."""
    row = await conn.fetchrow("""
        SELECT 1
        FROM portfolios
        WHERE email = $1
    """, email_addr)
    return bool(row)


##################################
# FETCH EMAIL REPLIES
##################################

def fetch_mail_replies():
    mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    mail.login(EMAIL_USER, EMAIL_PASS)
    mail.select("INBOX")

    status, msgs = mail.search(None, 'UNSEEN')
    replies = []

    if status == "OK":
        for num in msgs[0].split():
            typ, data = mail.fetch(num, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])

            from_addr = email.utils.parseaddr(msg["From"])[1]

            # Safely decode body text
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        raw_bytes = part.get_payload(decode=True) or b""
                        try:
                            text_part = raw_bytes.decode("utf-8")
                        except Exception:
                            # fallback if not utf-8
                            text_part = raw_bytes.decode("latin1", errors="ignore")
                        body += text_part
            else:
                raw_bytes = msg.get_payload(decode=True) or b""
                try:
                    body = raw_bytes.decode("utf-8")
                except Exception:
                    body = raw_bytes.decode("latin1", errors="ignore")

            replies.append((num, from_addr, body.strip()))

    mail.logout()
    return replies


##################################
# STORE REPLIES (multi-question)
##################################

async def store_replies(conn):
    raw_replies = fetch_mail_replies()
    if not raw_replies:
        return False

    mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    mail.login(EMAIL_USER, EMAIL_PASS)
    mail.select("INBOX")

    stored_any = False

    for num, from_addr, full_text in raw_replies:

        if not await is_candidate_email(conn, from_addr):
            # skip unrelated sender and leave unread
            continue

        row = await conn.fetchrow("""
            SELECT id FROM portfolios
            WHERE email = $1
        """, from_addr)

        if not row:
            continue

        pid = row["id"]

        # Split by numbering: 1., 2., etc.
        # This regex captures multiple answers if the candidate numbered them
        parts = re.split(r"\n\s*\d+\.\s*", full_text)
        answers = [p.strip() for p in parts[1:]]

        for q_index, answer_text in enumerate(answers, start=1):
            # check if this question still unanswered
            answer_row = await conn.fetchrow("""
                SELECT id FROM hr_answers
                WHERE portfolio_id = $1
                  AND question_id = $2
                  AND responded = FALSE
            """, pid, q_index)

            if not answer_row:
                continue

            await conn.execute("""
                UPDATE hr_answers
                SET raw_answer = $1,
                    responded = TRUE,
                    answer_received_at = $2
                WHERE id = $3
            """, answer_text, datetime.utcnow(), answer_row["id"])

            print(f"📝 Stored parsed Q{q_index} from {from_addr}")
            stored_any = True

        # Mark email seen after processing
        mail.store(num, '+FLAGS', '\\Seen')

    mail.logout()
    return stored_any


##################################
# MAIN LOOP
##################################

async def main():
    conn = await asyncpg.connect(**DB_CONFIG)

    print("\n⏳ Starting Agent 6 HR Receiver (polling loop)...\n")

    while True:

        stored = await store_replies(conn)

        # Count unanswered questions
        remaining = await conn.fetchval("""
            SELECT COUNT(*) FROM hr_answers
            WHERE responded = FALSE
        """)

        if remaining == 0:
            print("\n✅ All pending HR questions answered! Exiting.\n")
            break

        if not stored:
            print("⚠️ No new candidate replies yet.")

        await asyncio.sleep(POLL_INTERVAL)

    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
