import json
from flask import Flask, Request, Response, jsonify, request, make_response
import dotenv
from modules import db, llm, emb, instruments
from modules.turbo4 import Turbo4

import os

from modules.models import TurboTool
from psycopg2 import Error as PostgresError

app = Flask(__name__)

# ---------------- .Env Constants ----------------

dotenv.load_dotenv()

assert os.environ.get("DATABASE_URL"), "POSTGRES_CONNECTION_URL not found in .env file"
assert os.environ.get(
    "OPENAI_API_KEY"
), "POSTGRES_CONNECTION_URL not found in .env file"


DB_URL = os.environ.get("DATABASE_URL")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# ---------------- Cors Helper ----------------


def make_cors_response():
    # Set CORS headers for the preflight request
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
    return response


# ---------------- Self Correcting Assistant ----------------


def self_correcting_assistant(
    db: db.PostgresManager,
    agent_instruments: instruments.AgentInstruments,
    tools: TurboTool,
    error: PostgresError,
):
    # reset db - to unblock transactions
    db.roll_back()

    all_table_definitions = db.get_table_definitions_for_prompt()

    print(f"Loaded all table definitions")

    # ------ File prep

    file_path = agent_instruments.self_correcting_table_def_file

    # write all_table_definitions to file
    with open(file_path, "w") as f:
        f.write(all_table_definitions)

    files_to_upload = [file_path]

    sql_query = open(agent_instruments.sql_query_file).read()

    # ------ Prompts

    output_file_path = agent_instruments.run_sql_results_file

    diagnosis_prompt = f"Given the table_definitions.sql file, the following SQL_ERROR, and the SQL_QUERY, describe the most likely cause of the error. Think step by step.\n\nSQL_ERROR: {error}\n\nSQL_QUERY: {sql_query}"

    generation_prompt = (
        f"Based on your diagnosis, generate a new SQL query that will run successfully."
    )

    run_sql_prompt = "Use the run_sql function to run the SQL you've just generated."

    assistant_name = "SQL Self Correction"

    turbo4_assistant = Turbo4().get_or_create_assistant(assistant_name)

    print(f"Generated Assistant: {assistant_name}")

    file_ids = turbo4_assistant.upsert_files(files_to_upload)

    print(f"Uploaded files: {file_ids}")

    print(f"Running Self Correction Assistant...")

    (
        turbo4_assistant.set_instructions(
            "You're an elite SQL developer. You generate the most concise and performant SQL queries. You review failed queries and generate new SQL queries to fix them."
        )
        .enable_retrieval()
        .equip_tools(tools)
        .make_thread()
        # 1/3 STEP PATTERN: diagnose
        .add_message(diagnosis_prompt, file_ids=file_ids)
        .run_thread()
        .spy_on_assistant(agent_instruments.make_agent_chat_file(assistant_name))
        # 2/3 STEP PATTERN: generate
        .add_message(generation_prompt)
        .run_thread()
        .spy_on_assistant(agent_instruments.make_agent_chat_file(assistant_name))
        # 3/3 STEP PATTERN: execute
        .add_message(run_sql_prompt)
        .run_thread(toolbox=[tools[0].name])
        .spy_on_assistant(agent_instruments.make_agent_chat_file(assistant_name))
        # clean up, logging, reporting, cost
        .run_validation(agent_instruments.validate_file_exists(output_file_path))
        .spy_on_assistant(agent_instruments.make_agent_chat_file(assistant_name))
        .get_costs_and_tokens(agent_instruments.make_agent_cost_file(assistant_name))
    )

    pass


# ---------------- Primary Endpoint ----------------


@app.route("/prompt", methods=["POST", "OPTIONS"])
def prompt():
    # Set CORS headers for the main request
    response = make_cors_response()
    if request.method == "OPTIONS":
        return response

    # Get access to db, state, and functions
    with instruments.PostgresAgentInstruments(DB_URL, "prompt-endpoint") as (
        agent_instruments,
        db,
    ):
        # ---------------- Build Prompt ----------------

        base_prompt = request.json["prompt"]

        # simple word match for now - dropped embeddings for deployment size
        similar_tables = emb.DatabaseEmbedder(db).get_similar_table_defs_for_prompt(
            base_prompt
        )

        if len(similar_tables) == 0:
            print(f"No similar tables found for prompt: {base_prompt}")
            response.status_code = 400
            response.data = "No similar tables found."
            return response

        print("similar_tables", similar_tables)

        print(f"base_prompt: {base_prompt}")

        prompt = f"Fulfill this database query: {base_prompt}. "
        prompt = llm.add_cap_ref(
            prompt,
            f"Use these TABLE_DEFINITIONS to satisfy the database query.",
            "TABLE_DEFINITIONS",
            similar_tables,
        )

        # ---------------- Run 2 Agent Team - Generate SQL & Results ----------------

        tools = [
            TurboTool("run_sql", llm.run_sql_tool_config, agent_instruments.run_sql),
        ]

        sql_response = llm.prompt(
            prompt,
            model="gpt-4-1106-preview",
            instructions="You're an elite SQL developer. You generate the most concise and performant SQL queries.",
        )
        try:
            llm.prompt_func(
                "Use the run_sql function to run the SQL you've just generated: "
                + sql_response,
                model="gpt-4-1106-preview",
                instructions="You're an elite SQL developer. You generate the most concise and performant SQL queries.",
                turbo_tools=tools,
            )
            agent_instruments.validate_run_sql()
        except PostgresError as e:
            print(
                f"Received PostgresError -> Running Self Correction Team To Resolve: {e}"
            )

            # ---------------- Run Self Correction Team - Diagnosis, Generate New SQL, Retry ----------------
            self_correcting_assistant(db, agent_instruments, tools, e)

            print(f"Self Correction Team Complete.")

        # ---------------- Read result files and respond ----------------

        sql_query = open(agent_instruments.sql_query_file).read()
        sql_query_results = open(agent_instruments.run_sql_results_file).read()

        response_obj = {
            "prompt": base_prompt,
            "results": sql_query_results,
            "sql": sql_query,
        }

        print("response_obj", response_obj)

        response.data = json.dumps(response_obj)

        return response


if __name__ == "__main__":
    port = 3000
    print(f"Starting server on port {port}")
    app.run(debug=True, port=port)
