import json
from flask import Flask, Request, Response, jsonify, request, make_response
import dotenv
from modules import db, llm, emb, instruments

import os

from modules.models import TurboTool

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


# ---------------- Primary Endpoint ----------------


@app.route("/prompt", methods=["POST", "OPTIONS"])
def prompt():
    response = make_cors_response()

    # Set CORS headers for the main request
    if request.method == "OPTIONS":
        return response

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
            return jsonify({"error": "No similar tables found."})

        print("similar_tables", similar_tables)

        print(f"base_prompt: {base_prompt}")

        prompt = f"Fulfill this database query: {base_prompt}. "
        prompt = llm.add_cap_ref(
            prompt,
            f"Use these TABLE_DEFINITIONS to satisfy the database query.",
            "TABLE_DEFINITIONS",
            similar_tables,
        )

        # ---------------- Run Data Team - Generate SQL & Results ----------------

        tools = [
            TurboTool("run_sql", llm.run_sql_tool_config, agent_instruments.run_sql),
        ]

        sql_response = llm.prompt(
            prompt,
            model="gpt-4-1106-preview",
            instructions="You're an elite SQL developer. You generate the most concise and performant SQL queries.",
        )
        llm.prompt_func(
            "Use the run_sql function to run the SQL you've just generated: "
            + sql_response,
            model="gpt-4-1106-preview",
            instructions="You're an elite SQL developer. You generate the most concise and performant SQL queries.",
            turbo_tools=tools,
        )
        agent_instruments.validate_run_sql()

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
