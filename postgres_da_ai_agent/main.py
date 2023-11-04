import os
from postgres_da_ai_agent.modules.db import PostgresManager
from postgres_da_ai_agent.modules import llm
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

    prompt = f"Fulfill this database query: {args.prompt}. "

    with PostgresManager() as db:
        db.connect_with_url(DB_URL)

        table_definitions = db.get_table_definitions_for_prompt()

        prompt = llm.add_cap_ref(
            prompt,
            f"Use these {POSTGRES_TABLE_DEFINITIONS_CAP_REF} to satisfy the database query.",
            POSTGRES_TABLE_DEFINITIONS_CAP_REF,
            table_definitions,
        )

        # build the gpt_configuration object
        gpt4_config = {
            "use_cache": False,
            "temperature": 0,
            "config_list": autogen.config_list_from_models(["gpt-4"]),
            "request_timeout": 120,
            "functions": [
                {
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
                }
            ],
        }

        # build the function map
        function_map = {
            "run_sql": db.run_sql,
        }

        # create our terminate msg function
        def is_termination_msg(content):
            have_content = content.get("content", None) is not None
            if have_content and "APPROVED" in content["content"]:
                return True
            return False

        COMPLETION_PROMPT = "If everything looks good, respond with APPROVED"

        USER_PROXY_PROMPT = (
            "A human admin. Interact with the Product Manager to discuss the plan. Plan execution needs to be approved by this admin."
            + COMPLETION_PROMPT
        )
        DATA_ENGINEER_PROMPT = (
            "A Data Engineer. You follow an approved plan. Generate the initial SQL based on the requirements provided. Send it to the Sr Data Analyst to be executed."
            + COMPLETION_PROMPT
        )
        SR_DATA_ANALYST_PROMPT = (
            "Sr Data Analyst. You follow an approved plan. You run the SQL query, generate the response and send it to the product manager for final review."
            + COMPLETION_PROMPT
        )
        PRODUCT_MANAGER_PROMPT = (
            "Product Manager. Validate the response to make sure it's correct"
            + COMPLETION_PROMPT
        )

        # create a set of agents with specific roles
        # admin user proxy agent - takes in the prompt and manages the group chat
        user_proxy = autogen.UserProxyAgent(
            name="Admin",
            system_message=USER_PROXY_PROMPT,
            code_execution_config=False,
            human_input_mode="NEVER",
            is_termination_msg=is_termination_msg,
        )

        # data engineer agent - generates the sql query
        data_engineer = autogen.AssistantAgent(
            name="Engineer",
            llm_config=gpt4_config,
            system_message=DATA_ENGINEER_PROMPT,
            code_execution_config=False,
            human_input_mode="NEVER",
            is_termination_msg=is_termination_msg,
        )

        # sr data analyst agent - run the sql query and generate the response
        sr_data_analyst = autogen.AssistantAgent(
            name="Sr_Data_Analyst",
            llm_config=gpt4_config,
            system_message=SR_DATA_ANALYST_PROMPT,
            code_execution_config=False,
            human_input_mode="NEVER",
            is_termination_msg=is_termination_msg,
            function_map=function_map,
        )

        # product manager - validate the response to make sure it's correct
        product_manager = autogen.AssistantAgent(
            name="Product_Manager",
            llm_config=gpt4_config,
            system_message=PRODUCT_MANAGER_PROMPT,
            code_execution_config=False,
            human_input_mode="NEVER",
            is_termination_msg=is_termination_msg,
        )

        # create a group chat and initiate the chat.
        groupchat = autogen.GroupChat(
            agents=[user_proxy, data_engineer, sr_data_analyst, product_manager],
            messages=[],
            max_round=10,
        )
        manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=gpt4_config)

        user_proxy.initiate_chat(manager, clear_history=True, message=prompt)


if __name__ == "__main__":
    main()
