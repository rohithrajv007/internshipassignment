import os
import smtplib
from email.message import EmailMessage
import asyncpg
from dotenv import load_dotenv

load_dotenv()

#########################################
# DATABASE CONFIG
#########################################

DB_CONFIG = {
    "user":    os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "host":    os.getenv("DB_HOST"),
    "port":    int(os.getenv("DB_PORT", 5432)),
}

#########################################
# EMAIL CONFIG
#########################################

EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASSWORD")

#########################################
# HR SCREENING QUESTIONS
#########################################

HR_QUESTIONS = [
    "Tell us briefly about your work experience relevant to this role.",
    "What are your current salary expectations?",
    "Are you employed currently and what is your notice period?",
    "Why do you want this job?",
    "What motivates you in your work?"
]

#########################################
# SEND EMAIL FUNCTION
#########################################

def send_email(to_email, subject, body):
    msg = EmailMessage()
    msg["From"] = EMAIL_USER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as smtp:
        smtp.starttls()
        smtp.login(EMAIL_USER, EMAIL_PASS)
        smtp.send_message(msg)

    print(f"📧 Sent screening email to {to_email}")


#########################################
# MAIN AGENT (SEND ONLY)
#########################################

async def main():
    conn = await asyncpg.connect(**DB_CONFIG)

    # only shortlist_status == 'SELECTED'
    candidates = await conn.fetch("""
        SELECT id, candidate_name, email
        FROM portfolios
        WHERE shortlist_status = 'SELECTED'
          AND email IS NOT NULL;
    """)

    if not candidates:
        print("⚠️ No shortlisted candidates found.")
        await conn.close()
        return

    print("\n📤 Sending HR screening emails...\n")

    for c in candidates:
        to_email = c["email"]
        questions_text = "\n\n".join(
            f"{i+1}. {q}" for i, q in enumerate(HR_QUESTIONS)
        )

        subject = f"HR Screening for {c['candidate_name']}"
        body = f"Hello {c['candidate_name']},\n\n"
        body += "Please reply with answers to the following:\n\n"
        body += questions_text
        body += "\n\nThank you!\n"

        # send email
        send_email(to_email, subject, body)

        # store placeholder for answers
        for i, _ in enumerate(HR_QUESTIONS):
            await conn.execute("""
                INSERT INTO hr_answers (portfolio_id, question_id)
                VALUES ($1, $2)
            """, c["id"], i+1)

    await conn.close()

    print("\n✅ All screening emails sent successfully. Exiting.\n")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
