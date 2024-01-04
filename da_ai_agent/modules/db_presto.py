import json
import prestodb
from datetime import datetime


class PrestoManager:
    """
    A class to manage PrestoDB connections and queries
    """

    def __init__(self):
        self.conn = None
        self.cur = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def connect_with_url(self, config):
        # If auth key is None, do not include it in the connection parameters
        conn_params = {
            'host': config['host'],
            'port': config['port'],
            'user': config['user'],
            'catalog': config['catalog'],
            'schema': config['schema'],
            'http_scheme': config['http_scheme'],
        }
        if config.get('auth'):
            conn_params['auth'] = config['auth']

        self.conn = prestodb.dbapi.connect(**conn_params)
        self.cur = self.conn.cursor()

    def close(self):
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()

    def run_sql(self, sql) -> str:
        """
        Run a SQL query against the PrestoDB database and print the results as a plain text,
        including column names as the first row.
        """
        self.cur.execute(sql)
        rows = self.cur.fetchall()

        # Handling empty result sets
        if not rows:
            print("")
            return ""

        # Fetching column names from the cursor description
        columns = [desc[0] for desc in self.cur.description]
        column_names = ",".join(columns)

        # Joining all column values from each row, separated by commas
        # Then joining all rows, separated by a newline
        result_rows = "\n".join(
            ",".join(str(value) for value in row) for row in rows
        )

        # Combine column names and rows
        result_text = column_names + "\n" + result_rows

        # Print the entire results
        print(result_text)

        return result_text

    def datetime_handler(self, obj):
        """
        Handle datetime objects when serializing to JSON.
        """
        if isinstance(obj, datetime):
            return obj.isoformat()
        return str(obj)

    def get_all_table_names(self):
        """
        Get all table names in the PrestoDB database
        """
        # Adjusted query for PrestoDB
        self.cur.execute("SHOW TABLES")
        return [row[0] for row in self.cur.fetchall()]

    def get_table_definition(self, table_name):
        """
        Get the 'create' definition for a table in PrestoDB.
        The output format is modified to match the requested structure.
        """
        self.cur.execute(f"DESCRIBE {table_name}")
        rows = self.cur.fetchall()

        # Dictionary to hold the table definition
        table_definition = {table_name: {}}

        # Adding each column as a key-value pair in the table definition dictionary
        for row in rows:
            column_name, column_type, _ = row[:3]
            table_definition[table_name][column_name] = column_type

        return table_definition

    def get_table_definitions_for_prompt(self):
        """
        Get all table 'create' definitions in the PrestoDB database
        """
        table_names = self.get_all_table_names()
        definitions = []
        for table_name in table_names:
            definitions.append(self.get_table_definition(table_name))
        return "\n\n".join(definitions)

    def get_table_definitions_map_for_embeddings(self):
        """
        Creates a map of table names to table definitions.
        The structure is updated to match the requested format.
        """
        table_names = self.get_all_table_names()
        definitions = {}
        for table_name in table_names:
            definitions.update(self.get_table_definition(table_name))
        return definitions


    def get_related_tables(self, table_list, n=2):
        """
        Get tables that are related to the given tables in PrestoDB.
        Note: This function assumes a custom mechanism to track relationships,
        as PrestoDB does not support foreign keys natively.
        """

        related_tables_dict = {}

        for table in table_list:
            # Example query to fetch related tables based on a custom mechanism
            # Adjust the query based on your specific setup.
            self.cur.execute(
                """
                SELECT related_table
                FROM custom_relationships_table
                WHERE table_name = %s
                LIMIT %s;
                """,
                (table, n),
            )

            related_tables = [row[0] for row in self.cur.fetchall()]
            related_tables_dict[table] = related_tables

        # Convert dict to list and remove duplicates
        related_tables_list = []
        for related_tables in related_tables_dict.values():
            related_tables_list.extend(related_tables)

        return list(set(related_tables_list))
