from datetime import datetime
import json
import psycopg2
from psycopg2.sql import SQL, Identifier


class PrestoManager:
    """
    A class to manage PrestoDB connections and queries
    """


    def run_sql(self, sql) -> str:
        """
        Run a SQL query against the postgres database
        """


    def datetime_handler(self, obj):
        """
        Handle datetime objects when serializing to JSON.
        """


    def get_table_definition(self, table_name):
        """
        Generate the 'create' definition for a table
        """


    def get_all_table_names(self):
        """
        Get all table names in the database
        """


    def get_table_definitions_for_prompt(self):
        """
        Get all table 'create' definitions in the database
        """


    def get_table_definition_map_for_embeddings(self):
        """
        Creates a map of table names to table definitions
        """


    def get_related_tables(self, table_list, n=2):
        """
        Get tables that have foreign keys referencing the given table
        """



# Query to fetch tables that have foreign keys referencing the given table


# Query to fetch tables that the given table references


# Convert dict to list and remove dups

