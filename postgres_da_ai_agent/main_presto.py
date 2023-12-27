"""
Heads up: in v7 pyautogen doesn't work with the latest openai version so this file has been commented out via pyproject.toml
"""
import json
import os

from postgres_da_ai_agent.agents import agents_presto
from postgres_da_ai_agent.agents.instruments import PrestoAgentInstruments
from postgres_da_ai_agent.modules.db_presto import PrestoManager
from postgres_da_ai_agent.modules import llm
from postgres_da_ai_agent.modules import orchestrator
from postgres_da_ai_agent.modules import rand
from postgres_da_ai_agent.modules import file
from postgres_da_ai_agent.modules import embeddings_presto
import prestodb
import dotenv
import argparse
import autogen

from postgres_da_ai_agent.data_types import ConversationResult

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

    session_id = rand.generate_session_id("presto_session")  # Example session ID, modify as needed

    # Create an instance of PrestoAgentInstruments, which in turn creates PrestoManager
    with PrestoAgentInstruments(PRESTO_DB_CONFIG, session_id) as presto_instruments:
        # Execute the query and fetch results using PrestoManager's run_sql method

        # call_center - SQL_STATEMENT_ONE = "SELECT cc_call_center_sk, cc_call_center_id, cc_rec_start_date, cc_rec_end_date, cc_closed_date_sk, cc_open_date_sk, cc_name, cc_class, cc_employees, cc_sq_ft, cc_hours, cc_manager, cc_mkt_id, cc_mkt_class, cc_mkt_desc, cc_market_manager, cc_division, cc_division_name, cc_company, cc_company_name, cc_street_number, cc_street_name, cc_street_type, cc_suite_number, cc_city, cc_county, cc_state, cc_zip, cc_country, cc_gmt_offset, cc_tax_percentage FROM tpcds.sf10.call_center LIMIT 10"
        # customer_address - SQL_STATEMENT_TWO = "SELECT ca_address_sk, ca_address_id, ca_street_number, ca_street_name, ca_street_type, ca_suite_number, ca_city, ca_county, ca_state, ca_zip, ca_country, ca_gmt_offset, ca_location_type  FROM tpcds.sf10.customer_address LIMIT 10"
        # store - SQL_STATEMENT_THREE = "SELECT s_store_sk, s_store_id, s_rec_start_date, s_rec_end_date, s_closed_date_sk, s_store_name, s_number_employees, s_floor_space, s_hours, s_manager, s_market_id, s_geography_class, s_market_desc, s_market_manager, s_division_id, s_division_name, s_company_id, s_company_name, s_street_number, s_street_name, s_street_type, s_suite_number, s_city, s_county, s_state, s_zip, s_country, s_gmt_offset, s_tax_precentage FROM tpcds.sf10.store LIMIT 10"

        json_results = presto_instruments.run_sql("SELECT s_store_sk, s_store_id, s_rec_start_date, s_rec_end_date, s_closed_date_sk, s_store_name, s_number_employees, s_floor_space, s_hours, s_manager, s_market_id, s_geography_class, s_market_desc, s_market_manager, s_division_id, s_division_name, s_company_id, s_company_name, s_street_number, s_street_name, s_street_type, s_suite_number, s_city, s_county, s_state, s_zip, s_country, s_gmt_offset, s_tax_precentage FROM tpcds.sf10.store LIMIT 10")

        # Convert the JSON results to a Python object
        results = json.loads(json_results)

        # Log the results
        print("Query Results:")
        for row in results:
            print(row)


if __name__ == "__main__":
    main()