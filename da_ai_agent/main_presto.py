"""
Heads up: in v7 pyautogen doesn't work with the latest openai version so this file has been commented out via pyproject.toml
"""
import json
import os

from da_ai_agent.agents import agents_presto
from da_ai_agent.agents.instruments import PrestoAgentInstruments
from da_ai_agent.modules.db_presto import PrestoManager
from da_ai_agent.modules import llm
from da_ai_agent.modules import orchestrator
from da_ai_agent.modules import rand
from da_ai_agent.modules import file
from da_ai_agent.modules import embeddings_presto
import prestodb
import dotenv
import argparse
import autogen

from da_ai_agent.data_types import ConversationResult

# ---------------- Your Environment Variables ----------------

dotenv.load_dotenv()

required_env_vars = ["PRESTO_HOST", "OPENAI_API_KEY", "PRESTO_PORT", "PRESTO_USER", "PRESTO_CATALOG", "PRESTO_SCHEMA", "PRESTO_HTTP_SCHEME"]

for var in required_env_vars:
    if not os.environ.get(var):
        raise EnvironmentError(f"{var} not found in .env file")

# ---------------- Constants ---------------------------------

# Check if PRESTO_PASSWORD is present in the environment, use None if not provided
presto_password = os.getenv('PRESTO_PASSWORD', None)
auth = prestodb.auth.BasicAuthentication(os.getenv('PRESTO_USER'), presto_password) if presto_password else None

PRESTO_DB_CONFIG = {
    'host': os.getenv('PRESTO_HOST'),
    'port': int(os.getenv('PRESTO_PORT')),
    'user': os.getenv('PRESTO_USER'),
    'catalog': os.getenv('PRESTO_CATALOG'),
    'schema': os.getenv('PRESTO_SCHEMA'),
    'http_scheme': os.getenv('PRESTO_HTTP_SCHEME'),
    'auth': auth
}

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

PRESTO_TABLE_DEFINITIONS_CAP_REF = "TABLE_DEFINITIONS"


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

    with PrestoAgentInstruments(PRESTO_DB_CONFIG, session_id) as (agent_instruments, db):
        # TODO: Fix PRESTO_DB_URL set up as dictionary

        # ----------- Gate Team: Prevent bad prompts from running and burning your $$$ -------------

        gate_orchestrator = agents_presto.build_team_orchestrator(
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
        # TODO: Set up table definitions so they work with PrestoDB db_presto.py file methods
        map_table_name_to_table_def = db.get_table_definition_map_for_embeddings()

        database_embedder = embeddings_presto.DatabaseEmbedder()

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
            f"Use these {PRESTO_TABLE_DEFINITIONS_CAP_REF} to satisfy the database query.",
            PRESTO_TABLE_DEFINITIONS_CAP_REF,
            table_definitions,
        )

        # ----------- Data Eng Team: Based on a SQL table definitions and a prompt create an sql statement and execute it -------------

        data_eng_orchestrator = agents_presto.build_team_orchestrator(
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
            f"Use these {PRESTO_TABLE_DEFINITIONS_CAP_REF} to satisfy the database query.",
            PRESTO_TABLE_DEFINITIONS_CAP_REF,
            core_and_related_table_definitions,
        )

        data_insights_orchestrator = agents_presto.build_team_orchestrator(
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