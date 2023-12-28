from postgres_da_ai_agent.agents.turbo4 import Turbo4
from postgres_da_ai_agent.data_types import Chat, TurboTool
from typing import List, Callable
import os
from postgres_da_ai_agent.agents.instruments import PrestoAgentInstruments
from postgres_da_ai_agent.modules import llm
from postgres_da_ai_agent.modules import rand
from postgres_da_ai_agent.modules import embeddings_presto
import argparse
import dotenv
import prestodb

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
PRESTO_TABLE_DEFINITIONS_CAP_REF = "TABLE_DEFINITIONS"


custom_function_tool_config = {
    "type": "function",
    "function": {
        "name": "store_fact",
        "description": "A function that stores a fact.",
        "parameters": {
            "type": "object",
            "properties": {"fact": {"type": "string"}},
        },
    },
}

run_sql_tool_config = {
    "type": "function",
    "function": {
        "name": "run_sql",
        "description": "Run a SQL query against the postgres database",
        "parameters": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "The SQL query to run",
                }
            },
            "required": ["sql"],
        },
    },
}


def store_fact(fact: str):
    print(f"------store_fact({fact})------")
    return "Fact stored."


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", help="The prompt for the AI")
    args = parser.parse_args()

    if not args.prompt:
        print("Please provide a prompt")
        return

    raw_prompt = args.prompt

    prompt = f"Fulfill this database query: {raw_prompt}. "

    assistant_name = "Turbo4"

    assistant = Turbo4()

    session_id = rand.generate_session_id(assistant_name + raw_prompt)

    with PrestoAgentInstruments(PRESTO_DB_CONFIG, session_id) as (agent_instruments, db):
        database_embedder = embeddings_presto.DatabaseEmbedder(db)

        table_definitions = database_embedder.get_similar_table_defs_for_prompt(
            raw_prompt
        )

        prompt = llm.add_cap_ref(
            prompt,
            f"Use these {PRESTO_TABLE_DEFINITIONS_CAP_REF} to satisfy the database query.",
            PRESTO_TABLE_DEFINITIONS_CAP_REF,
            table_definitions,
        )

        tools = [
            TurboTool("run_sql", run_sql_tool_config, agent_instruments.run_sql),
        ]

        (
            assistant.get_or_create_assistant(assistant_name)
            .set_instructions(
                "You're an elite SQL developer. You generate the most concise and performant SQL queries."
            )
            .equip_tools(tools)
            .make_thread()
            .add_message(prompt)
            .run_thread()
            .add_message(
                "Use the run_sql function to run the SQL you've just generated.",
            )
            .run_thread(toolbox=[tools[0].name])
            .run_validation(agent_instruments.validate_run_sql)
            .spy_on_assistant(agent_instruments.make_agent_chat_file(assistant_name))
            .get_costs_and_tokens(
                agent_instruments.make_agent_cost_file(assistant_name)
            )
        )

        print(f"✅ Turbo4 Assistant finished.")

        # ---------- Simple Prompt Solution - Same thing, only 2 api calls instead of 8+ ------------
        # sql_response = llm.prompt(
        #     prompt,
        #     model="gpt-4-1106-preview",
        #     instructions="You're an elite SQL developer. You generate the most concise and performant SQL queries.",
        # )
        # llm.prompt_func(
        #     "Use the run_sql function to run the SQL you've just generated: "
        #     + sql_response,
        #     model="gpt-4-1106-preview",
        #     instructions="You're an elite SQL developer. You generate the most concise and performant SQL queries.",
        #     turbo_tools=tools,
        # )
        # agent_instruments.validate_run_sql()

        # ----------- Example use case of Turbo4 and the Assistants API ------------

        # (
        #     assistant.get_or_create_assistant(assistant_name)
        #     .make_thread()
        #     .equip_tools(tools)
        #     .add_message("Generate 10 random facts about LLM technology.")
        #     .run_thread()
        #     .add_message("Use the store_fact function to 1 fact.")
        #     .run_thread(toolbox=["store_fact"])
        # )


if __name__ == "__main__":
    main()
