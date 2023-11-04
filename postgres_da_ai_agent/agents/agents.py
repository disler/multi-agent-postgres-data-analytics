from typing import Optional, List, Dict, Any
from postgres_da_ai_agent.agents.instruments import PostgresAgentInstruments
from postgres_da_ai_agent.modules import orchestrator
from postgres_da_ai_agent.agents import agent_config
import autogen
import guidance

# ------------------------ PROMPTS ------------------------


USER_PROXY_PROMPT = "A human admin. Interact with the Product Manager to discuss the plan. Plan execution needs to be approved by this admin."
DATA_ENGINEER_PROMPT = "A Data Engineer. Generate the initial SQL based on the requirements provided. Send it to the Sr Data Analyst to be executed. "
SR_DATA_ANALYST_PROMPT = "Sr Data Analyst. You run the SQL query using the run_sql function, send the raw response to the data viz team. You use the run_sql function exclusively."


GUIDANCE_SCRUM_MASTER_SQL_NLQ_PROMPT = """
Is the following block of text a SQL Natural Language Query (NLQ)? Please rank from 1 to 5, where:
1: Definitely not NLQ
2: Likely not NLQ
3: Neutral / Unsure
4: Likely NLQ
5: Definitely NLQ

Return the rank as a number exclusively using the rank variable to be casted as an integer.

Block of Text: {{potential_nlq}}
{{#select "rank" logprobs='logprobs'}} 1{{or}} 2{{or}} 3{{or}} 4{{or}} 5{{/select}}
"""

DATA_INSIGHTS_GUIDANCE_PROMPT = """
You're a data innovator. You analyze SQL databases table structure and generate 3 novel insights for your team to reflect on and query. 
Format your insights in JSON format.
```json
[{{#geneach 'insight' num_iterations=3 join=','}}
{
    "insight": "{{gen 'insight' temperature=0.7}}",
    "actionable_business_value": "{{gen 'actionable_value' temperature=0.7}}",
    "sql": "{{gen 'new_query' temperature=0.7}}"
}
{{/geneach}}]
```"""


INSIGHTS_FILE_REPORTER_PROMPT = "You're a data reporter. You write json data you receive directly into a file using the write_innovation_file function."


# unused prompts
COMPLETION_PROMPT = "If everything looks good, respond with APPROVED"
PRODUCT_MANAGER_PROMPT = (
    "Product Manager. Validate the response to make sure it's correct"
    + COMPLETION_PROMPT
)
TEXT_REPORT_ANALYST_PROMPT = "Text File Report Analyst. You exclusively use the write_file function on a summarized report."
JSON_REPORT_ANALYST_PROMPT = "Json Report Analyst. You exclusively use the write_json_file function on the report."
YML_REPORT_ANALYST_PROMPT = "Yaml Report Analyst. You exclusively use the write_yml_file function on the report."


# ------------------------ BUILD AGENT TEAMS ------------------------


def build_data_eng_team(instruments: PostgresAgentInstruments):
    """
    Build a team of agents that can generate, execute, and report an SQL query
    """

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


def build_scrum_master_team(instruments: PostgresAgentInstruments):
    user_proxy = autogen.UserProxyAgent(
        name="Admin",
        system_message=USER_PROXY_PROMPT,
        code_execution_config=False,
        human_input_mode="NEVER",
    )

    scrum_agent = DefensiveScrumMasterAgent(
        name="Scrum_Master",
        llm_config=agent_config.base_config,
        system_message=GUIDANCE_SCRUM_MASTER_SQL_NLQ_PROMPT,
        human_input_mode="NEVER",
    )

    return [user_proxy, scrum_agent]


def build_insights_team(instruments: PostgresAgentInstruments):
    user_proxy = autogen.UserProxyAgent(
        name="Admin",
        system_message=USER_PROXY_PROMPT,
        code_execution_config=False,
        human_input_mode="NEVER",
    )

    insights_agent = InsightsAgent(
        name="Insights",
        llm_config=agent_config.base_config,
        system_message=DATA_INSIGHTS_GUIDANCE_PROMPT,
        human_input_mode="NEVER",
    )

    insights_data_reporter = autogen.AssistantAgent(
        name="Insights_Data_Reporter",
        llm_config=agent_config.write_innovation_file_config,
        system_message=INSIGHTS_FILE_REPORTER_PROMPT,
        human_input_mode="NEVER",
        function_map={
            "write_innovation_file": instruments.write_innovation_file,
        },
    )

    return [user_proxy, insights_agent, insights_data_reporter]


# ------------------------ ORCHESTRATION ------------------------


def build_team_orchestrator(
    team: str,
    agent_instruments: PostgresAgentInstruments,
    validate_results: callable = None,
) -> orchestrator.Orchestrator:
    """
    Based on a team name, build a team of agents and return an orchestrator
    """
    if team == "data_eng":
        return orchestrator.Orchestrator(
            name="data_eng_team",
            agents=build_data_eng_team(agent_instruments),
            instruments=agent_instruments,
            validate_results_func=validate_results,
        )
    elif team == "data_viz":
        return orchestrator.Orchestrator(
            name="data_viz_team",
            agents=build_data_viz_team(agent_instruments),
            validate_results_func=validate_results,
        )
    elif team == "scrum_master":
        return orchestrator.Orchestrator(
            name="scrum_master_team",
            agents=build_scrum_master_team(agent_instruments),
            instruments=agent_instruments,
            validate_results_func=validate_results,
        )
    elif team == "data_insights":
        return orchestrator.Orchestrator(
            name="data_insights_team",
            agents=build_insights_team(agent_instruments),
            instruments=agent_instruments,
            validate_results_func=validate_results,
        )

    raise Exception("Unknown team: " + team)


# ------------------------ CUSTOM AGENTS ------------------------


class DefensiveScrumMasterAgent(autogen.ConversableAgent):
    """
    Custom agent that uses the guidance function to determine if a message is a SQL NLQ
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Register the new reply function for this specific agent
        self.register_reply(self, self.check_sql_nlq, position=0)

    def check_sql_nlq(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[autogen.Agent] = None,
        config: Optional[Any] = None,  # Persistent state.
    ):
        # Check the last received message
        last_message = messages[-1]["content"]

        # Use the guidance string to determine if the message is a SQL NLQ
        response = guidance(
            GUIDANCE_SCRUM_MASTER_SQL_NLQ_PROMPT, potential_nlq=last_message
        )

        # You can return the exact response or just a simplified version,
        # here we are just returning the rank for simplicity
        rank = response.get("choices", [{}])[0].get("rank", "3")

        return True, rank


class InsightsAgent(autogen.ConversableAgent):
    """
    Custom agent that uses the guidance function to generate insights in JSON format
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register_reply(self, self.generate_insights, position=0)

    def generate_insights(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[autogen.Agent] = None,
        config: Optional[Any] = None,
    ):
        insights = guidance(DATA_INSIGHTS_GUIDANCE_PROMPT)
        return True, insights
