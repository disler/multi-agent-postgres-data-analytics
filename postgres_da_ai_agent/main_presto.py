"""
Heads up: in v7 pyautogen doesn't work with the latest openai version so this file has been commented out via pyproject.toml
"""

import os
from postgres_da_ai_agent.agents.instruments import PostgresAgentInstruments
from postgres_da_ai_agent.modules.db import PostgresManager
from postgres_da_ai_agent.modules import llm
from postgres_da_ai_agent.modules import orchestrator
from postgres_da_ai_agent.modules import rand
from postgres_da_ai_agent.modules import file
from postgres_da_ai_agent.modules import embeddings
from postgres_da_ai_agent.agents import agents
import dotenv
import argparse
import autogen

from postgres_da_ai_agent.data_types import ConversationResult


# ---------------- Your Environment Variables ----------------

dotenv.load_dotenv()

assert os.environ.get("PRESTO_DATABASE_URL"), "PRESTO_DATABASE_URL not found in .env file"
assert os.environ.get(
    "OPENAI_API_KEY"
), "OPENAI_API_KEY not found in .env file"


# ---------------- Constants ---------------------------------


PRESTO_DATABASE_URL = os.environ.get("PRESTO_DATABASE_URL")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

PRESTO_DATABASE_TABLE_DEFINITIONS_CAP_REF = "PRESTO_DATABASE_TABLE_DEFINITIONS"


def main():
    # ---------------- Parse '--prompt' CLI Parameter ----------------

    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", help="The prompt for the AI")
    args = parser.parse_args()

    if not args.prompt:
        print("Please provide a prompt")
        return

    raw_prompt = args.prompt

    prompt = f"Fulfill this database query: {raw_prompt}. "

    session_id = rand.generate_session_id(raw_prompt)

    # ---------------- Create Agent Instruments And Build Database Connection ----------------


        # -------- BUILD TABLE DEFINITIONS -----------
    with PostgresAgentInstruments(DB_URL, session_id) as (agent_instruments, db):
        # ----------- Gate Team: Prevent bad prompts from running and burning your $$$ -------------

        gate_orchestrator = agents.build_team_orchestrator(
            "scrum_master",
            agent_instruments,
            validate_results=lambda: (True, ""),
        )

        gate_orchestrator: ConversationResult = (
            gate_orchestrator.sequential_conversation(prompt)
        )

        print("gate_orchestrator.last_message_str", gate_orchestrator.last_message_str)

        nlq_confidence = int(gate_orchestrator.last_message_str)

        match nlq_confidence:
            case (1 | 2):
                print(f"❌ Gate Team Rejected - Confidence too low: {nlq_confidence}")
                return
            case (3 | 4 | 5):
                print(f"✅ Gate Team Approved - Valid confidence: {nlq_confidence}")
            case _:
                print("❌ Gate Team Rejected - Invalid response")
                return

        # ----------- Data Eng Team: Based on a SQL table definitions and a prompt create an sql statement and execute it -------------


        # ----------- Data Insights Team: Based on sql table definitions and a prompt generate novel insights -------------



if __name__ == "__main__":
    main()
