import os
from postgres_da_ai_agent.modules.db import PostgresManager
from postgres_da_ai_agent.modules import llm
from postgres_da_ai_agent.modules import orchestrator
from postgres_da_ai_agent.modules import file
import dotenv
import argparse
import autogen


# build the gpt_configuration object
# Base Configuration
base_config = {
    "use_cache": False,
    "temperature": 0,
    "config_list": autogen.config_list_from_models(["gpt-4"]),
    "request_timeout": 120,
}

# Configuration with "run_sql"
run_sql_config = {
    **base_config,  # Inherit base configuration
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

# Configuration with "write_file"
write_file_config = {
    **base_config,  # Inherit base configuration
    "functions": [
        {
            "name": "write_file",
            "description": "Write a file to the filesystem",
            "parameters": {
                "type": "object",
                "properties": {
                    "fname": {
                        "type": "string",
                        "description": "The name of the file to write",
                    },
                    "content": {
                        "type": "string",
                        "description": "The content of the file to write",
                    },
                },
                "required": ["fname", "content"],
            },
        }
    ],
}

# Configuration with "write_json_file"
write_json_file_config = {
    **base_config,  # Inherit base configuration
    "functions": [
        {
            "name": "write_json_file",
            "description": "Write a json file to the filesystem",
            "parameters": {
                "type": "object",
                "properties": {
                    "fname": {
                        "type": "string",
                        "description": "The name of the file to write",
                    },
                    "json_str": {
                        "type": "string",
                        "description": "The content of the file to write",
                    },
                },
                "required": ["fname", "json_str"],
            },
        }
    ],
}

write_yaml_file_config = {
    **base_config,  # Inherit base configuration
    "functions": [
        {
            "name": "write_yml_file",
            "description": "Write a yml file to the filesystem",
            "parameters": {
                "type": "object",
                "properties": {
                    "fname": {
                        "type": "string",
                        "description": "The name of the file to write",
                    },
                    "json_str": {
                        "type": "string",
                        "description": "The json content of the file to write",
                    },
                },
                "required": ["fname", "json_str"],
            },
        }
    ],
}


def create_func_map(name: str, func: callable):
    return {
        name: func,
    }


def build_function_map_run_sql(db: PostgresManager):
    return create_func_map("run_sql", db.run_sql)


function_map_write_file = create_func_map("write_file", file.write_file)
function_map_write_json_file = create_func_map("write_json_file", file.write_json_file)
function_map_write_yaml_file = create_func_map("write_yml_file", file.write_yml_file)
