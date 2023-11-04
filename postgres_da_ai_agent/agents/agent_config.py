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


write_innovation_file_config = {
    **base_config,  # Inherit base configuration
    "functions": [
        {
            "name": "write_innovation_file",
            "description": "Write a file to the filesystem",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The content of the file to write",
                    },
                },
                "required": ["content"],
            },
        }
    ],
}
