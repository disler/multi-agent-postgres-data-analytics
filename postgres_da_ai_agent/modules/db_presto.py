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

    def connect_with_url(self, url):
        # Extract connection parameters from the URL
        # Assuming the URL format: https://user:password@host:port/catalog/schema
        _, rest = url.split("://")
        user_password, host_port_catalog_schema = rest.split("@")
        user, password = user_password.split(":")
        host_port, catalog_schema = host_port_catalog_schema.split("/")
        host, port = host_port.split(":")
        catalog, schema = catalog_schema.split("/")

        # Establishing the connection
        self.conn = prestodb.dbapi.connect(
            host=host,
            port=int(port),
            user=user,
            catalog=catalog,
            schema=schema,
            http_scheme='https',
            auth=prestodb.auth.BasicAuthentication(user, password)
        )
        self.cur = self.conn.cursor()

    def close(self):
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()

    def run_sql(self, sql) -> str:
        """
        Run a SQL query against the PrestoDB database
        """
        self.cur.execute(sql)
        rows = self.cur.fetchall()

        # Handling empty result sets
        if not rows:
            return json.dumps([])

        # Fetching column names from the cursor
        columns = [desc[0] for desc in self.cur.description]
        list_of_dicts = [dict(zip(columns, row)) for row in rows]

        json_result = json.dumps(list_of_dicts, indent=4, default=self.datetime_handler)
        return json_result

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
        Get the 'create' definition for a table in PrestoDB
        """
        # PrestoDB does not directly support a single query to get the full create statement.
        # You need to construct it manually from column information.
        self.cur.execute(f"DESCRIBE {table_name}")
        rows = self.cur.fetchall()
        create_table_stmt = f"CREATE TABLE {table_name} (\n"
        for row in rows:
            column_name, column_type, _ = row[:3]
            create_table_stmt += f"  {column_name} {column_type},\n"
        create_table_stmt = create_table_stmt.rstrip(",\n") + "\n);"
        return create_table_stmt

    def get_table_definitions_for_prompt(self):
        """
        Get all table 'create' definitions in the PrestoDB database
        """
        table_names = self.get_all_table_names()
        definitions = []
        for table_name in table_names:
            definitions.append(self.get_table_definition(table_name))
        return "\n\n".join(definitions)

