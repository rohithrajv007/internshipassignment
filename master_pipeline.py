import subprocess
import sys
import time
import os

WAIT_TIME = 5   # seconds between agents


############################################
# RUN AGENT SAFELY
############################################

def run_agent(agent_file):

    # Check file exists (VERY good practice)
    if not os.path.exists(agent_file):
        print(f"\n❌ ERROR: {agent_file} not found.\n")
        sys.exit(1)

    print(f"\n🚀 Starting {agent_file}...\n")

    start_time = time.time()

    process = subprocess.run(
        [sys.executable, agent_file],
        text=True
    )

    if process.returncode != 0:
        print(f"\n❌ {agent_file} FAILED.")
        print("Stopping pipeline.\n")
        sys.exit(1)

    duration = round(time.time() - start_time, 2)

    print(f"\n✅ {agent_file} completed in {duration}s\n")


############################################
# MASTER PIPELINE
############################################

def main():

    print("\n" + "="*50)
    print("🚀 AUTONOMOUS HIRING PIPELINE STARTED")
    print("="*50)

    agents = [
        "agent1.py",
        "agent2.py",
        "agent3_ai_evaluator.py",
        "agent4.py",
        "agent5_hr_email_sender.py",
        "agent6_hr_receive_answers.py",
        "agent7_hr_ai_evaluator.py",
    ]

    for i, agent in enumerate(agents):

        run_agent(agent)

        # Wait AFTER completion except for last agent
        if i < len(agents) - 1:
            print(f"⏳ Waiting {WAIT_TIME} seconds before next agent...\n")
            time.sleep(WAIT_TIME)

    print("\n" + "="*50)
    print("🎉 PIPELINE COMPLETED SUCCESSFULLY")
    print("="*50)


############################################

if __name__ == "__main__":
    main()
