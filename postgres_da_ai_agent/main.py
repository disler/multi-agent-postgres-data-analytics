import os
from postgres_da_ai_agent.modules.db import PostgresManager
from postgres_da_ai_agent.modules import llm
from postgres_da_ai_agent.modules import orchestrator
from postgres_da_ai_agent.modules import file
from postgres_da_ai_agent.modules import embeddings
from postgres_da_ai_agent.agents import agents
import dotenv
import argparse
import autogen

dotenv.load_dotenv()

assert os.environ.get("DATABASE_URL"), "POSTGRES_CONNECTION_URL not found in .env file"
assert os.environ.get(
    "OPENAI_API_KEY"
), "POSTGRES_CONNECTION_URL not found in .env file"

DB_URL = os.environ.get("DATABASE_URL")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

POSTGRES_TABLE_DEFINITIONS_CAP_REF = "TABLE_DEFINITIONS"
RESPONSE_FORMAT_CAP_REF = "RESPONSE_FORMAT"
SQL_DELIMITER = "---------"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", help="The prompt for the AI")
    args = parser.parse_args()

    if not args.prompt:
        print("Please provide a prompt")
        return

    raw_prompt = args.prompt

    prompt = f"Fulfill this database query: {raw_prompt}. "

    with PostgresManager() as db:
        db.connect_with_url(DB_URL)

        map_table_name_to_table_def = db.get_table_definition_map_for_embeddings()

        database_embedder = embeddings.DatabaseEmbedder()

        for name, table_def in map_table_name_to_table_def.items():
            database_embedder.add_table(name, table_def)

        similar_tables = database_embedder.get_similar_tables(raw_prompt, n=5)

        table_definitions = database_embedder.get_table_definitions_from_names(
            similar_tables
        )

        prompt = llm.add_cap_ref(
            prompt,
            f"Use these {POSTGRES_TABLE_DEFINITIONS_CAP_REF} to satisfy the database query.",
            POSTGRES_TABLE_DEFINITIONS_CAP_REF,
            table_definitions,
        )

        data_eng_orchestrator = agents.build_team_orchestrator("data_eng", db)

        success, data_eng_messages = data_eng_orchestrator.sequential_conversation(
            prompt
        )

        # ---------------------------------------------

        data_eng_cost, data_eng_tokens = data_eng_orchestrator.get_cost_and_tokens()

        print(f"Data Eng Cost: {data_eng_cost}, tokens: {data_eng_tokens}")

        print(f"💰📊🤖 Organization Cost: {data_eng_cost}, tokens: {data_eng_tokens}")


if __name__ == "__main__":
    main()
