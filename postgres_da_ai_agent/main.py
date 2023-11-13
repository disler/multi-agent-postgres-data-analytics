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

from postgres_da_ai_agent.types import ConversationResult


# ---------------- Your Environment Variables ----------------

dotenv.load_dotenv()

assert os.environ.get("DATABASE_URL"), "POSTGRES_CONNECTION_URL not found in .env file"
assert os.environ.get(
    "OPENAI_API_KEY"
), "POSTGRES_CONNECTION_URL not found in .env file"


# ---------------- Constants ----------------


DB_URL = os.environ.get("DATABASE_URL")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

POSTGRES_TABLE_DEFINITIONS_CAP_REF = "TABLE_DEFINITIONS"


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

        # -------- BUILD TABLE DEFINITIONS -----------

        map_table_name_to_table_def = db.get_table_definition_map_for_embeddings()

        database_embedder = embeddings.DatabaseEmbedder()

        for name, table_def in map_table_name_to_table_def.items():
            database_embedder.add_table(name, table_def)

        similar_tables = database_embedder.get_similar_tables(raw_prompt, n=5)

        table_definitions = database_embedder.get_table_definitions_from_names(
            similar_tables
        )

        related_table_names = db.get_related_tables(similar_tables, n=3)

        core_and_related_table_definitions = (
            database_embedder.get_table_definitions_from_names(
                related_table_names + similar_tables
            )
        )

        prompt = llm.add_cap_ref(
            prompt,
            f"Use these {POSTGRES_TABLE_DEFINITIONS_CAP_REF} to satisfy the database query.",
            POSTGRES_TABLE_DEFINITIONS_CAP_REF,
            table_definitions,
        )

        # ----------- Data Eng Team: Based on a sql table definitions and a prompt create an sql statement and execute it -------------

        data_eng_orchestrator = agents.build_team_orchestrator(
            "data_eng",
            agent_instruments,
            validate_results=agent_instruments.validate_run_sql,
        )

        data_eng_conversation_result: ConversationResult = (
            data_eng_orchestrator.sequential_conversation(prompt)
        )

        match data_eng_conversation_result:
            case ConversationResult(
                success=True, cost=data_eng_cost, tokens=data_eng_tokens
            ):
                print(
                    f"✅ Orchestrator was successful. Team: {data_eng_orchestrator.name}"
                )
                print(
                    f"💰📊🤖 {data_eng_orchestrator.name} Cost: {data_eng_cost}, tokens: {data_eng_tokens}"
                )
            case _:
                print(
                    f"❌ Orchestrator failed. Team: {data_eng_orchestrator.name} Failed"
                )

        # ----------- Data Insights Team: Based on sql table definitions and a prompt generate novel insights -------------

        innovation_prompt = f"Given this database query: '{raw_prompt}'. Generate novel insights and new database queries to give business insights."

        insights_prompt = llm.add_cap_ref(
            innovation_prompt,
            f"Use these {POSTGRES_TABLE_DEFINITIONS_CAP_REF} to satisfy the database query.",
            POSTGRES_TABLE_DEFINITIONS_CAP_REF,
            core_and_related_table_definitions,
        )

        data_insights_orchestrator = agents.build_team_orchestrator(
            "data_insights",
            agent_instruments,
            validate_results=agent_instruments.validate_innovation_files,
        )

        data_insights_conversation_result: ConversationResult = (
            data_insights_orchestrator.round_robin_conversation(
                insights_prompt, loops=1
            )
        )

        match data_insights_conversation_result:
            case ConversationResult(
                success=True, cost=data_insights_cost, tokens=data_insights_tokens
            ):
                print(
                    f"✅ Orchestrator was successful. Team: {data_insights_orchestrator.name}"
                )
                print(
                    f"💰📊🤖 {data_insights_orchestrator.name} Cost: {data_insights_cost}, tokens: {data_insights_tokens}"
                )
            case _:
                print(
                    f"❌ Orchestrator failed. Team: {data_insights_orchestrator.name} Failed"
                )


if __name__ == "__main__":
    main()
