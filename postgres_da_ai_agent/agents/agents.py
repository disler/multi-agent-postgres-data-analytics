import os
from postgres_da_ai_agent.agents.instruments import PostgresAgentInstruments
from postgres_da_ai_agent.modules.db import PostgresManager
from postgres_da_ai_agent.modules import llm
from postgres_da_ai_agent.modules import orchestrator
from postgres_da_ai_agent.modules import file
from postgres_da_ai_agent.agents import agent_config
import dotenv
import argparse
import autogen

# ------------ PROMPTS ------------


# create our terminate msg function
def is_termination_msg(content):
    have_content = content.get("content", None) is not None
    if have_content and "APPROVED" in content["content"]:
        return True
    return False


COMPLETION_PROMPT = "If everything looks good, respond with APPROVED"

USER_PROXY_PROMPT = "A human admin. Interact with the Product Manager to discuss the plan. Plan execution needs to be approved by this admin."
DATA_ENGINEER_PROMPT = "A Data Engineer. Generate the initial SQL based on the requirements provided. Send it to the Sr Data Analyst to be executed. "
SR_DATA_ANALYST_PROMPT = "Sr Data Analyst. You run the SQL query using the run_sql function, send the raw response to the data viz team. You use the run_sql function exclusively."
PRODUCT_MANAGER_PROMPT = (
    "Product Manager. Validate the response to make sure it's correct"
    + COMPLETION_PROMPT
)

TEXT_REPORT_ANALYST_PROMPT = "Text File Report Analyst. You exclusively use the write_file function on a summarized report."
JSON_REPORT_ANALYST_PROMPT = "Json Report Analyst. You exclusively use the write_json_file function on the report."
YML_REPORT_ANALYST_PROMPT = "Yaml Report Analyst. You exclusively use the write_yml_file function on the report."


# ------------ AGENTS ------------
def build_data_eng_team(instruments: PostgresAgentInstruments):
    # create a set of agents with specific roles
    # admin user proxy agent - takes in the prompt and manages the group chat
    user_proxy = autogen.UserProxyAgent(
        name="Admin",
        system_message=USER_PROXY_PROMPT,
        code_execution_config=False,
        human_input_mode="NEVER",
    )

    # data engineer agent - generates the sql query
    data_engineer = autogen.AssistantAgent(
        name="Engineer",
        llm_config=agent_config.base_config,
        system_message=DATA_ENGINEER_PROMPT,
        code_execution_config=False,
        human_input_mode="NEVER",
    )

    sr_data_analyst = autogen.AssistantAgent(
        name="Sr_Data_Analyst",
        llm_config=agent_config.run_sql_config,
        system_message=SR_DATA_ANALYST_PROMPT,
        code_execution_config=False,
        human_input_mode="NEVER",
        function_map={
            "run_sql": instruments.run_sql,
        },
    )

    # product manager - validate the response to make sure it's correct
    product_manager = autogen.AssistantAgent(
        name="Product_Manager",
        llm_config=agent_config.base_config,
        system_message=PRODUCT_MANAGER_PROMPT,
        code_execution_config=False,
        human_input_mode="NEVER",
    )

    return [
        user_proxy,
        data_engineer,
        sr_data_analyst,
    ]


def build_data_viz_team(instruments: PostgresAgentInstruments):
    # admin user proxy agent - takes in the prompt and manages the group chat
    user_proxy = autogen.UserProxyAgent(
        name="Admin",
        system_message=USER_PROXY_PROMPT,
        code_execution_config=False,
        human_input_mode="NEVER",
    )

    # text report analyst - writes a summary report of the results and saves them to a local text file
    text_report_analyst = autogen.AssistantAgent(
        name="Text_Report_Analyst",
        llm_config=agent_config.write_file_config,
        system_message=TEXT_REPORT_ANALYST_PROMPT,
        human_input_mode="NEVER",
        function_map={
            "write_file": instruments.write_file,
        },
    )

    # json report analyst - writes a summary report of the results and saves them to a local json file
    json_report_analyst = autogen.AssistantAgent(
        name="Json_Report_Analyst",
        llm_config=agent_config.write_json_file_config,
        system_message=JSON_REPORT_ANALYST_PROMPT,
        human_input_mode="NEVER",
        function_map={
            "write_json_file": instruments.write_json_file,
        },
    )

    yaml_report_analyst = autogen.AssistantAgent(
        name="Yml_Report_Analyst",
        llm_config=agent_config.write_yaml_file_config,
        system_message=YML_REPORT_ANALYST_PROMPT,
        human_input_mode="NEVER",
        function_map={
            "write_yml_file": instruments.write_yml_file,
        },
    )

    return [
        user_proxy,
        text_report_analyst,
        json_report_analyst,
        yaml_report_analyst,
    ]


# ------------ ORCHESTRATION ------------


def build_team_orchestrator(
    team: str,
    agent_instruments: PostgresAgentInstruments,
    validate_results: callable = None,
) -> orchestrator.Orchestrator:
    if team == "data_eng":
        return orchestrator.Orchestrator(
            name="Postgres Data Analytics Multi-Agent ::: Data Engineering Team",
            agents=build_data_eng_team(agent_instruments),
            instruments=agent_instruments,
            validate_results_func=validate_results,
        )
    elif team == "data_viz":
        return orchestrator.Orchestrator(
            name="Postgres Data Analytics Multi-Agent ::: Data Viz Team",
            agents=build_data_viz_team(agent_instruments),
            validate_results_func=validate_results,
        )

    raise Exception("Unknown team: " + team)
