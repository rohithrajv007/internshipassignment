import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


##################################################
# RESET DATABASE
##################################################

def reset_database():
    conn = psycopg2.connect(
        dbname="postgres",
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    # Terminate connections to allow drop
    cursor.execute("""
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = %s;
    """, (DB_NAME,))

    cursor.execute(f"DROP DATABASE IF EXISTS {DB_NAME}")
    print(f"🗑️ Dropped database '{DB_NAME}'")

    cursor.execute(f"CREATE DATABASE {DB_NAME}")
    print(f"✅ Created database '{DB_NAME}'")

    cursor.close()
    conn.close()


##################################################
# CREATE TABLES
##################################################

def create_tables():
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

    cursor = conn.cursor()

    ##################################################
    # portfolios table
    ##################################################

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolios (
            id SERIAL PRIMARY KEY,
            candidate_name TEXT,
            portfolio_url TEXT UNIQUE NOT NULL,
            email TEXT,

            cleaned_data TEXT,

            status VARCHAR(20) DEFAULT 'pending',

            backend_score FLOAT,
            ai_score FLOAT,

            ai_backend_score FLOAT,
            ai_ai_score FLOAT,

            final_backend_score FLOAT,
            final_ai_score FLOAT,

            backend_recommendation TEXT,
            ai_recommendation TEXT,

            shortlist_status TEXT,

            last_scraped TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    ############################################
    # INDEXES for performance
    ############################################

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_portfolios_status
        ON portfolios(status);
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_portfolios_backend_score
        ON portfolios(backend_score DESC);
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_portfolios_final_backend
        ON portfolios(final_backend_score DESC);
    """)

    ##################################################
    # hr_questions table
    ##################################################

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hr_questions (
            id SERIAL PRIMARY KEY,
            question TEXT NOT NULL,
            criteria JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    ##################################################
    # hr_answers table
    ##################################################

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hr_answers (
            id SERIAL PRIMARY KEY,
            portfolio_id INTEGER NOT NULL
                REFERENCES portfolios(id)
                ON DELETE CASCADE,
            question_id INTEGER NOT NULL
                REFERENCES hr_questions(id)
                ON DELETE CASCADE,
            raw_answer TEXT,
            processed_answer TEXT,
            ai_score FLOAT,
            ai_decision TEXT,
            responded BOOLEAN DEFAULT FALSE,
            answer_received_at TIMESTAMP
        );
    """)

    conn.commit()
    cursor.close()
    conn.close()

    print("✅ Tables created successfully.")


##################################################
# INSERT SAMPLE DATA
##################################################

def insert_sample_data():
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

    cursor = conn.cursor()

    ############################################
    # sample portfolios
    ############################################

    cursor.execute("""
        INSERT INTO portfolios (candidate_name, portfolio_url, email)
        VALUES
        ('Rohith Raj', 'https://my-portfolio-three-omega-10.vercel.app/', 'rajrohith.003@gmail.com'),
        ('Umang Saxena', 'https://www.umangsaxena.xyz/', 'umang@example.com'),
        ('Satyarth', 'https://ankulkumar0001.netlify.app/', NULL)
        ON CONFLICT (portfolio_url) DO NOTHING;
    """)

    ############################################
    # HR Screening questions
    ############################################

    cursor.execute("""
        INSERT INTO hr_questions (question, criteria)
        VALUES
        ('Tell us briefly about your work experience relevant to this role.', 
            '{"keywords":["experience","work","projects"],"threshold":2}'),
        ('What are your current salary expectations?', 
            '{"keywords":["salary","expected","lpa","annum"],"threshold":1}'),
        ('Are you employed currently and what is your notice period?', 
            '{"keywords":["notice","period","days","weeks"],"threshold":1}'),
        ('Why do you want this job?', 
            '{"keywords":["motivation","role","fit","interest"],"threshold":1}'),
        ('What motivates you in your work?', 
            '{"keywords":["motivation","passion","goals","growth"],"threshold":1}');
    """)

    conn.commit()
    cursor.close()
    conn.close()

    print("✅ Sample data inserted successfully.")


##################################################
# MAIN
##################################################

if __name__ == "__main__":

    print("\n🚀 Resetting Hiring Agent Database...\n")

    reset_database()
    create_tables()
    insert_sample_data()

    print("\n🎉 Database READY for multi-agent pipeline!\n")
